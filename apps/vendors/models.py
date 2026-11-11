from django.conf import settings
from django.db import models
from django.utils import timezone


class SellerProfile(models.Model):
    """A customer's optional seller application, reviewed by marketplace staff."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        UNDER_REVIEW = "under_review", "Under review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SUSPENDED = "suspended", "Suspended"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seller_profile"
    )
    business_name = models.CharField(max_length=120)
    contact_phone = models.CharField(max_length=30)
    description = models.TextField(max_length=1000, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    submitted_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="seller_reviews",
    )
    review_note = models.TextField(blank=True)

    class Meta:
        ordering = ("-submitted_at",)
        indexes = [models.Index(fields=["status", "submitted_at"], name="vendors_sel_status_97b0bf_idx")]

    def __str__(self):
        return f"{self.business_name} ({self.get_status_display()})"


class Store(models.Model):
    """One seller has one store in the MVP. Real products arrive in Phase 03."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"

    seller = models.OneToOneField(SellerProfile, on_delete=models.PROTECT, related_name="store")
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, max_length=160)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
