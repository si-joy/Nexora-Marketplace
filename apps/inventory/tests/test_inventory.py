"""Regression tests for seller-scoped inventory and product stock initialization."""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from apps.catalog.models import Category, Product, ProductVariant
from apps.catalog.services.products import create_product
from apps.inventory.forms import StockAdjustmentForm
from apps.inventory.models import Stock, StockMovement
from apps.inventory.services import adjust_stock
from apps.vendors.models import SellerProfile, Store

User = get_user_model()


@pytest.fixture
def seller_stock(db):
    seller = User.objects.create_user(email="inventory-seller@example.com", password="ComplexPass456!")
    other = User.objects.create_user(email="inventory-other@example.com", password="ComplexPass456!")
    first_profile = SellerProfile.objects.create(
        user=seller, business_name="Seller One", contact_phone="12345678",
        status=SellerProfile.Status.APPROVED,
    )
    other_profile = SellerProfile.objects.create(
        user=other, business_name="Seller Two", contact_phone="12345678",
        status=SellerProfile.Status.APPROVED,
    )
    store = Store.objects.create(
        seller=first_profile, name="Seller One", slug="seller-one",
        status=Store.Status.ACTIVE,
    )
    Store.objects.create(
        seller=other_profile, name="Seller Two", slug="seller-two",
        status=Store.Status.ACTIVE,
    )
    category = Category.objects.create(name="Audio", slug="inventory-audio")
    product = Product.objects.create(
        store=store, category=category, name="Example Headphones",
        slug="inventory-headphones", status=Product.Status.PUBLISHED,
    )
    variant = ProductVariant.objects.create(
        product=product, sku="INVENTORY-TEST-01", is_default=True,
    )
    return seller, other, category, product, variant


@pytest.mark.django_db
def test_stock_adjustments_have_audited_before_and_after_values(seller_stock):
    seller, _, _, _, variant = seller_stock
    stock = adjust_stock(seller=seller, variant_id=variant.pk, delta=10, note="Delivered")
    assert stock.available == 10
    stock = adjust_stock(seller=seller, variant_id=variant.pk, delta=-3, note="Damaged")
    assert stock.available == 7
    assert list(StockMovement.objects.filter(stock=stock).values_list("delta", flat=True)) == [-3, 10]
    assert StockMovement.objects.filter(
        stock=stock, before_quantity=10, after_quantity=7, note="Damaged",
    ).exists()


@pytest.mark.django_db
def test_negative_adjustments_never_exceed_available(seller_stock):
    seller, _, _, _, variant = seller_stock
    stock = adjust_stock(seller=seller, variant_id=variant.pk, delta=6)
    stock.reserved_quantity = 4
    stock.save(update_fields=["reserved_quantity"])
    with pytest.raises(ValidationError):
        adjust_stock(seller=seller, variant_id=variant.pk, delta=-3)
    with pytest.raises(ValidationError):
        adjust_stock(seller=seller, variant_id=variant.pk, delta=0)
    stock.refresh_from_db()
    assert stock.quantity == 6
    assert stock.available == 2
    assert StockMovement.objects.filter(stock=stock).count() == 1


@pytest.mark.django_db
def test_seller_cannot_change_another_store_inventory(client, seller_stock):
    _, other, _, _, variant = seller_stock
    with pytest.raises(PermissionDenied):
        adjust_stock(seller=other, variant_id=variant.pk, delta=99)
    client.force_login(other)
    assert client.get(reverse("inventory:adjust", args=[variant.pk])).status_code == 404
    assert client.post(reverse("inventory:adjust", args=[variant.pk]), {"delta": 4}).status_code == 404
    assert not Stock.objects.filter(variant=variant).exists()


@pytest.mark.django_db
def test_inventory_views_and_stock_changes_do_not_reset_approval(client, seller_stock):
    seller, _, _, product, variant = seller_stock
    client.force_login(seller)
    assert client.get(reverse("inventory:list")).status_code == 200
    assert client.get(reverse("inventory:adjust", args=[variant.pk])).status_code == 200
    response = client.post(reverse("inventory:adjust", args=[variant.pk]), {
        "delta": 5, "note": "Received stock",
    })
    assert response.status_code == 302
    assert response.url == reverse("inventory:list")
    assert Stock.objects.get(variant=variant).quantity == 5
    product.refresh_from_db()
    assert product.status == Product.Status.PUBLISHED


@pytest.mark.django_db
def test_initial_stock_creates_one_audited_movement(seller_stock):
    seller, _, category, _, _ = seller_stock
    product = create_product(seller=seller, cleaned={
        "name": "New Stock Item", "category": category, "brand": None,
        "description": "", "short_description": "",
        "sku": "INITIAL-TEST-01", "price_bdt": Decimal("1200.00"),
        "initial_stock": 15,
    })
    variant = product.variants.get(is_default=True)
    assert variant.available_stock == 15
    stock = Stock.objects.get(variant=variant)
    move = StockMovement.objects.get(stock=stock)
    assert (move.before_quantity, move.after_quantity, move.delta) == (0, 15, 15)
    assert product.status == Product.Status.DRAFT


@pytest.mark.django_db
def test_initial_stock_validation_and_zero_default(seller_stock):
    seller, _, category, _, _ = seller_stock
    data = {
        "name": "Stock Validation", "category": category,
        "sku": "INITIAL-VALIDATE", "price_bdt": Decimal("500.00"),
    }
    with pytest.raises(ValidationError):
        create_product(seller=seller, cleaned={**data, "initial_stock": -1})
    assert not Product.objects.filter(name="Stock Validation").exists()
    product = create_product(seller=seller, cleaned=data)
    assert product.variants.get().available_stock == 0


def test_stock_adjustment_form_rejects_zero_and_fraction():
    assert not StockAdjustmentForm({"delta": 0}).is_valid()
    assert not StockAdjustmentForm({"delta": "1.5"}).is_valid()
    assert StockAdjustmentForm({"delta": "-2", "note": "Damaged"}).is_valid()
