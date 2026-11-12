"""End-to-end COD order requests and seller/customer stock permissions."""
from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Currency, Product, ProductVariant, ProductVariantPrice, Category
from apps.inventory.models import Stock, StockMovement
from apps.orders.models import Order, OrderItem
from apps.orders.services import checkout_preview, customer_cancel, place_order, seller_transition
from apps.shopping.models import Cart, CartItem
from apps.vendors.models import SellerProfile, Store

User = get_user_model()
ADDRESS = {
    "contact_name": "Sample Buyer", "phone": "01712345678",
    "address_line": "House 20, Road 15, Block A, Uttara",
    "area": "Dhaka", "postal_code": "1230", "notes": "",
}


@pytest.fixture
def order_context(db):
    seller = User.objects.create_user(email="order-seller@example.test", password="ValidPass123!")
    buyer = User.objects.create_user(email="order-buyer@example.test", password="ValidPass123!")
    stranger = User.objects.create_user(email="order-stranger@example.test", password="ValidPass123!")
    profile = SellerProfile.objects.create(
        user=seller, business_name="Order store", contact_phone="0123456789",
        status=SellerProfile.Status.APPROVED,
    )
    store = Store.objects.create(
        seller=profile, name="Order store", slug="order-store", status=Store.Status.ACTIVE,
    )
    category = Category.objects.create(name="Order audio", slug="order-audio", is_active=True)
    product = Product.objects.create(
        store=store, category=category, name="Order headphones",
        slug="order-headphones", status=Product.Status.PUBLISHED,
    )
    variant = ProductVariant.objects.create(product=product, sku="ORDER-H-01", is_default=True)
    bdt, _ = Currency.objects.get_or_create(
        code="BDT", defaults={"name": "Bangladeshi Taka", "symbol": "৳"}
    )
    price = ProductVariantPrice.objects.create(
        variant=variant, currency=bdt, amount=Decimal("650.00"),
        compare_at_amount=Decimal("950.00"),
    )
    stock = Stock.objects.create(variant=variant, quantity=5)
    return buyer, seller, stranger, store, product, variant, price, stock


def order_for(buyer, variant, quantity=2, **kwargs):
    return place_order(
        user=buyer, token=str(uuid4()), details=ADDRESS,
        variant_id=variant.pk, quantity=quantity, **kwargs,
    )


@pytest.mark.django_db
def test_direct_order_reserves_stock_and_snapshots_sale_price(order_context):
    buyer, seller, _, store, product, variant, price, stock = order_context
    order = order_for(buyer, variant)
    line = order.lines.get()
    assert order.buyer == buyer
    assert order.source == Order.Source.DIRECT
    assert order.subtotal_bdt == Decimal("1300.00")
    assert line.unit_price_bdt == Decimal("650.00")
    assert line.line_total_bdt == Decimal("1300.00")
    assert line.store_id == store.pk
    assert line.product_name == product.name
    stock.refresh_from_db()
    assert (stock.quantity, stock.reserved_quantity, stock.available) == (5, 2, 3)
    assert not StockMovement.objects.filter(stock=stock).exists()


@pytest.mark.django_db
def test_repeated_same_checkout_token_does_not_reserve_twice(order_context):
    buyer, _, _, _, _, variant, _, stock = order_context
    key = str(uuid4())
    first = place_order(user=buyer, token=key, details=ADDRESS, variant_id=variant.pk, quantity=2)
    second = place_order(user=buyer, token=key, details=ADDRESS, variant_id=variant.pk, quantity=2)
    assert first.pk == second.pk
    assert Order.objects.count() == 1
    stock.refresh_from_db()
    assert stock.reserved_quantity == 2


@pytest.mark.django_db
def test_invalid_out_of_stock_order_rolls_back_reservations(order_context):
    buyer, _, _, _, _, variant, _, stock = order_context
    with pytest.raises(ValidationError):
        order_for(buyer, variant, quantity=6)
    assert Order.objects.count() == 0
    stock.refresh_from_db()
    assert stock.reserved_quantity == 0


