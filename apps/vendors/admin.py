from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import SellerProfile, Store
from .services import review_application


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ("business_name", "user", "status", "submitted_at", "reviewed_at")
    list_filter = ("status", "submitted_at")
    search_fields = ("business_name", "user__email")
    readonly_fields = (
        "user", "business_name", "contact_phone", "description", "submitted_at",
        "status", "reviewed_at", "reviewed_by", "review_note",
    )
    actions = ("mark_reviewing", "approve_selected", "reject_selected", "suspend_selected")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _run_action(self, request, queryset, decision):
        succeeded = 0
        for profile_id in queryset.values_list("pk", flat=True):
            try:
                review_application(profile_id=profile_id, reviewer=request.user, decision=decision)
            except ValidationError as error:
                self.message_user(request, f"Application #{profile_id}: {error}", messages.WARNING)
            else:
                succeeded += 1
        self.message_user(request, f"{succeeded} seller application(s) updated.", messages.SUCCESS)

    @admin.action(description="Mark pending applications under review")
    def mark_reviewing(self, request, queryset):
        self._run_action(request, queryset, "review")

    @admin.action(description="Approve selected pending sellers")
    def approve_selected(self, request, queryset):
        self._run_action(request, queryset, "approve")

    @admin.action(description="Reject selected pending sellers")
    def reject_selected(self, request, queryset):
        self._run_action(request, queryset, "reject")

    @admin.action(description="Suspend selected approved sellers")
    def suspend_selected(self, request, queryset):
        self._run_action(request, queryset, "suspend")


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "seller", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "slug", "seller__user__email")
    readonly_fields = ("seller", "name", "slug", "description", "status", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
