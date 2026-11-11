"""Admin catalog moderation; seller-originated product details remain read-only here."""
from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import Brand, Category, Currency, Product, ProductImage, ProductVariant, ProductVariantPrice
from .services import approve_product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "is_active", "sort_order")
    search_fields = ("name", "slug")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "symbol", "decimal_places", "is_active")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "store", "category", "status", "created_at", "published_at")
    search_fields = ("name", "slug", "store__name")
    list_filter = ("status", "category")
    readonly_fields = (
        "store", "category", "brand", "name", "slug", "short_description",
        "description", "status", "moderation_note", "reviewed_by", "published_at",
        "created_at", "updated_at",
    )
    actions = ("approve_selected", "reject_selected")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _review(self, request, queryset, approve):
        count = 0
        for pk in queryset.values_list("pk", flat=True):
            try:
                approve_product(reviewer=request.user, product_id=pk, approve=approve)
            except ValidationError as error:
                self.message_user(request, f"Product #{pk}: {error}", level=messages.WARNING)
            else:
                count += 1
        self.message_user(request, f"{count} products reviewed.", level=messages.SUCCESS)

    @admin.action(description="Approve selected pending products")
    def approve_selected(self, request, queryset):
        self._review(request, queryset, True)

    @admin.action(description="Reject selected pending products")
    def reject_selected(self, request, queryset):
        self._review(request, queryset, False)


class ReadOnlyCatalogAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ProductVariant)
class ProductVariantAdmin(ReadOnlyCatalogAdmin):
    list_display = ("sku", "product", "is_default", "is_active")


@admin.register(ProductVariantPrice)
class ProductVariantPriceAdmin(ReadOnlyCatalogAdmin):
    list_display = ("variant", "currency", "amount")


@admin.register(ProductImage)
class ProductImageAdmin(ReadOnlyCatalogAdmin):
    list_display = ("product", "image", "sort_order")
