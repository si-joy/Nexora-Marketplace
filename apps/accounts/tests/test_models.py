import pytest

from apps.accounts.models import User


@pytest.mark.django_db
def test_user_login_is_email_and_password_is_hashed():
    user = User.objects.create_user("Example@DOMAIN.COM", "A-strong-test-password-123")
    assert user.email == "example@domain.com"
    assert user.username is None
    assert user.check_password("A-strong-test-password-123")


@pytest.mark.django_db
def test_superuser_has_required_privileges():
    user = User.objects.create_superuser("admin@example.com", "A-strong-test-password-123")
    assert user.is_staff and user.is_superuser