@pytest.mark.django_db
def test_order_uses_current_price_and_never_browsers_amount(order_context):
    buyer, _, _, _, _, variant, price, _ = order_context
    price.amount = Decimal("700.00")
    price.save(update_fields=["amount"])
    order = place_order(user=buyer, token=str(uuid4()), details=ADDRESS, variant_id=variant.pk, quantity=1)
    assert order.subtotal_bdt == Decimal("700.00")
    assert order.lines.get().unit_price_bdt == Decimal("700.00")


@pytest.mark.django_db
def test_cart_checkout_clears_only_real_items(order_context):
    buyer, _, _, _, _, variant, _, stock = order_context
    cart = Cart.objects.create(user=buyer)
    CartItem.objects.create(cart=cart, variant=variant, quantity=3)
    order = place_order(user=buyer, token=str(uuid4()), details=ADDRESS)
    assert order.source == Order.Source.CART
    assert not CartItem.objects.filter(cart=cart).exists()
    assert order.lines.get().quantity == 3
    stock.refresh_from_db()
    assert stock.available == 2


@pytest.mark.django_db
def test_customer_pending_cancellation_releases_stock_once(order_context):
    buyer, _, _, _, _, variant, _, stock = order_context
    order = order_for(buyer, variant)
    line = customer_cancel(user=buyer, line_id=order.lines.get().pk)
    assert line.status == OrderItem.Status.CANCELLED
    stock.refresh_from_db()
    assert stock.quantity == 5
    assert stock.reserved_quantity == 0
    with pytest.raises(ValidationError):
        customer_cancel(user=buyer, line_id=line.pk)
    stock.refresh_from_db()
    assert stock.reserved_quantity == 0


@pytest.mark.django_db
def test_seller_flow_delivers_and_audits_stock_exactly_once(order_context):
    buyer, seller, _, _, _, variant, _, stock = order_context
    order = order_for(buyer, variant)
    line = order.lines.get()
    for state in (OrderItem.Status.PROCESSING, OrderItem.Status.SHIPPED, OrderItem.Status.DELIVERED):
        seller_transition(seller=seller, line_id=line.pk, new_status=state)
    stock.refresh_from_db()
    assert (stock.quantity, stock.reserved_quantity) == (3, 0)
    history = StockMovement.objects.get(stock=stock)
    assert history.delta == -2
    assert history.before_quantity == 5 and history.after_quantity == 3
    with pytest.raises(ValidationError):
        seller_transition(seller=seller, line_id=line.pk, new_status=OrderItem.Status.DELIVERED)
    assert StockMovement.objects.filter(stock=stock).count() == 1


@pytest.mark.django_db
def test_seller_can_cancel_processing_and_release_stock(order_context):
    buyer, seller, _, _, _, variant, _, stock = order_context
    line = order_for(buyer, variant).lines.get()
    seller_transition(seller=seller, line_id=line.pk, new_status=OrderItem.Status.PROCESSING)
    seller_transition(seller=seller, line_id=line.pk, new_status=OrderItem.Status.CANCELLED)
    stock.refresh_from_db()
    assert stock.reserved_quantity == 0
    assert stock.quantity == 5


@pytest.mark.django_db
def test_foreign_customers_and_sellers_cannot_access_orders(client, order_context):
    buyer, seller, stranger, _, _, variant, _, _ = order_context
    order = order_for(buyer, variant)
    line = order.lines.get()
    client.force_login(stranger)
    assert client.get(reverse("orders:customer_order_detail", args=[order.pk])).status_code == 404
    assert client.post(reverse("orders:customer_cancel_line", args=[line.pk])).status_code == 403
    assert client.post(reverse("orders:seller_update_line", args=[line.pk]), {"status": "shipped"}).status_code == 403
    with pytest.raises(PermissionDenied):
        seller_transition(seller=stranger, line_id=line.pk, new_status=OrderItem.Status.CANCELLED)


