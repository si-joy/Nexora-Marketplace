"""Seller-scoped inventory changes with transaction and conditional-update guards.

SQLite supports local development. Test concurrent stock edits on PostgreSQL before launch.
"""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F

from apps.catalog.models import ProductVariant
from apps.catalog.services.products import require_seller_store

from .models import Stock, StockMovement


@transaction.atomic
def adjust_stock(*, seller, variant_id, delta, note=""):
    store = require_seller_store(seller)
    variant = (
        ProductVariant.objects.select_related("product")
        .filter(pk=variant_id, product__store=store)
        .first()
    )
    if variant is None:
        raise PermissionDenied("You cannot change stock belonging to another seller.")
    if type(delta) is not int or delta == 0 or abs(delta) > 100_000:
        raise ValidationError("Enter a nonzero whole-number adjustment (up to 100,000).")
    if not isinstance(note, str) or len(note) > 240:
        raise ValidationError("Enter a stock note of at most 240 characters.")

    stock, _ = Stock.objects.get_or_create(variant=variant)
    stock = Stock.objects.select_for_update().get(pk=stock.pk)
    if delta < 0 and stock.available < -delta:
        raise ValidationError("You cannot remove more than the available stock.")

    # Conditional atomic write prevents underflow even if another writer races.
    updated = Stock.objects.filter(
        pk=stock.pk, quantity__gte=F("reserved_quantity") - delta
    ).update(quantity=F("quantity") + delta)
    if updated != 1:
        raise ValidationError("Insufficient stock. Refresh the page and try again.")

    stock.refresh_from_db()
    StockMovement.objects.create(
        stock=stock,
        actor=seller,
        delta=delta,
        before_quantity=stock.quantity - delta,
        after_quantity=stock.quantity,
        reason=StockMovement.Reason.RECEIVE if delta > 0 else StockMovement.Reason.CORRECT,
        note=note.strip(),
    )
    return stock
