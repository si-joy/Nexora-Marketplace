import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
def test_register_creates_customer_and_signs_in(client):
    response = client.post(reverse("accounts:register"), {
        "first_name": "Joy", "last_name": "Shopper", "email": "Buyer@Example.com",
        "password1": "ComplexPass456!", "password2": "ComplexPass456!",
    })
    assert response.status_code == 302
    assert response.url == reverse("accounts:dashboard")
    assert User.objects.filter(email="buyer@example.com").exists()
    assert client.get(reverse("accounts:dashboard")).status_code == 200


@pytest.mark.django_db
def test_email_duplicate_is_case_insensitive(client):
    User.objects.create_user(email="customer@example.com", password="ComplexPass456!")
    response = client.post(reverse("accounts:register"), {
        "first_name": "A", "last_name": "B", "email": "CUSTOMER@example.com",
        "password1": "ComplexPass456!", "password2": "ComplexPass456!",
    })
    assert response.status_code == 200
    assert User.objects.count() == 1
    assert b"already exists" in response.content


@pytest.mark.django_db
def test_login_is_case_insensitive_and_logout_requires_post(client):
    User.objects.create_user(email="buyer@example.com", password="ComplexPass456!")
    response = client.post(reverse("accounts:login"), {
        "username": "BUYER@EXAMPLE.COM", "password": "ComplexPass456!"
    })
    assert response.status_code == 302
    assert client.get(reverse("accounts:logout")).status_code == 405
    assert client.post(reverse("accounts:logout")).status_code == 302
    assert client.get(reverse("accounts:dashboard")).status_code == 302


@pytest.mark.django_db
def test_unauthenticated_dashboard_redirects_to_login(client):
    response = client.get(reverse("accounts:dashboard"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_password_reset_email_contains_token(client):
    User.objects.create_user(email="buyer@example.com", password="ComplexPass456!")
    response = client.post(reverse("accounts:password_reset"), {"email": "buyer@example.com"})
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    assert "/account/password/reset/" in mail.outbox[0].body


@pytest.mark.django_db
def test_login_rejects_external_next_url(client):
    User.objects.create_user(email="buyer@example.com", password="ComplexPass456!")
    response = client.post(reverse("accounts:login") + "?next=https://example.net/evil", {
        "username": "buyer@example.com", "password": "ComplexPass456!",
    })
    assert response.status_code == 302
    assert response.url == reverse("accounts:dashboard")
