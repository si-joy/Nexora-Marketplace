"""Per-variant inventory and append-only stock movement history."""
from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Stock(models.Model):
    variant = models.OneToOneField(
        "catalog.ProductVariant", on_delete=models.PROTECT, related_name="stock"
    )
    quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=0), name="inv_qty_nonnegative"),
            models.CheckConstraint(condition=Q(reserved_quantity__gte=0), name="inv_reserved_nonnegative"),
            models.CheckConstraint(
                condition=Q(quantity__gte=F("reserved_quantity")),
                name="inv_reserved_within_qty",
            ),
        ]

    @property
    def available(self):
        return self.quantity - self.reserved_quantity

    def __str__(self):
        return f"{self.variant.sku}: {self.available} available"


class StockMovement(models.Model):
    """Audit entries are only created by inventory services, never manually edited."""
    class Reason(models.TextChoices):
        RECEIVE = "receive", "Received / initial stock"
        CORRECT = "correct", "Adjustment"

    stock = models.ForeignKey(Stock, on_delete=models.PROTECT, related_name="movements")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    delta = models.IntegerField()
    before_quantity = models.PositiveIntegerField()
    after_quantity = models.PositiveIntegerField()
    reason = models.CharField(
        max_length=12, choices=Reason.choices, default=Reason.CORRECT
    )
    note = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            models.CheckConstraint(condition=~Q(delta=0), name="inv_nonzero_movement")
        ]

    def __str__(self):
        return f"{self.stock.variant.sku}: {self.delta:+d}"
