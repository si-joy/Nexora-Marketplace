"""Account-owned marketplace bag; demo bag remains local to the browser."""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="marketplace_cart"
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Marketplace bag for user #{self.user_id}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        "catalog.ProductVariant", on_delete=models.PROTECT, related_name="cart_items"
    )
    quantity = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(99)]
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("cart", "variant"), name="shopping_unique_cart_variant"),
            models.CheckConstraint(condition=Q(quantity__gte=1, quantity__lte=99), name="shopping_item_quantity_range"),
        ]

    def __str__(self):
        return f"{self.variant.sku} × {self.quantity}"
