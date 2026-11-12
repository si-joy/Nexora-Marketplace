"""Read-only order audit. Fulfillment must use stock-safe seller services."""
from django.contrib import admin

from .models import Order, OrderItem


class ImmutableOrderAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(ImmutableOrderAdmin):
    list_display = ("id", "buyer", "source", "subtotal_bdt", "created_at")
    list_filter = ("source", "created_at")
    search_fields = ("buyer__email", "contact_name", "phone", "id")
    readonly_fields = (
        "buyer", "checkout_token", "source", "contact_name", "phone",
        "address_line", "area", "postal_code", "notes", "subtotal_bdt", "created_at",
    )


@admin.register(OrderItem)
class OrderItemAdmin(ImmutableOrderAdmin):
    list_display = ("id", "order", "store", "product_name", "quantity", "status", "line_total_bdt")
    list_filter = ("status", "store")
    search_fields = ("order__id", "sku", "product_name", "store__name")
    readonly_fields = (
        "order", "store", "variant", "product_name", "sku", "store_name",
        "quantity", "unit_price_bdt", "line_total_bdt", "status", "updated_at",
    )
