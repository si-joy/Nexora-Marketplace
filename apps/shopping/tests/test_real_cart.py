"""Account-cart API, stock validation and isolation tests."""
import json
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Category, Currency, Product, ProductVariant, ProductVariantPrice
from apps.inventory.models import Stock
from apps.shopping.models import CartItem
from apps.vendors.models import SellerProfile, Store

User = get_user_model()


@pytest.fixture
def real_cart_item(db):
    seller = User.objects.create_user(email="cart-seller@example.test", password="ValidPass123!")
    buyer = User.objects.create_user(email="cart-buyer@example.test", password="ValidPass123!")
    second_buyer = User.objects.create_user(email="cart-other@example.test", password="ValidPass123!")
    profile = SellerProfile.objects.create(
        user=seller, business_name="Cart Store", contact_phone="012345678",
        status=SellerProfile.Status.APPROVED,
    )
    store = Store.objects.create(
        seller=profile, name="Cart Store", slug="cart-store",
        status=Store.Status.ACTIVE,
    )
    category = Category.objects.create(name="Cart Audio", slug="cart-audio", is_active=True)
    product = Product.objects.create(
        store=store, category=category, name="Cart Headphones",
        slug="cart-headphones", status=Product.Status.PUBLISHED,
    )
    variant = ProductVariant.objects.create(product=product, sku="CART-HP-1", is_default=True)
    bdt, _ = Currency.objects.get_or_create(
        code="BDT", defaults={"name": "Bangladeshi Taka", "symbol": "৳"}
    )
    ProductVariantPrice.objects.create(variant=variant, currency=bdt, amount=Decimal("750.00"))
    stock = Stock.objects.create(variant=variant, quantity=5)
    return buyer, second_buyer, product, variant, stock


def post_json(client, url, data):
    return client.post(url, json.dumps(data), content_type="application/json")


@pytest.mark.django_db
def test_anonymous_cart_read_is_empty_but_write_requires_login(client, real_cart_item):
    _, _, _, variant, _ = real_cart_item
    response = client.get(reverse("shopping:real_cart_get"))
    assert response.status_code == 200
    assert response.json()["authenticated"] is False
    response = post_json(client, reverse("shopping:real_cart_add"), {"variant_id": variant.pk, "quantity": 1})
    assert response.status_code == 401
    assert response.json()["ok"] is False


@pytest.mark.django_db
def test_add_update_and_remove_cart_item(client, real_cart_item):
    buyer, _, _, variant, _ = real_cart_item
    client.force_login(buyer)
    add = reverse("shopping:real_cart_add")
    response = post_json(client, add, {"variant_id": variant.pk, "quantity": 2})
    assert response.status_code == 200
    assert response.json()["item_count"] == 2
    assert response.json()["subtotal"] == "1500.00"
    response = post_json(client, add, {"variant_id": variant.pk, "quantity": 1})
    assert response.json()["item_count"] == 3
    update = reverse("shopping:real_cart_update", args=[variant.pk])
    response = post_json(client, update, {"quantity": 4})
    assert response.json()["item_count"] == 4
    assert response.json()["subtotal"] == "3000.00"
    response = post_json(client, update, {"quantity": 0})
    assert response.json()["item_count"] == 0
    assert not CartItem.objects.filter(cart__user=buyer).exists()


@pytest.mark.django_db
def test_stock_limit_is_enforced_and_no_reservation_is_made(client, real_cart_item):
    buyer, _, _, variant, stock = real_cart_item
    client.force_login(buyer)
    add = reverse("shopping:real_cart_add")
    response = post_json(client, add, {"variant_id": variant.pk, "quantity": 6})
    assert response.status_code == 400
    assert not CartItem.objects.filter(cart__user=buyer).exists()
    response = post_json(client, add, {"variant_id": variant.pk, "quantity": 5})
    assert response.status_code == 200
    assert post_json(client, add, {"variant_id": variant.pk, "quantity": 1}).status_code == 400
    stock.refresh_from_db()
    assert stock.reserved_quantity == 0