@pytest.mark.django_db
def test_checkout_requires_login_and_valid_form(client, order_context):
    buyer, _, _, _, _, variant, _, _ = order_context
    url = reverse("orders:checkout") + f"?variant={variant.pk}"
    response = client.get(url)
    assert response.status_code == 302
    assert reverse("accounts:login") in response["Location"]
    client.force_login(buyer)
    response = client.get(url)
    assert response.status_code == 200
    assert b"Place COD order request" in response.content
    token = client.session["order_checkout_token"]
    invalid = client.post(reverse("orders:checkout"), {
        "checkout_token": token, "variant": str(variant.pk), "quantity": "1",
        "contact_name": "A", "phone": "no", "address_line": "Short", "area": "Dhaka",
    })
    assert invalid.status_code == 200
    assert Order.objects.count() == 0


@pytest.mark.django_db
def test_checkout_post_creates_order_and_redirects(client, order_context):
    buyer, _, _, _, _, variant, _, stock = order_context
    client.force_login(buyer)
    client.get(reverse("orders:checkout") + f"?variant={variant.pk}&quantity=2")
    token = client.session["order_checkout_token"]
    response = client.post(reverse("orders:checkout"), {
        **ADDRESS, "checkout_token": token, "variant": str(variant.pk),
        "quantity": "2", "agree": "on",
    })
    assert response.status_code == 302
    order = Order.objects.get(buyer=buyer)
    assert str(order.pk) in response["Location"]
    assert client.get(reverse("orders:customer_order_detail", args=[order.pk])).status_code == 200
    stock.refresh_from_db()
    assert stock.reserved_quantity == 2


@pytest.mark.django_db
def test_seller_orders_only_show_own_lines(client, order_context):
    buyer, seller, _, store, _, variant, _, _ = order_context
    order_for(buyer, variant)
    client.force_login(seller)
    response = client.get(reverse("orders:seller_orders"))
    assert response.status_code == 200
    assert b"Order headphones" in response.content
    client.force_login(buyer)
    assert client.get(reverse("orders:seller_orders")).status_code == 403


@pytest.mark.django_db
def test_post_actions_enforce_csrf(order_context):
    buyer, seller, _, _, _, variant, _, _ = order_context
    order = order_for(buyer, variant)
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(buyer)
    assert strict.post(reverse("orders:customer_cancel_line", args=[order.lines.get().pk])).status_code == 403


@pytest.mark.django_db
def test_demo_items_do_not_become_real_orders(order_context):
    buyer, _, _, _, _, variant, _, _ = order_context
    from apps.shopping.models import DemoCartItem
    cart = Cart.objects.create(user=buyer)
    DemoCartItem.objects.create(cart=cart, product_id="studio-headphones", quantity=1)
    with pytest.raises(ValidationError, match="empty"):
        place_order(user=buyer, token=str(uuid4()), details=ADDRESS)
    assert Order.objects.count() == 0


