"""Transactional manual COD checkout and stock-safe per-seller fulfillment.

No payment processing, shipping integrations, or automatic inventory release.
Stock is reserved when an order request is submitted; fulfilled on delivery.
"""
from decimal import Decimal
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F

from apps.catalog.models import ProductVariant
from apps.inventory.models import Stock, StockMovement
from apps.shopping.models import Cart, CartItem
from apps.shopping.services import _price, _sellable
from apps.catalog.services.products import require_seller_store

from .models import Order, OrderItem


def _items_for_checkout(user, *, variant_id=None, quantity=1):
    if variant_id is None:
        cart = Cart.objects.filter(user=user).first()
        if not cart:
            raise ValidationError("Your marketplace bag is empty.")
        items = list(CartItem.objects.filter(cart=cart).order_by("variant_id").values_list("variant_id", "quantity"))
        if not items:
            raise ValidationError("Your marketplace bag is empty.")
        return items

    if type(variant_id) is not int or variant_id <= 0:
        raise ValidationError("Select an available product.")
    if type(quantity) is not int or not 1 <= quantity <= 99:
        raise ValidationError("Choose a quantity from 1 to 99.")
    return [(variant_id, quantity)]


def checkout_preview(*, user, variant_id=None, quantity=1):
    data = _items_for_checkout(user, variant_id=variant_id, quantity=quantity)
    lines = []
    total = Decimal("0.00")
    for variant_id, count in data:
        variant = ProductVariant.objects.select_related(
            "product__store__seller", "product__category"
        ).filter(pk=variant_id).first()
        if variant is None or not _sellable(variant):
            raise ValidationError("A product is no longer available; update your bag.")
        price = _price(variant_id)
        stock = Stock.objects.filter(variant_id=variant_id).first()
        if price is None or not stock or stock.available < count:
            raise ValidationError(f"Not enough stock for {variant.product.name}; update your bag.")
        line_total = price * count
        total += line_total
        lines.append({"variant": variant, "quantity": count, "unit_price": price, "line_total": line_total})
    return lines, total


@transaction.atomic
def place_order(*, user, token, details, variant_id=None, quantity=1, expected_total=None):
    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied("Sign in before placing an order.")
    try:
        key = str(UUID(str(token)))
    except (ValueError, AttributeError, TypeError):
        raise ValidationError("Invalid checkout token. Reload checkout.") from None

    # Repeated submission of the same checkout page must not reserve twice.
    existing = Order.objects.filter(checkout_token=key).first()
    if existing:
        if existing.buyer_id != user.pk:
            raise ValidationError("Invalid checkout token. Reload checkout.")
        return existing

    # Serialize checkout of a given buyer's bag on databases with row locking.
    from django.contrib.auth import get_user_model
    get_user_model().objects.select_for_update().get(pk=user.pk)
    # A second concurrent request using the same token may have completed
    # while waiting for the buyer lock. Check again before reserving stock.
    existing = Order.objects.filter(checkout_token=key).first()
    if existing:
        if existing.buyer_id != user.pk:
            raise ValidationError("Invalid checkout token. Reload checkout.")
        return existing
    source = Order.Source.DIRECT if variant_id is not None else Order.Source.CART
    data = _items_for_checkout(user, variant_id=variant_id, quantity=quantity)
    lines = []
    total = Decimal("0.00")
    # Sort IDs to avoid cross-checkout deadlocks on PostgreSQL.
    for item_variant_id, count in sorted(data):
        variant = ProductVariant.objects.select_related(
            "product__store__seller", "product__category"
        ).filter(pk=item_variant_id).first()
        if variant is None or not _sellable(variant):
            raise ValidationError("A product is no longer available. Update your bag.")
        price = _price(item_variant_id)
        if price is None:
            raise ValidationError("A product has no valid price.")
        stock = Stock.objects.filter(variant_id=item_variant_id).first()
        if stock is None:
            raise ValidationError("A product has no available stock.")
        # Atomic conditional update protects against competing checkout requests.
        reserved = Stock.objects.filter(
            pk=stock.pk,
            quantity__gte=F("reserved_quantity") + count,
        ).update(reserved_quantity=F("reserved_quantity") + count)
        if reserved != 1:
            raise ValidationError(f"Not enough stock for {variant.product.name}.")
        total += price * count
        lines.append((variant, count, price))
    if expected_total is not None and total != Decimal(str(expected_total)):
        raise ValidationError("Prices changed during checkout. Reload checkout to review the latest total.")
    order = Order.objects.create(
        buyer=user, checkout_token=key, source=source, subtotal_bdt=total,
        contact_name=details["contact_name"], phone=details["phone"],
        address_line=details["address_line"], area=details["area"],
        postal_code=details.get("postal_code", ""),
        notes=details.get("notes", ""),
    )
    OrderItem.objects.bulk_create([
        OrderItem(
            order=order, variant=variant, store=variant.product.store,
            product_name=variant.product.name, sku=variant.sku,
            store_name=variant.product.store.name, quantity=count,
            unit_price_bdt=price, line_total_bdt=price * count,
        )
        for variant, count, price in lines
    ])
    if source == Order.Source.CART:
        CartItem.objects.filter(cart__user=user).delete()
    return order


