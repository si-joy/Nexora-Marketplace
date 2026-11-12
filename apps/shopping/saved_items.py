"""Account-scoped demo cart and both wishlist types. No local-storage reliance."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from apps.catalog.demo_data import DEMO_PRODUCTS
from apps.catalog.models import Product
from apps.vendors.models import SellerProfile, Store

from .models import Cart, DemoCartItem, DemoWishlistItem, MarketplaceWishlistItem

DEMO_IDS = frozenset(product["id"] for product in DEMO_PRODUCTS)
MAX_DEMO_UNITS = 200
MAX_DEMO_PER_PRODUCT = 99


def saved_snapshot(user):
    if not user.is_authenticated or not user.is_active:
        return {
            "ok": True, "authenticated": False,
            "demo_cart": [], "demo_favorites": [], "marketplace_favorites": [],
        }
    demo_cart = list(
        DemoCartItem.objects.filter(cart__user=user)
        .order_by("pk").values("product_id", "quantity")
    )
    return {
        "ok": True,
        "authenticated": True,
        "demo_cart": demo_cart,
        "demo_favorites": list(
            DemoWishlistItem.objects.filter(user=user).order_by("pk")
            .values_list("product_id", flat=True)
        ),
        "marketplace_favorites": list(
            MarketplaceWishlistItem.objects.filter(user=user).order_by("pk")
            .values_list("product_id", flat=True)
        ),
    }


def _demo_product(product_id):
    if not isinstance(product_id, str) or product_id not in DEMO_IDS:
        raise ValidationError("Invalid demo product.")


@transaction.atomic
def change_demo_cart(*, user, product_id, quantity):
    _demo_product(product_id)
    if type(quantity) is not int or not 0 <= quantity <= MAX_DEMO_PER_PRODUCT:
        raise ValidationError("Quantity must be a whole number between 0 and 99.")

    cart, _ = Cart.objects.get_or_create(user=user)
    Cart.objects.select_for_update().get(pk=cart.pk)
    line = DemoCartItem.objects.filter(cart=cart, product_id=product_id).first()
    if quantity:
        total = DemoCartItem.objects.filter(cart=cart).aggregate(
            total=Sum("quantity")
        )["total"] or 0
        if total - (line.quantity if line else 0) + quantity > MAX_DEMO_UNITS:
            raise ValidationError("Maximum 200 demo units per bag.")
        if line:
            line.quantity = quantity
            line.save(update_fields=["quantity"])
        else:
            DemoCartItem.objects.create(cart=cart, product_id=product_id, quantity=quantity)
    elif line:
        line.delete()
    return saved_snapshot(user)


@transaction.atomic
def clear_demo_cart(*, user):
    DemoCartItem.objects.filter(cart__user=user).delete()
    return saved_snapshot(user)


@transaction.atomic
def toggle_demo_wishlist(*, user, product_id):
    _demo_product(product_id)
    item, created = DemoWishlistItem.objects.get_or_create(
        user=user, product_id=product_id
    )
    if not created:
        item.delete()
    return saved_snapshot(user)


@transaction.atomic
def toggle_marketplace_wishlist(*, user, product_id):
    if type(product_id) is not int or product_id <= 0:
        raise ValidationError("Invalid marketplace product.")
    # Existing entries remain removable if a seller's listing is unpublished.
    item = MarketplaceWishlistItem.objects.filter(
        user=user, product_id=product_id
    ).first()
    if item:
        item.delete()
        return saved_snapshot(user)
    if not Product.objects.filter(
        pk=product_id, status=Product.Status.PUBLISHED,
        category__is_active=True, store__status=Store.Status.ACTIVE,
        store__seller__status=SellerProfile.Status.APPROVED,
    ).exists():
        raise ValidationError("Marketplace listing is unavailable.")
    MarketplaceWishlistItem.objects.create(user=user, product_id=product_id)
    return saved_snapshot(user)
