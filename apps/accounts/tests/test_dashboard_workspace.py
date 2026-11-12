"""Account dashboard panels must stay account-scoped and preserve existing security."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.catalog.demo_data import DEMO_PRODUCTS
from apps.orders.models import OrderItem
from apps.orders.tests.test_order_workflow import order_context, order_for
from apps.shopping.models import (
    Cart, CartItem, DemoCartItem, DemoWishlistItem, MarketplaceWishlistItem,
)

User = get_user_model()
DASH = "accounts:dashboard"


@pytest.fixture
def customer(db):
    return User.objects.create_user(
        email="workspace-customer@example.test", password="CurrentPassword789!",
        first_name="Nexora", last_name="Member",
    )


@pytest.mark.django_db
def test_dashboard_redirects_anonymous_user(client):
    response = client.get(reverse(DASH), {"tab": "wishlist"}, HTTP_X_CUSTOMER_PANEL="1")
    assert response.status_code == 302
    assert reverse("accounts:login") in response["Location"]


@pytest.mark.django_db
@pytest.mark.parametrize("tab,heading", [
    ("overview", "QUICK ACTIONS"),
    ("orders", "My orders"),
    ("wishlist", "My wishlist"),
    ("bag", "Shopping bag"),
    ("password", "Change password"),
])
def test_customer_workspace_keeps_sidebar_on_direct_urls(client, customer, tab, heading):
    client.force_login(customer)
    response = client.get(reverse(DASH), {"tab": tab})
    assert response.status_code == 200
    html = response.content.decode()
    assert 'data-customer-sidebar' in html
    assert 'data-customer-navigation' in html
    assert 'data-customer-panel' in html
    assert f'data-customer-panel-view="{tab}"' in html
    assert 'js/customer-workspace.js' in html
    assert heading in html
    assert response.context["active_tab"] == tab
    assert "no-store" in response.headers["Cache-Control"]


@pytest.mark.django_db
@pytest.mark.parametrize("tab", ["overview", "orders", "wishlist", "bag", "password"])
def test_customer_panel_request_renders_only_right_side(client, customer, tab):
    client.force_login(customer)
    response = client.get(reverse(DASH), {"tab": tab}, HTTP_X_CUSTOMER_PANEL="1")
    assert response.status_code == 200
    html = response.content.decode()
    assert html.count('data-customer-panel-view=') == 1
    assert f'data-customer-panel-view="{tab}"' in html
    assert 'data-customer-sidebar' not in html
    assert "<html" not in html
    assert "data-customer-workspace" not in html


@pytest.mark.django_db
def test_invalid_tab_defaults_to_overview_and_post_other_tab_rejected(client, customer):
    client.force_login(customer)
    for params in ({}, {"tab": "../orders"}, {"tab": "unknown"}):
        response = client.get(reverse(DASH), params)
        assert response.status_code == 200
        assert response.context["active_tab"] == "overview"
    response = client.post(reverse(DASH) + "?tab=orders", {})
    assert response.status_code == 405


@pytest.mark.django_db
def test_saved_wishlist_is_account_owned_and_visible_in_partial(client, order_context):
    buyer, _, stranger, _, product, _, _, _ = order_context
    DemoWishlistItem.objects.create(user=buyer, product_id="studio-headphones")
    MarketplaceWishlistItem.objects.create(user=buyer, product=product)
    DemoWishlistItem.objects.create(user=stranger, product_id="orbit-watch")
    client.force_login(buyer)
    result = client.get(reverse(DASH), {"tab": "wishlist"}, HTTP_X_CUSTOMER_PANEL="1")
    assert result.status_code == 200
    html = result.content.decode()
    assert "Studio Wireless Headphones" in html
    assert product.name in html
    assert "Orbit Smartwatch" not in html
    assert 'data-account-remove-favorite' in html
    assert 'data-kind="demo"' in html
    assert 'data-kind="marketplace"' in html
    client.force_login(stranger)
    other = client.get(reverse(DASH), {"tab": "wishlist"}, HTTP_X_CUSTOMER_PANEL="1")
    assert "Studio Wireless Headphones" not in other.content.decode()


@pytest.mark.django_db
def test_bag_panel_shows_account_items_not_other_users(client, order_context):
    buyer, _, stranger, _, product, variant, _, _ = order_context
    cart = Cart.objects.create(user=buyer)
    DemoCartItem.objects.create(cart=cart, product_id="pods-lite", quantity=2)
    CartItem.objects.create(cart=cart, variant=variant, quantity=1)
    other_cart = Cart.objects.create(user=stranger)
    DemoCartItem.objects.create(cart=other_cart, product_id="orbit-watch", quantity=4)
    client.force_login(buyer)
    page = client.get(reverse(DASH), {"tab": "bag"}, HTTP_X_CUSTOMER_PANEL="1")
    assert page.status_code == 200
    html = page.content.decode()
    assert "Nova True Wireless Earbuds" in html
    assert "Order headphones" in html
    assert "Orbit Smartwatch" not in html
    assert 'data-account-bag-change' in html
    assert "Request COD checkout" in html
    assert "Only approved marketplace products can be ordered" in html


@pytest.mark.django_db
def test_dashboard_order_details_are_buyer_scoped(client, order_context):
    buyer, _, stranger, _, _, variant, _, _ = order_context
    order = order_for(buyer, variant)
    client.force_login(buyer)
    page = client.get(reverse(DASH), {
        "tab": "orders", "order": str(order.pk),
    }, HTTP_X_CUSTOMER_PANEL="1")
    assert page.status_code == 200
    html = page.content.decode()
    assert f"Order #{order.pk}" in html
    assert "Order headphones" in html
    assert "Delivery information" in html
    assert 'data-customer-order-cancel' in html
    assert 'data-customer-panel-link' in html

    client.force_login(stranger)
    assert client.get(reverse(DASH), {
        "tab": "orders", "order": str(order.pk),
    }, HTTP_X_CUSTOMER_PANEL="1").status_code == 404
    assert client.get(reverse(DASH), {
        "tab": "orders", "order": "not-a-number",
    }).status_code == 404


@pytest.mark.django_db
def test_customer_can_cancel_pending_order_without_redirect(client, order_context):
    buyer, _, _, _, _, variant, _, stock = order_context
    order = order_for(buyer, variant)
    line = order.lines.get()
    client.force_login(buyer)
    ajax = client.post(
        reverse("orders:customer_cancel_line", args=[line.pk]),
        HTTP_X_CUSTOMER_PANEL="1",
    )
    assert ajax.status_code == 200
    assert ajax.json() == {"ok": True}
    line.refresh_from_db()
    stock.refresh_from_db()
    assert line.status == OrderItem.Status.CANCELLED
    assert stock.reserved_quantity == 0
    second = client.post(
        reverse("orders:customer_cancel_line", args=[line.pk]),
        HTTP_X_CUSTOMER_PANEL="1",
    )
    assert second.status_code == 400
    assert second.json()["ok"] is False


@pytest.mark.django_db
def test_cancel_requires_ownership_even_with_ajax_header(client, order_context):
    buyer, _, stranger, _, _, variant, _, stock = order_context
    order = order_for(buyer, variant)
    client.force_login(stranger)
    response = client.post(
        reverse("orders:customer_cancel_line", args=[order.lines.get().pk]),
        HTTP_X_CUSTOMER_PANEL="1",
    )
    assert response.status_code == 403
    stock.refresh_from_db()
    assert stock.reserved_quantity == 2


@pytest.mark.django_db
def test_password_panel_validates_old_password_and_keeps_session(client, customer):
    client.force_login(customer)
    url = reverse(DASH) + "?tab=password"
    bad = client.post(url, {
        "old_password": "incorrect",
        "new_password1": "FreshStrongPassword2026!",
        "new_password2": "FreshStrongPassword2026!",
    }, HTTP_X_CUSTOMER_PANEL="1")
    assert bad.status_code == 200
    assert 'data-customer-panel-view="password"' in bad.content.decode()
    assert "Your old password was entered incorrectly" in bad.content.decode()
    customer.refresh_from_db()
    assert customer.check_password("CurrentPassword789!")

    good = client.post(url, {
        "old_password": "CurrentPassword789!",
        "new_password1": "FreshStrongPassword2026!",
        "new_password2": "FreshStrongPassword2026!",
    }, HTTP_X_CUSTOMER_PANEL="1")
    assert good.status_code == 200
    assert "Your password was updated successfully." in good.content.decode()
    customer.refresh_from_db()
    assert customer.check_password("FreshStrongPassword2026!")
    assert client.get(reverse(DASH), {"tab": "overview"}).status_code == 200


@pytest.mark.django_db
def test_password_panel_has_normal_post_fallback(client, customer):
    client.force_login(customer)
    response = client.post(reverse(DASH) + "?tab=password", {
        "old_password": "CurrentPassword789!",
        "new_password1": "NewUniquePassword123!",
        "new_password2": "NewUniquePassword123!",
    })
    assert response.status_code == 302
    assert response["Location"] == reverse(DASH)
    customer.refresh_from_db()
    assert customer.check_password("NewUniquePassword123!")