@transaction.atomic
def customer_cancel(*, user, line_id):
    line = OrderItem.objects.select_for_update().select_related("order").filter(
        pk=line_id, order__buyer=user
    ).first()
    if line is None:
        raise PermissionDenied("You cannot cancel this order item.")
    if line.status != OrderItem.Status.PENDING:
        raise ValidationError("Only pending items can be cancelled. Contact the seller for later changes.")
    _release(line)
    line.status = OrderItem.Status.CANCELLED
    line.save(update_fields=["status", "updated_at"])
    return line


def _release(line):
    updated = Stock.objects.filter(
        variant_id=line.variant_id,
        reserved_quantity__gte=line.quantity,
    ).update(reserved_quantity=F("reserved_quantity") - line.quantity)
    if updated != 1:
        raise ValidationError("Stock reservation is inconsistent. Contact support.")


@transaction.atomic
def seller_transition(*, seller, line_id, new_status):
    store = require_seller_store(seller)
    line = OrderItem.objects.select_for_update().filter(pk=line_id, store=store).first()
    if line is None:
        raise PermissionDenied("This order item belongs to another store.")
    transitions = {
        OrderItem.Status.PENDING: {OrderItem.Status.PROCESSING, OrderItem.Status.CANCELLED},
        OrderItem.Status.PROCESSING: {OrderItem.Status.SHIPPED, OrderItem.Status.CANCELLED},
        OrderItem.Status.SHIPPED: {OrderItem.Status.DELIVERED},
    }
    if new_status not in transitions.get(line.status, set()):
        raise ValidationError("This order status transition is not allowed.")
    if new_status == OrderItem.Status.CANCELLED:
        _release(line)
    if new_status == OrderItem.Status.DELIVERED:
        stock = Stock.objects.select_for_update().filter(variant_id=line.variant_id).first()
        if stock is None:
            raise ValidationError("Reserved inventory was not found.")
        before = stock.quantity
        updated = Stock.objects.filter(
            pk=stock.pk,
            reserved_quantity__gte=line.quantity,
            quantity__gte=line.quantity,
        ).update(
            quantity=F("quantity") - line.quantity,
            reserved_quantity=F("reserved_quantity") - line.quantity,
        )
        if updated != 1:
            raise ValidationError("Insufficient reserved inventory for delivery.")
        StockMovement.objects.create(
            stock=stock, actor=seller, delta=-line.quantity,
            before_quantity=before, after_quantity=before-line.quantity,
            reason=StockMovement.Reason.CORRECT,
            note=f"Order #{line.order_id} line #{line.pk} delivered",
        )
    line.status = new_status
    line.save(update_fields=["status", "updated_at"])
    return line
