from django.contrib import admin

from .models import Stock, StockMovement


class ReadOnlyInventoryAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Stock)
class StockAdmin(ReadOnlyInventoryAdmin):
    list_display = ("variant", "quantity", "reserved_quantity", "updated_at")
    search_fields = ("variant__sku", "variant__product__name")


@admin.register(StockMovement)
class StockMovementAdmin(ReadOnlyInventoryAdmin):
    list_display = ("stock", "delta", "reason", "actor", "created_at")
    search_fields = ("stock__variant__sku", "stock__variant__product__name")
    list_filter = ("reason", "created_at")
