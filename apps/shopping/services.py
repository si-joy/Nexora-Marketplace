"""Account-owned marketplace bag; never reserves stock or processes checkout."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.urls import reverse

from apps.catalog.models import Product, ProductVariant, ProductVariantPrice
from apps.inventory.models import Stock
from apps.vendors.models import SellerProfile, Store

from .models import Cart, CartItem

MAX_PER_PRODUCT = 99
MAX_CART_UNITS = 200


def _sellable(variant):
    p = variant.product
    return (
        variant.is_active and p.status == Product.Status.PUBLISHED
        and p.category.is_active and p.store.status == Store.Status.ACTIVE
        and p.store.seller.status == SellerProfile.Status.APPROVED
    )


def _price(variant_id):
    return ProductVariantPrice.objects.filter(
        variant_id=variant_id, currency_id="BDT", currency__is_active=True
    ).values_list("amount", flat=True).first()


def _stock(variant_id):
    record = Stock.objects.filter(variant_id=variant_id).first()
    return record.available if record else 0


def _variant(variant_id):
    obj = ProductVariant.objects.select_related(
        "product__store__seller", "product__category"
    ).filter(pk=variant_id).first()
    if obj is None or not _sellable(obj) or _price(variant_id) is None:
        raise ValidationError("This product is not available.")
    return obj


def cart_snapshot(user):
    if not user.is_authenticated:
        return {"ok": True, "authenticated": False, "items": [], "item_count": 0, "subtotal": "0.00"}
    cart = Cart.objects.filter(user=user).first()
    if cart is None:
        return {"ok": True, "authenticated": True, "items": [], "item_count": 0, "subtotal": "0.00"}

    lines = CartItem.objects.filter(cart=cart).select_related(
        "variant__product__store__seller", "variant__product__category"
    ).prefetch_related("variant__product__images").order_by("id")
    items = []
    total = Decimal("0.00")
    count = 0
    for line in lines:
        variant = line.variant
        p = variant.product
        available = _stock(variant.id)
        price = _price(variant.id)
        valid = _sellable(variant) and price is not None and available >= line.quantity
        line_total = price * line.quantity if valid else Decimal("0.00")
        total += line_total
        count += line.quantity
        image = p.primary_image
        items.append({
            "variant_id": variant.pk, "name": p.name, "store": p.store.name,
            "url": reverse("catalog:marketplace_detail", args=[p.slug]),
            "image_url": image.image.url if image else "",
            "quantity": line.quantity, "available_quantity": available,
            "is_available": valid, "line_total": str(line_total),
        })
    return {
        "ok": True, "authenticated": True, "items": items,
        "item_count": count, "subtotal": str(total),
    }


def _quantity(value, *, zero_allowed=False):
    if type(value) is not int or not (0 if zero_allowed else 1) <= value <= MAX_PER_PRODUCT:
        raise ValidationError("Quantity must be a whole number between 0 and 99." if zero_allowed else "Quantity must be a whole number between 1 and 99.")


@transaction.atomic
def add_to_cart(*, user, variant_id, quantity):
    _quantity(quantity)
    _variant(variant_id)
    cart, _ = Cart.objects.get_or_create(user=user)
    Cart.objects.select_for_update().get(pk=cart.pk)
    line = CartItem.objects.filter(cart=cart, variant_id=variant_id).first()
    desired = (line.quantity if line else 0) + quantity
    if desired > MAX_PER_PRODUCT:
        raise ValidationError("Maximum 99 units per product.")
    count = CartItem.objects.filter(cart=cart).aggregate(n=Sum("quantity"))["n"] or 0
    if count + quantity > MAX_CART_UNITS:
        raise ValidationError("Maximum 200 units in your bag.")
    if desired > _stock(variant_id):
        raise ValidationError("Insufficient available stock.")
    if line:
        line.quantity = desired
        line.save(update_fields=["quantity"])
    else:
        CartItem.objects.create(cart=cart, variant_id=variant_id, quantity=desired)
    return cart_snapshot(user)


@transaction.atomic
def set_cart_quantity(*, user, variant_id, quantity):
    _quantity(quantity, zero_allowed=True)
    cart = Cart.objects.filter(user=user).first()
    if cart is None:
        raise ValidationError("This product is not in your bag.")
    Cart.objects.select_for_update().get(pk=cart.pk)
    line = CartItem.objects.filter(cart=cart, variant_id=variant_id).first()
    if line is None:
        raise ValidationError("This product is not in your bag.")
    if quantity == 0:
        line.delete()
        return cart_snapshot(user)
    if quantity > line.quantity:
        _variant(variant_id)
        if quantity > _stock(variant_id):
            raise ValidationError("Insufficient available stock.")
        count = CartItem.objects.filter(cart=cart).aggregate(n=Sum("quantity"))["n"] or 0
        if count - line.quantity + quantity > MAX_CART_UNITS:
            raise ValidationError("Maximum 200 units in your bag.")
    line.quantity = quantity
    line.save(update_fields=["quantity"])
    return cart_snapshot(user)


@transaction.atomic
def clear_cart(*, user):
    cart = Cart.objects.filter(user=user).first()
    if cart is not None:
        Cart.objects.select_for_update().get(pk=cart.pk)
        cart.items.all().delete()
    return cart_snapshot(user)
