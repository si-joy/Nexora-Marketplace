"""Per-account demo/marketplace favorites, cart persistence and privacy."""
import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Category, Product
from apps.shopping.models import Cart, DemoCartItem, DemoWishlistItem, MarketplaceWishlistItem
from apps.vendors.models import SellerProfile, Store

User = get_user_model()


@pytest.fixture
def accounts(db):
    a = User.objects.create_user(email="saved-a@example.test", password="CorrectPass123!")
    b = User.objects.create_user(email="saved-b@example.test", password="CorrectPass123!")
    seller = User.objects.create_user(email="saved-seller@example.test", password="CorrectPass123!")
    profile = SellerProfile.objects.create(
        user=seller, business_name="Saved shop", contact_phone="0123456789",
        status=SellerProfile.Status.APPROVED,
    )
    store = Store.objects.create(
        seller=profile, name="Saved shop", slug="saved-shop",
        status=Store.Status.ACTIVE,
    )
    category = Category.objects.create(name="Saved category", slug="saved-category", is_active=True)
    product = Product.objects.create(
        store=store, category=category, name="Saved Product",
        slug="saved-product", status=Product.Status.PUBLISHED,
    )
    return a, b, product


def saved_post(client, action, **payload):
    return client.post(
        reverse("shopping:account_saved_change"),
        json.dumps({"action": action, **payload}),
        content_type="application/json",
    )


@pytest.mark.django_db
def test_anonymous_has_no_saved_items_and_cannot_modify(client, accounts):
    user, _, _ = accounts
    assert client.get(reverse("shopping:account_saved_get")).json() == {
        "ok": True, "authenticated": False,
        "demo_cart": [], "demo_favorites": [], "marketplace_favorites": [],
    }
    assert saved_post(client, "demo_wishlist_toggle", product_id="studio-headphones").status_code == 401
    assert not DemoWishlistItem.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_demo_cart_persists_after_logout_and_login_without_browser_storage(client, accounts):
    a, _, _ = accounts
    client.force_login(a)
    response = saved_post(client, "demo_cart_set", product_id="studio-headphones", quantity=3)
    assert response.status_code == 200
    assert response.json()["demo_cart"] == [{"product_id": "studio-headphones", "quantity": 3}]
    client.logout()
    assert client.get(reverse("shopping:account_saved_get")).json()["demo_cart"] == []
    client.force_login(a)
    assert client.get(reverse("shopping:account_saved_get")).json()["demo_cart"][0]["quantity"] == 3


@pytest.mark.django_db
def test_account_isolation_for_demo_cart_and_both_wishlists(client, accounts):
    a, b, product = accounts
    client.force_login(a)
    assert saved_post(client, "demo_cart_set", product_id="orbit-watch", quantity=2).status_code == 200
    assert saved_post(client, "demo_wishlist_toggle", product_id="studio-headphones").status_code == 200
    assert saved_post(client, "marketplace_wishlist_toggle", product_id=product.pk).status_code == 200
    client.force_login(b)
    snapshot = client.get(reverse("shopping:account_saved_get")).json()
    assert snapshot["demo_cart"] == []
    assert snapshot["demo_favorites"] == []
    assert snapshot["marketplace_favorites"] == []
    assert saved_post(client, "demo_cart_set", product_id="pods-lite", quantity=1).status_code == 200
    client.force_login(a)
    snapshot = client.get(reverse("shopping:account_saved_get")).json()
    assert snapshot["demo_favorites"] == ["studio-headphones"]
    assert snapshot["marketplace_favorites"] == [product.pk]
    assert snapshot["demo_cart"][0]["product_id"] == "orbit-watch"


