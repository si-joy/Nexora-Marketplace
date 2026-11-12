"""Seller workspace keeps the left navigation, while panels load independently."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.catalog.models import Product
from apps.catalog.services.products import create_product
from apps.inventory.models import Stock
from apps.vendors.models import SellerProfile, Store

from apps.catalog.tests.test_real_catalog import approved_seller, category, cleaned
from apps.orders.tests.test_order_workflow import order_context, order_for

User = get_user_model()
DASH = "vendors:dashboard"


@pytest.mark.django_db
@pytest.mark.parametrize("tab,marker", [
    ("overview", "Your store at a glance"),
    ("products", "Manage products"),
    ("stock", "Stock overview"),
    ("orders", "Store orders"),
])
def test_workspace_keeps_sidebar_for_all_direct_tab_urls(client, approved_seller, tab, marker):
    seller, _, store = approved_seller
    client.force_login(seller)
    response = client.get(reverse(DASH), {"tab": tab})
    assert response.status_code == 200
    html = response.content.decode()
    assert 'data-seller-sidebar' in html
    assert 'data-seller-navigation' in html
    assert 'data-seller-panel' in html
    assert f'data-seller-panel-view="{tab}"' in html
    assert marker in html
    assert 'js/seller-workspace.js' in html
    assert response.context["active_tab"] == tab
    assert "no-store" in response.headers["Cache-Control"]


@pytest.mark.django_db
@pytest.mark.parametrize("tab", ["overview", "products", "stock", "orders"])
def test_ajax_returns_only_right_panel_not_full_page(client, approved_seller, tab):
    seller, _, _ = approved_seller
    client.force_login(seller)
    result = client.get(
        reverse(DASH), {"tab": tab}, HTTP_X_SELLER_PANEL="1",
    )
    assert result.status_code == 200
    html = result.content.decode()
    assert html.count('data-seller-panel-view=') == 1
    assert f'data-seller-panel-view="{tab}"' in html
    assert 'data-seller-sidebar' not in html
    assert "<html" not in html
    assert 'data-seller-workspace' not in html


@pytest.mark.django_db
def test_default_and_unknown_tabs_use_safe_overview(client, approved_seller):
    seller, _, _ = approved_seller
    client.force_login(seller)
    for query in ({}, {"tab": "not-real"}, {"tab": "../../../accounts"}):
        result = client.get(reverse(DASH), query)
        assert result.status_code == 200
        assert result.context["active_tab"] == "overview"
        assert b'data-seller-panel-view="overview"' in result.content


@pytest.mark.django_db
def test_tabs_only_show_this_store_products_and_stock(client, approved_seller, category):
    seller, _, store = approved_seller
    item = create_product(seller=seller, cleaned=cleaned(category))
    variant = item.variants.get(is_default=True)
    Stock.objects.create(variant=variant, quantity=7)

    stranger = User.objects.create_user(email="dashboard-other@example.test", password="ValidPass123!")
    other_profile = SellerProfile.objects.create(
        user=stranger, business_name="Private Seller", contact_phone="01700000000",
        status=SellerProfile.Status.APPROVED,
    )
    other_store = Store.objects.create(
        seller=other_profile, name="Private Store", slug="private-store", status=Store.Status.ACTIVE
    )
    Product.objects.create(
        store=other_store, category=category, name="Other seller secret listing",
        slug="secret-dashboard-listing", status=Product.Status.DRAFT,
    )
    client.force_login(seller)
    for tab in ("products", "stock"):
        result = client.get(reverse(DASH), {"tab": tab}, HTTP_X_SELLER_PANEL="1")
        assert result.status_code == 200
        html = result.content.decode()
        assert item.name in html
        assert "Other seller secret listing" not in html
    stock_html = client.get(reverse(DASH), {"tab": "stock"}).content.decode()
    assert "7" in stock_html
    assert variant.sku in stock_html


@pytest.mark.django_db
def test_product_panel_pagination_keeps_dashboard_url(client, approved_seller, category):
    seller, _, store = approved_seller
    Product.objects.bulk_create([
        Product(
            store=store, category=category, name=f"Sample Item {index:02}",
            slug=f"sample-item-{index:02}", status=Product.Status.DRAFT,
        ) for index in range(22)
    ])
    client.force_login(seller)
    response = client.get(reverse(DASH), {"tab": "products", "page": "2"})
    assert response.status_code == 200
    assert response.context["page"].number == 2
    assert 'data-seller-panel-link' in response.content.decode()
    assert "tab=products&page=1" in response.content.decode()


@pytest.mark.django_db
def test_customer_cannot_open_seller_panel(client):
    buyer = User.objects.create_user(email="dashboard-buyer@example.test", password="ValidPass123!")
    client.force_login(buyer)
    response = client.get(reverse(DASH), {"tab": "orders"}, HTTP_X_SELLER_PANEL="1")
    assert response.status_code == 302
    assert reverse("vendors:apply") in response["Location"]


@pytest.mark.django_db
def test_order_ajax_updates_only_right_panel_and_keeps_seller_access(client, order_context):
    buyer, seller, stranger, store, _, variant, _, stock = order_context
    order = order_for(buyer, variant)
    line = order.lines.get()
    client.force_login(seller)

    page = client.get(reverse(DASH), {"tab": "orders"}, HTTP_X_SELLER_PANEL="1")
    assert page.status_code == 200
    assert b"Order headphones" in page.content
    assert b'data-seller-order-form' in page.content

    response = client.post(
        reverse("orders:seller_update_line", args=[line.pk]),
        {"status": "processing"}, HTTP_X_SELLER_PANEL="1",
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    line.refresh_from_db()
    assert line.status == "processing"
    updated = client.get(reverse(DASH), {"tab": "orders"}, HTTP_X_SELLER_PANEL="1")
    assert b"Mark shipped" in updated.content

    # Validation must use the existing service and return an explicit JSON error.
    invalid = client.post(
        reverse("orders:seller_update_line", args=[line.pk]),
        {"status": "delivered"}, HTTP_X_SELLER_PANEL="1",
    )
    assert invalid.status_code == 400
    assert invalid.json()["ok"] is False

    # The old full-page POST still works when JavaScript is not available.
    normal = client.post(
        reverse("orders:seller_update_line", args=[line.pk]), {"status": "shipped"}
    )
    assert normal.status_code == 302
    assert normal["Location"] == reverse("orders:seller_orders")


@pytest.mark.django_db
def test_seller_panel_ajax_uses_existing_account_permissions(client, order_context):
    buyer, seller, stranger, store, _, variant, _, stock = order_context
    order = order_for(buyer, variant)
    client.force_login(stranger)
    response = client.post(
        reverse("orders:seller_update_line", args=[order.lines.get().pk]),
        {"status": "processing"}, HTTP_X_SELLER_PANEL="1",
    )
    assert response.status_code == 403