@pytest.mark.django_db
def test_customer_carts_are_isolated(client, real_cart_item):
    buyer, second, _, variant, _ = real_cart_item
    client.force_login(buyer)
    post_json(client, reverse("shopping:real_cart_add"), {"variant_id": variant.pk, "quantity": 2})
    client.force_login(second)
    assert client.get(reverse("shopping:real_cart_get")).json()["item_count"] == 0
    assert post_json(client, reverse("shopping:real_cart_update", args=[variant.pk]), {"quantity": 0}).status_code == 400
    assert post_json(client, reverse("shopping:real_cart_clear"), {}).status_code == 200
    client.force_login(buyer)
    assert client.get(reverse("shopping:real_cart_get")).json()["item_count"] == 2


@pytest.mark.django_db
def test_unpublished_listing_cannot_be_added_and_existing_line_is_flagged(client, real_cart_item):
    buyer, _, product, variant, _ = real_cart_item
    client.force_login(buyer)
    post_json(client, reverse("shopping:real_cart_add"), {"variant_id": variant.pk, "quantity": 1})
    product.status = Product.Status.DRAFT
    product.save(update_fields=["status"])
    snapshot = client.get(reverse("shopping:real_cart_get")).json()
    assert snapshot["items"][0]["is_available"] is False
    assert snapshot["subtotal"] == "0.00"
    assert post_json(client, reverse("shopping:real_cart_add"), {"variant_id": variant.pk, "quantity": 1}).status_code == 400
    assert post_json(client, reverse("shopping:real_cart_update", args=[variant.pk]), {"quantity": 0}).status_code == 200


@pytest.mark.django_db
def test_stock_reduction_flags_old_cart_without_deleting_line(client, real_cart_item):
    buyer, _, _, variant, stock = real_cart_item
    client.force_login(buyer)
    post_json(client, reverse("shopping:real_cart_add"), {"variant_id": variant.pk, "quantity": 4})
    stock.quantity = 2
    stock.save(update_fields=["quantity"])
    snapshot = client.get(reverse("shopping:real_cart_get")).json()
    assert snapshot["items"][0]["is_available"] is False
    assert snapshot["items"][0]["available_quantity"] == 2
    assert snapshot["subtotal"] == "0.00"
    assert post_json(client, reverse("shopping:real_cart_update", args=[variant.pk]), {"quantity": 2}).status_code == 200


@pytest.mark.django_db
def test_invalid_requests_do_not_change_cart(client, real_cart_item):
    buyer, _, _, variant, _ = real_cart_item
    client.force_login(buyer)
    add = reverse("shopping:real_cart_add")
    for payload in ({"variant_id": variant.pk, "quantity": True},
                    {"variant_id": variant.pk, "quantity": 0},
                    {"variant_id": variant.pk, "quantity": "2"},
                    {"variant_id": -1, "quantity": 1}):
        assert post_json(client, add, payload).status_code == 400
    assert client.post(add, "not-json", content_type="application/json").status_code == 400
    assert client.post(add, "hello", content_type="text/plain").status_code == 400
    assert not CartItem.objects.filter(cart__user=buyer).exists()


@pytest.mark.django_db
def test_real_cart_mutations_require_csrf(real_cart_item):
    buyer, _, _, variant, _ = real_cart_item
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(buyer)
    response = post_json(strict, reverse("shopping:real_cart_add"), {"variant_id": variant.pk, "quantity": 1})
    assert response.status_code == 403


@pytest.mark.django_db
def test_drawer_api_config_and_product_action_render(client, real_cart_item):
    buyer, _, product, _, _ = real_cart_item
    client.force_login(buyer)
    html = client.get(reverse("catalog:marketplace_detail", args=[product.slug])).content.decode()
    assert 'id="real-cart-api"' in html
    assert 'data-add-real-bag' in html
    assert reverse("shopping:real_cart_add") in html