@pytest.mark.django_db
def test_multi_seller_cart_splits_lines_and_keeps_permissions(order_context):
    buyer, seller, stranger, store, _, first, _, first_stock = order_context
    other_seller = User.objects.create_user(email="order-second-seller@example.test", password="ValidPass123!")
    profile = SellerProfile.objects.create(
        user=other_seller, business_name="Another seller", contact_phone="01711000000",
        status=SellerProfile.Status.APPROVED,
    )
    other_store = Store.objects.create(
        seller=profile, name="Another store", slug="another-order-store", status=Store.Status.ACTIVE
    )
    category = first.product.category
    second_product = Product.objects.create(
        store=other_store, category=category, name="Second seller item",
        slug="second-seller-item", status=Product.Status.PUBLISHED,
    )
    second_variant = ProductVariant.objects.create(
        product=second_product, sku="ORDER-S-02", is_default=True,
    )
    bdt = Currency.objects.get(pk="BDT")
    ProductVariantPrice.objects.create(
        variant=second_variant, currency=bdt, amount=Decimal("100.00"),
    )
    second_stock = Stock.objects.create(variant=second_variant, quantity=4)
    cart = Cart.objects.create(user=buyer)
    CartItem.objects.create(cart=cart, variant=first, quantity=2)
    CartItem.objects.create(cart=cart, variant=second_variant, quantity=3)

    order = place_order(user=buyer, token=str(uuid4()), details=ADDRESS)
    assert order.lines.count() == 2
    assert order.subtotal_bdt == Decimal("1600.00")
    first_stock.refresh_from_db()
    second_stock.refresh_from_db()
    assert first_stock.reserved_quantity == 2
    assert second_stock.reserved_quantity == 3

    first_line = order.lines.get(store=store)
    second_line = order.lines.get(store=other_store)
    with pytest.raises(PermissionDenied):
        seller_transition(seller=seller, line_id=second_line.id, new_status="processing")
    seller_transition(seller=other_seller, line_id=second_line.id, new_status="processing")
    with pytest.raises(PermissionDenied):
        seller_transition(seller=other_seller, line_id=first_line.id, new_status="processing")


@pytest.mark.django_db
def test_customer_cannot_cancel_item_after_seller_accepts(order_context):
    buyer, seller, _, _, _, variant, _, stock = order_context
    line = order_for(buyer, variant).lines.get()
    seller_transition(seller=seller, line_id=line.id, new_status="processing")
    with pytest.raises(ValidationError):
        customer_cancel(user=buyer, line_id=line.id)
    stock.refresh_from_db()
    assert stock.reserved_quantity == 2


@pytest.mark.django_db
def test_order_creation_rejects_replay_token_from_another_user(order_context):
    buyer, _, stranger, _, _, variant, _, stock = order_context
    token = str(uuid4())
    order = place_order(user=buyer, token=token, details=ADDRESS, variant_id=variant.pk)
    with pytest.raises(ValidationError, match="token"):
        place_order(user=stranger, token=token, details=ADDRESS, variant_id=variant.pk)
    assert Order.objects.count() == 1
    stock.refresh_from_db()
    assert stock.reserved_quantity == 1


@pytest.mark.django_db
def test_checkout_rejects_price_change_since_customer_viewed_quote(client, order_context):
    buyer, _, _, _, _, variant, price, stock = order_context
    client.force_login(buyer)
    checkout_url = reverse("orders:checkout")
    page = client.get(checkout_url + f"?variant={variant.pk}&quantity=2")
    assert page.status_code == 200
    token = client.session["order_checkout_token"]
    price.amount = Decimal("675.00")
    price.save(update_fields=["amount"])
    response = client.post(checkout_url, {
        **ADDRESS, "checkout_token": token,
        "variant": str(variant.pk), "quantity": "2", "agree": "on",
    })
    assert response.status_code == 200
    assert b"prices changed" in response.content.lower()
    assert not Order.objects.exists()
    stock.refresh_from_db()
    assert stock.reserved_quantity == 0


@pytest.mark.django_db
def test_checkout_rejects_changed_cart_quantity_since_quote(client, order_context):
    buyer, _, _, _, _, variant, _, stock = order_context
    client.force_login(buyer)
    cart = Cart.objects.create(user=buyer)
    line = CartItem.objects.create(cart=cart, variant=variant, quantity=1)
    checkout_url = reverse("orders:checkout")
    page = client.get(checkout_url)
    assert page.status_code == 200
    token = client.session["order_checkout_token"]
    line.quantity = 2
    line.save(update_fields=["quantity"])
    response = client.post(checkout_url, {
        **ADDRESS, "checkout_token": token, "agree": "on",
    })
    assert response.status_code == 200
    assert b"bag or prices changed" in response.content
    assert Order.objects.count() == 0
    stock.refresh_from_db()
    assert stock.reserved_quantity == 0
