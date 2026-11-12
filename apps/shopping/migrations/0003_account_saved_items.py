"""Account-owned demo bag and demo/marketplace wishlists.

Adds tables only. Older browser localStorage data is intentionally not imported
because it is not reliably attributable to the currently authenticated user.
"""
from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("shopping", "0002_sync_implicit_primary_key_state"),
        ("catalog", "0003_sync_implicit_primary_key_state"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="DemoCartItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("product_id", models.CharField(max_length=100)),
                ("quantity", models.PositiveSmallIntegerField(validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(99),
                ])),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                ("cart", models.ForeignKey(to="shopping.cart", related_name="demo_items", on_delete=django.db.models.deletion.CASCADE)),
            ],
            options={"constraints": [
                models.UniqueConstraint(fields=("cart", "product_id"), name="shopping_unique_demo_cart_item"),
                models.CheckConstraint(condition=models.Q(quantity__gte=1, quantity__lte=99), name="shopping_demo_cart_qty_range"),
            ]},
        ),
        migrations.CreateModel(
            name="DemoWishlistItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("product_id", models.CharField(max_length=100)),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name="demo_wishlist", on_delete=django.db.models.deletion.CASCADE)),
            ],
            options={"constraints": [
                models.UniqueConstraint(fields=("user", "product_id"), name="shopping_unique_demo_wishlist"),
            ]},
        ),
        migrations.CreateModel(
            name="MarketplaceWishlistItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                ("product", models.ForeignKey(to="catalog.product", related_name="saved_by_users", on_delete=django.db.models.deletion.CASCADE)),
                ("user", models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name="marketplace_wishlist", on_delete=django.db.models.deletion.CASCADE)),
            ],
            options={"constraints": [
                models.UniqueConstraint(fields=("user", "product"), name="shopping_unique_marketplace_wishlist"),
            ]},
        ),
    ]
