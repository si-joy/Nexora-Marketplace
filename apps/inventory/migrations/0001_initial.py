# Inventory MVP. Reservation fields exist for future orders, not active checkout.
from django.conf import settings
from django.db import migrations, models
from django.db.models import F, Q
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("catalog", "0002_seed_bdt"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Stock",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("quantity", models.PositiveIntegerField(default=0)),
                ("reserved_quantity", models.PositiveIntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("variant", models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="stock", to="catalog.productvariant"
                )),
            ],
            options={"constraints": [
                models.CheckConstraint(condition=Q(quantity__gte=0), name="inv_qty_nonnegative"),
                models.CheckConstraint(condition=Q(reserved_quantity__gte=0), name="inv_reserved_nonnegative"),
                models.CheckConstraint(condition=Q(quantity__gte=F("reserved_quantity")), name="inv_reserved_within_qty"),
            ]},
        ),
        migrations.CreateModel(
            name="StockMovement",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("delta", models.IntegerField()),
                ("before_quantity", models.PositiveIntegerField()),
                ("after_quantity", models.PositiveIntegerField()),
                ("reason", models.CharField(
                    choices=[("receive", "Received / initial stock"), ("correct", "Adjustment")],
                    default="correct", max_length=12,
                )),
                ("note", models.CharField(blank=True, max_length=240)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    to=settings.AUTH_USER_MODEL
                )),
                ("stock", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="movements", to="inventory.stock"
                )),
            ],
            options={
                "ordering": ("-created_at", "-id"),
                "constraints": [
                    models.CheckConstraint(condition=~Q(delta=0), name="inv_nonzero_movement"),
                ],
            },
        ),
    ]
