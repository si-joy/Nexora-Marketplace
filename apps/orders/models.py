"""Order requests are snapshots. Each seller fulfills only their own lines."""
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Order(models.Model):
    class Source(models.TextChoices):
        CART = "cart", "Marketplace bag"
        DIRECT = "direct", "Buy now"

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="marketplace_orders"
    )
    checkout_token = models.CharField(max_length=36, unique=True)
    source = models.CharField(max_length=8, choices=Source.choices, default=Source.CART)
    contact_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=24)
    address_line = models.CharField(max_length=255)
    area = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=16, blank=True)
    notes = models.CharField(max_length=500, blank=True)
    subtotal_bdt = models.DecimalField(max_digits=13, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")

    @property
    def summary_status(self):
        states = set(self.lines.values_list("status", flat=True))
        if not states or states == {OrderItem.Status.CANCELLED}:
            return "Cancelled"
        if states == {OrderItem.Status.DELIVERED}:
            return "Delivered"
        if OrderItem.Status.SHIPPED in states:
            return "Partially shipped" if len(states) > 1 else "Shipped"
        if OrderItem.Status.DELIVERED in states:
            return "Partially delivered"
        if OrderItem.Status.PROCESSING in states:
            return "Processing"
        if states == {OrderItem.Status.PENDING}:
            return "Pending seller review"
        return "Partially cancelled"

    def __str__(self):
        return f"Order #{self.pk} for {self.buyer_id}"


class OrderItem(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="lines")
    store = models.ForeignKey(
        "vendors.Store", on_delete=models.PROTECT, related_name="order_lines"
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant", on_delete=models.PROTECT, related_name="order_lines"
    )
    product_name = models.CharField(max_length=200)
    sku = models.CharField(max_length=80)
    store_name = models.CharField(max_length=120)
    quantity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    unit_price_bdt = models.DecimalField(max_digits=12, decimal_places=2)
    line_total_bdt = models.DecimalField(max_digits=13, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(fields=("order", "variant"), name="orders_unique_variant_per_order"),
            models.CheckConstraint(condition=Q(quantity__gte=1), name="orders_positive_quantity"),
            models.CheckConstraint(condition=Q(unit_price_bdt__gt=0), name="orders_positive_unit_price"),
            models.CheckConstraint(condition=Q(line_total_bdt__gt=0), name="orders_positive_line_total"),
        ]
        indexes = [models.Index(fields=("store", "status"), name="orders_store_status_idx")]

    def __str__(self):
        return f"Order #{self.order_id} · {self.product_name} × {self.quantity}"
