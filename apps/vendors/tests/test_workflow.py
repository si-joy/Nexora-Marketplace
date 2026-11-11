import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from apps.vendors.models import SellerProfile, Store
from apps.vendors.services import review_application, submit_application

User = get_user_model()


@pytest.fixture
def buyer(db):
    return User.objects.create_user(email="buyer@example.com", password="ComplexPass456!")


@pytest.fixture
def reviewer(db):
    return User.objects.create_superuser(email="staff@example.com", password="ComplexPass456!")


@pytest.mark.django_db
def test_application_requires_signin(client):
    assert client.get(reverse("vendors:apply")).status_code == 302


@pytest.mark.django_db
def test_apply_is_pending_and_not_approved_automatically(client, buyer):
    client.force_login(buyer)
    response = client.post(reverse("vendors:apply"), {
        "business_name": "Example Store", "contact_phone": "+880123456789",
        "description": "Electronics and gadgets",
    })
    assert response.status_code == 302
    profile = SellerProfile.objects.get(user=buyer)
    assert profile.status == SellerProfile.Status.PENDING
    assert not Store.objects.filter(seller=profile).exists()
    dashboard = client.get(reverse("vendors:dashboard"))
    assert dashboard.status_code == 200
    assert b"Application status" in dashboard.content


@pytest.mark.django_db
def test_only_staff_with_permission_can_approve(buyer, reviewer):
    profile = submit_application(
        user=buyer, business_name="Example Store", contact_phone="+880123456789"
    )
    with pytest.raises(PermissionDenied):
        review_application(profile_id=profile.pk, reviewer=buyer, decision="approve")
    profile.refresh_from_db()
    assert profile.status == SellerProfile.Status.PENDING
    profile = review_application(profile_id=profile.pk, reviewer=reviewer, decision="approve")
    assert profile.status == SellerProfile.Status.APPROVED
    assert profile.store.status == Store.Status.ACTIVE
    assert Store.objects.count() == 1


@pytest.mark.django_db
def test_approved_seller_dashboard_and_suspend(client, buyer, reviewer):
    profile = submit_application(
        user=buyer, business_name="Example Store", contact_phone="+880123456789"
    )
    review_application(profile_id=profile.pk, reviewer=reviewer, decision="approve")
    client.force_login(buyer)
    response = client.get(reverse("vendors:dashboard"))
    assert response.status_code == 200
    assert b"Example Store" in response.content
    review_application(profile_id=profile.pk, reviewer=reviewer, decision="suspend")
    dashboard = client.get(reverse("vendors:dashboard"))
    assert b"Suspended" in dashboard.content
    assert Store.objects.get(seller=profile).status == Store.Status.SUSPENDED


@pytest.mark.django_db
def test_rejected_seller_can_reapply(client, buyer, reviewer):
    profile = submit_application(
        user=buyer, business_name="First Store", contact_phone="12345678"
    )
    review_application(profile_id=profile.pk, reviewer=reviewer, decision="reject")
    client.force_login(buyer)
    response = client.post(reverse("vendors:apply"), {
        "business_name": "Updated Store", "contact_phone": "23456789", "description": "Fresh"
    })
    assert response.status_code == 302
    profile.refresh_from_db()
    assert profile.business_name == "Updated Store"
    assert profile.status == SellerProfile.Status.PENDING
    assert profile.reviewed_by is None
    assert not Store.objects.filter(seller=profile).exists()


@pytest.mark.django_db
def test_application_not_duplicated_and_invalid_transition_rejected(buyer, reviewer):
    profile = submit_application(user=buyer, business_name="Store", contact_phone="123456789")
    with pytest.raises(ValidationError):
        submit_application(user=buyer, business_name="Another", contact_phone="123456789")
    with pytest.raises(ValidationError):
        review_application(profile_id=profile.pk, reviewer=reviewer, decision="suspend")
    assert SellerProfile.objects.count() == 1


@pytest.mark.django_db
def test_admin_can_review_before_approving(buyer, reviewer):
    profile = submit_application(user=buyer, business_name="Store One", contact_phone="123456789")
    profile = review_application(profile_id=profile.pk, reviewer=reviewer, decision="review")
    assert profile.status == SellerProfile.Status.UNDER_REVIEW
    assert not Store.objects.filter(seller=profile).exists()
    profile = review_application(profile_id=profile.pk, reviewer=reviewer, decision="approve")
    assert profile.status == SellerProfile.Status.APPROVED
    assert profile.store.status == Store.Status.ACTIVE
