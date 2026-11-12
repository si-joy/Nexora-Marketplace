"""Relational catalog. No order/cart side effects are performed in these models."""
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models import Q


def product_image_path(instance, filename):
    # Avoid using user-controlled filenames as storage paths.
    ext = Path(filename).suffix.lower()
    return f"catalog/products/{instance.product_id}/{uuid4().hex}{ext}"


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    parent = models.ForeignKey("self", null=True, blank=True, related_name="children", on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name_plural = "categories"

    def clean(self):
        super().clean()
        if not self.parent_id:
            return
        if self.pk and self.pk == self.parent_id:
            raise ValidationError({"parent": "A category cannot be its own parent."})
        seen = {self.pk}
        ancestor = self.parent
        while ancestor is not None:
            if ancestor.pk in seen:
                raise ValidationError({"parent": "Circular category hierarchy is not allowed."})
            seen.add(ancestor.pk)
            ancestor = ancestor.parent

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Currency(models.Model):
    """ISO currency codes. MVP seller pricing uses BDT; model allows expansion."""
    code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=60)
    symbol = models.CharField(max_length=8)
    decimal_places = models.PositiveSmallIntegerField(default=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("code",)

    def __str__(self):
        return self.code


class Product(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending review"
        PUBLISHED = "published", "Published"
        REJECTED = "rejected", "Rejected"
        ARCHIVED = "archived", "Archived"

    store = models.ForeignKey("vendors.Store", related_name="products", on_delete=models.PROTECT)
    category = models.ForeignKey(Category, related_name="products", on_delete=models.PROTECT)
    brand = models.ForeignKey(Brand, related_name="products", on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=225)
    short_description = models.CharField(max_length=240, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    moderation_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_catalog_products",
    )
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("store", "status", "-created_at"), name="cat_store_status_created_idx"),
            models.Index(fields=("category", "status"), name="cat_category_status_idx"),
        ]

    @property
    def primary_image(self):
        return next(iter(self.images.all()), None)

    @property
    def bdt_price(self):
        for variant in self.variants.all():
            if not variant.is_active:
                continue
            for price in variant.prices.all():
                if price.currency_id == "BDT":
                    return price.amount
        return None

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=80, unique=True)
    attributes = models.JSONField(default=dict, blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(fields=["product"], condition=Q(is_default=True), name="cat_one_default_variant"),
        ]

    @property
    def available_stock(self):
        try:
            return self.stock.available
        except ObjectDoesNotExist:
            return 0

    def __str__(self):
        return self.sku


class ProductVariantPrice(models.Model):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="prices")
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="variant_prices")
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["variant", "currency"], name="cat_unique_variant_currency"),
            models.CheckConstraint(condition=Q(amount__gt=0), name="cat_price_positive"),
        ]

    def __str__(self):
        return f"{self.currency_id} {self.amount}"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=product_image_path, max_length=300)
    alt_text = models.CharField(max_length=160, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sort_order", "id")

    def __str__(self):
        return f"Image for {self.product_id}"
