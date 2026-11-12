from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("catalog", "0002_seed_bdt"),
        ("inventory", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(name="Cart", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("user", models.OneToOneField(to=settings.AUTH_USER_MODEL, related_name="marketplace_cart", on_delete=django.db.models.deletion.CASCADE)),
        ]),
        migrations.CreateModel(name="CartItem", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False)),
            ("quantity", models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(99)])),
            ("added_at", models.DateTimeField(auto_now_add=True)),
            ("cart", models.ForeignKey(to="shopping.cart", related_name="items", on_delete=django.db.models.deletion.CASCADE)),
            ("variant", models.ForeignKey(to="catalog.productvariant", related_name="cart_items", on_delete=django.db.models.deletion.PROTECT)),
        ], options={"constraints": [
            models.UniqueConstraint(fields=("cart", "variant"), name="shopping_unique_cart_variant"),
            models.CheckConstraint(condition=models.Q(quantity__gte=1, quantity__lte=99), name="shopping_item_quantity_range"),
        ]}),
    ]
