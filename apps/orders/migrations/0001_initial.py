"""Additive order request and seller fulfillment schema."""
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("catalog", "0005_variant_compare_at_amount"),
        ("inventory", "0002_sync_implicit_primary_key_state"),
        ("vendors", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("checkout_token", models.CharField(max_length=36, unique=True)),
                ("source", models.CharField(choices=[("cart", "Marketplace bag"), ("direct", "Buy now")], default="cart", max_length=8)),
                ("contact_name", models.CharField(max_length=120)),
                ("phone", models.CharField(max_length=24)),
                ("address_line", models.CharField(max_length=255)),
                ("area", models.CharField(max_length=100)),
                ("postal_code", models.CharField(blank=True, max_length=16)),
                ("notes", models.CharField(blank=True, max_length=500)),
                ("subtotal_bdt", models.DecimalField(decimal_places=2, max_digits=13)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("buyer", models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name="marketplace_orders", on_delete=django.db.models.deletion.PROTECT)),
            ],
            options={"ordering": ("-created_at", "-id")},
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("product_name", models.CharField(max_length=200)),
                ("sku", models.CharField(max_length=80)),
                ("store_name", models.CharField(max_length=120)),
                ("quantity", models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ("unit_price_bdt", models.DecimalField(decimal_places=2, max_digits=12)),
                ("line_total_bdt", models.DecimalField(decimal_places=2, max_digits=13)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("processing", "Processing"), ("shipped", "Shipped"), ("delivered", "Delivered"), ("cancelled", "Cancelled")], default="pending", max_length=12)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("order", models.ForeignKey(to="orders.order", related_name="lines", on_delete=django.db.models.deletion.PROTECT)),
                ("store", models.ForeignKey(to="vendors.store", related_name="order_lines", on_delete=django.db.models.deletion.PROTECT)),
                ("variant", models.ForeignKey(to="catalog.productvariant", related_name="order_lines", on_delete=django.db.models.deletion.PROTECT)),
            ],
            options={
                "ordering": ("id",),
                "constraints": [
                    models.UniqueConstraint(fields=("order", "variant"), name="orders_unique_variant_per_order"),
                    models.CheckConstraint(condition=Q(quantity__gte=1), name="orders_positive_quantity"),
                    models.CheckConstraint(condition=Q(unit_price_bdt__gt=0), name="orders_positive_unit_price"),
                    models.CheckConstraint(condition=Q(line_total_bdt__gt=0), name="orders_positive_line_total"),
                ],
                "indexes": [models.Index(fields=("store", "status"), name="orders_store_status_idx")],
            },
        ),
    ]
