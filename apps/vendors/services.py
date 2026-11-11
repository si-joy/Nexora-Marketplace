"""All seller-application transitions occur in one transaction."""

from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from .models import SellerProfile, Store


@transaction.atomic
def submit_application(*, user, business_name, contact_phone, description=""):
    if not user.is_authenticated:
        raise PermissionDenied("Sign in to apply as a seller.")
    # request.user may be a SimpleLazyObject. Resolve the concrete model,
    # locking its row on databases that support SELECT ... FOR UPDATE.
    user = get_user_model().objects.select_for_update().get(pk=user.pk)
    if not user.is_active:
        raise PermissionDenied("Sign in to apply as a seller.")
    profile, created = SellerProfile.objects.get_or_create(
        user=user,
        defaults={
            "business_name": business_name,
            "contact_phone": contact_phone,
            "description": description,
        },
    )
    if not created:
        if profile.status != SellerProfile.Status.REJECTED:
            raise ValidationError("You already have a seller application.")
        profile.business_name = business_name
        profile.contact_phone = contact_phone
        profile.description = description
        profile.status = SellerProfile.Status.PENDING
        profile.submitted_at = timezone.now()
        profile.reviewed_at = None
        profile.reviewed_by = None
        profile.review_note = ""
        profile.save(update_fields=[
            "business_name", "contact_phone", "description", "status", "submitted_at",
            "reviewed_at", "reviewed_by", "review_note",
        ])
    return profile


def _check_reviewer(reviewer):
    if not reviewer.is_authenticated or not reviewer.is_staff or not reviewer.has_perm(
        "vendors.change_sellerprofile"
    ):
        raise PermissionDenied("Only authorized administrators can review seller applications.")


@transaction.atomic
def review_application(*, profile_id, reviewer, decision, note=""):
    _check_reviewer(reviewer)
    profile = SellerProfile.objects.select_for_update().get(pk=profile_id)
    allowed = {
        "review": {SellerProfile.Status.PENDING},
        "approve": {SellerProfile.Status.PENDING, SellerProfile.Status.UNDER_REVIEW},
        "reject": {SellerProfile.Status.PENDING, SellerProfile.Status.UNDER_REVIEW},
        "suspend": {SellerProfile.Status.APPROVED},
    }
    if decision not in allowed or profile.status not in allowed[decision]:
        raise ValidationError("This application cannot make the requested status transition.")

    new_status = {
        "review": SellerProfile.Status.UNDER_REVIEW,
        "approve": SellerProfile.Status.APPROVED,
        "reject": SellerProfile.Status.REJECTED,
        "suspend": SellerProfile.Status.SUSPENDED,
    }[decision]
    profile.status = new_status
    profile.reviewed_at = timezone.now()
    profile.reviewed_by = reviewer
    profile.review_note = note
    profile.save(update_fields=["status", "reviewed_at", "reviewed_by", "review_note"])

    if decision == "approve":
        Store.objects.get_or_create(
            seller=profile,
            defaults={
                "name": profile.business_name,
                "slug": f"{slugify(profile.business_name)[:115] or 'store'}-{uuid4().hex[:12]}",
                "description": profile.description,
                "status": Store.Status.ACTIVE,
            },
        )
    elif decision == "suspend":
        Store.objects.filter(seller=profile).update(status=Store.Status.SUSPENDED)
    return profile
