# Initial database-backed catalog schema for Nexora V6.
import apps.catalog.models.catalog
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("vendors", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Brand",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(max_length=140, unique=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ("name",)},
        ),
        migrations.CreateModel(
            name="Currency",
            fields=[
                ("code", models.CharField(max_length=3, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=60)),
                ("symbol", models.CharField(max_length=8)),
                ("decimal_places", models.PositiveSmallIntegerField(default=2)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ("code",)},
        ),
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(max_length=140, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="children", to="catalog.category")),
            ],
            options={"ordering": ("sort_order", "name"), "verbose_name_plural": "categories"},
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("slug", models.SlugField(max_length=225, unique=True)),
                ("short_description", models.CharField(blank=True, max_length=240)),
                ("description", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("pending", "Pending review"), ("published", "Published"), ("rejected", "Rejected"), ("archived", "Archived")], db_index=True, default="draft", max_length=12)),
                ("moderation_note", models.TextField(blank=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("brand", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="products", to="catalog.brand")),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="products", to="catalog.category")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_catalog_products", to=settings.AUTH_USER_MODEL)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="products", to="vendors.store")),
            ],
            options={"ordering": ("-created_at",), "indexes": [
                models.Index(fields=["store", "status", "-created_at"], name="cat_store_status_created_idx"),
                models.Index(fields=["category", "status"], name="cat_category_status_idx"),
            ]},
        ),
        migrations.CreateModel(
            name="ProductVariant",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("sku", models.CharField(max_length=80, unique=True)),
                ("attributes", models.JSONField(blank=True, default=dict)),
                ("is_default", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="variants", to="catalog.product")),
            ],
            options={"ordering": ("id",), "constraints": [
                models.UniqueConstraint(condition=models.Q(("is_default", True)), fields=("product",), name="cat_one_default_variant")
            ]},
        ),
        migrations.CreateModel(
            name="ProductImage",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("image", models.ImageField(max_length=300, upload_to=apps.catalog.models.catalog.product_image_path)),
                ("alt_text", models.CharField(blank=True, max_length=160)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="images", to="catalog.product")),
            ],
            options={"ordering": ("sort_order", "id")},
        ),
        migrations.CreateModel(
            name="ProductVariantPrice",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="variant_prices", to="catalog.currency")),
                ("variant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="prices", to="catalog.productvariant")),
            ],
            options={"constraints": [
                models.UniqueConstraint(fields=("variant", "currency"), name="cat_unique_variant_currency"),
                models.CheckConstraint(condition=models.Q(("amount__gt", 0)), name="cat_price_positive"),
            ]},
        ),
    ]