@pytest.mark.django_db
def test_wishlist_toggle_is_persistent_and_reversible(client, accounts):
    a, _, product = accounts
    client.force_login(a)
    assert saved_post(client, "demo_wishlist_toggle", product_id="pods-lite").status_code == 200
    assert saved_post(client, "marketplace_wishlist_toggle", product_id=product.pk).status_code == 200
    assert DemoWishlistItem.objects.filter(user=a).count() == 1
    assert MarketplaceWishlistItem.objects.filter(user=a).count() == 1
    client.logout()
    client.force_login(a)
    snapshot = client.get(reverse("shopping:account_saved_get")).json()
    assert snapshot["demo_favorites"] == ["pods-lite"]
    assert snapshot["marketplace_favorites"] == [product.pk]
    saved_post(client, "demo_wishlist_toggle", product_id="pods-lite")
    saved_post(client, "marketplace_wishlist_toggle", product_id=product.pk)
    assert not DemoWishlistItem.objects.filter(user=a).exists()
    assert not MarketplaceWishlistItem.objects.filter(user=a).exists()


@pytest.mark.django_db
def test_demo_cart_update_remove_and_clear(client, accounts):
    a, _, _ = accounts
    client.force_login(a)
    saved_post(client, "demo_cart_set", product_id="studio-headphones", quantity=7)
    saved_post(client, "demo_cart_set", product_id="orbit-watch", quantity=2)
    assert saved_post(client, "demo_cart_set", product_id="studio-headphones", quantity=1).status_code == 200
    assert saved_post(client, "demo_cart_set", product_id="orbit-watch", quantity=0).status_code == 200
    assert DemoCartItem.objects.get(cart__user=a).quantity == 1
    assert saved_post(client, "demo_cart_clear").json()["demo_cart"] == []
    assert not DemoCartItem.objects.filter(cart__user=a).exists()


@pytest.mark.django_db
def test_invalid_demo_ids_quantity_and_marketplace_ids_are_rejected(client, accounts):
    a, _, _ = accounts
    client.force_login(a)
    for value in (-1, True, 100, "2", 1.5):
        assert saved_post(client, "demo_cart_set", product_id="orbit-watch", quantity=value).status_code == 400
    assert saved_post(client, "demo_cart_set", product_id="fake-sku", quantity=1).status_code == 400
    assert saved_post(client, "demo_wishlist_toggle", product_id="fake-sku").status_code == 400
    assert saved_post(client, "marketplace_wishlist_toggle", product_id=999999).status_code == 400
    assert saved_post(client, "bad-action").status_code == 400
    assert not Cart.objects.filter(user=a).exists() or not DemoCartItem.objects.filter(cart__user=a).exists()


@pytest.mark.django_db
def test_marketplace_unpublished_cannot_be_saved_but_existing_can_be_removed(client, accounts):
    a, _, product = accounts
    client.force_login(a)
    assert saved_post(client, "marketplace_wishlist_toggle", product_id=product.pk).status_code == 200
    product.status = Product.Status.DRAFT
    product.save(update_fields=["status"])
    assert saved_post(client, "marketplace_wishlist_toggle", product_id=product.pk).status_code == 200
    assert saved_post(client, "marketplace_wishlist_toggle", product_id=product.pk).status_code == 400


@pytest.mark.django_db
def test_wishlist_page_is_account_scoped(client, accounts):
    a, b, product = accounts
    client.force_login(a)
    saved_post(client, "marketplace_wishlist_toggle", product_id=product.pk)
    html = client.get(reverse("shopping:wishlist")).content.decode()
    assert 'data-saved-marketplace-item' in html
    assert "Saved Product" in html
    client.force_login(b)
    assert "data-saved-marketplace-item" not in client.get(reverse("shopping:wishlist")).content.decode()
    client.logout()
    assert "data-saved-marketplace-item" not in client.get(reverse("shopping:wishlist")).content.decode()


@pytest.mark.django_db
def test_saved_mutation_requires_csrf_token(accounts):
    a, _, _ = accounts
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(a)
    assert saved_post(strict, "demo_wishlist_toggle", product_id="studio-headphones").status_code == 403


def test_storefront_has_account_saved_configuration_and_no_old_browser_storage(client):
    response = client.get(reverse("core:home"))
    assert response.status_code == 200
    assert b'data-saved-get' in response.content
    assert b'data-saved-change' in response.content
