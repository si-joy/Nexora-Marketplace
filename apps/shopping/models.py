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


class DemoCartItem(models.Model):
    """A sample-catalog selection belonging to one account, never localStorage."""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="demo_items")
    product_id = models.CharField(max_length=100)
    quantity = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(99)]
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("cart", "product_id"), name="shopping_unique_demo_cart_item"),
            models.CheckConstraint(condition=Q(quantity__gte=1, quantity__lte=99), name="shopping_demo_cart_qty_range"),
        ]


class DemoWishlistItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="demo_wishlist"
    )
    product_id = models.CharField(max_length=100)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("user", "product_id"), name="shopping_unique_demo_wishlist"),
        ]


class MarketplaceWishlistItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="marketplace_wishlist"
    )
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.CASCADE, related_name="saved_by_users"
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("user", "product"), name="shopping_unique_marketplace_wishlist"),
        ]
