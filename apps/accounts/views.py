from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from django.http import HttpResponseNotAllowed
from django.views.decorators.cache import never_cache

from .forms import CustomerRegistrationForm, StyledPasswordChangeForm


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = CustomerRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome to Nexora! Your account is ready.")
        return redirect("accounts:dashboard")
    return render(request, "accounts/register.html", {"form": form})


CUSTOMER_TABS = frozenset({"overview", "orders", "wishlist", "bag", "password"})


@login_required
@never_cache
def dashboard(request):
    """Account-owned workspace with server-rendered panel navigation.

    GET without the panel header remains a fully navigable document. A
    requested X-Customer-Panel response contains only the right-hand panel.
    """
    from apps.catalog.demo_data import DEMO_PRODUCTS
    from apps.catalog.orm_selectors import live_products
    from apps.orders.models import Order
    from apps.shopping.models import (
        CartItem, DemoCartItem, DemoWishlistItem, MarketplaceWishlistItem,
    )
    from apps.shopping.services import cart_snapshot
    from apps.vendors.models import SellerProfile

    tab = request.GET.get("tab", "overview")
    if tab not in CUSTOMER_TABS:
        tab = "overview"
    if request.method != "GET" and not (request.method == "POST" and tab == "password"):
        return HttpResponseNotAllowed(["GET"])

    context = {"active_tab": tab}
    if tab == "overview":
        context.update({
            "seller_profile": SellerProfile.objects.filter(user=request.user).first(),
            "order_count": Order.objects.filter(buyer=request.user).count(),
            "wishlist_count": (
                DemoWishlistItem.objects.filter(user=request.user).count()
                + MarketplaceWishlistItem.objects.filter(user=request.user).count()
            ),
            "bag_count": (
                sum(DemoCartItem.objects.filter(cart__user=request.user)
                    .values_list("quantity", flat=True))
                + sum(CartItem.objects.filter(cart__user=request.user)
                    .values_list("quantity", flat=True))
            ),
        })
    elif tab == "orders":
        requested = request.GET.get("order")
        if requested:
            context["order_detail"] = get_object_or_404(
                Order.objects.filter(buyer=request.user).prefetch_related("lines"),
                pk=requested if requested.isdecimal() else -1,
            )
        else:
            orders = (
                Order.objects.filter(buyer=request.user)
                .prefetch_related("lines")
            )
            context["page"] = Paginator(orders, 15).get_page(request.GET.get("page"))
    elif tab == "wishlist":
        demo_ids = set(
            DemoWishlistItem.objects.filter(user=request.user)
            .values_list("product_id", flat=True)
        )
        context["demo_favorites"] = [
            product for product in DEMO_PRODUCTS if product["id"] in demo_ids
        ]
        saved_ids = MarketplaceWishlistItem.objects.filter(
            user=request.user
        ).values_list("product_id", flat=True)
        real_favorites = live_products().filter(pk__in=saved_ids).order_by("-pk")
        context["page"] = Paginator(real_favorites, 20).get_page(request.GET.get("page"))
    elif tab == "bag":
        saved_demo = {
            item["product_id"]: item["quantity"]
            for item in DemoCartItem.objects.filter(
                cart__user=request.user
            ).values("product_id", "quantity")
        }
        context["demo_lines"] = [
            {"product": product, "quantity": saved_demo[product["id"]]}
            for product in DEMO_PRODUCTS if product["id"] in saved_demo
        ]
        context["real_cart"] = cart_snapshot(request.user)
        context["can_checkout"] = bool(context["real_cart"]["items"]) and all(
            item["is_available"] for item in context["real_cart"]["items"]
        )
    elif tab == "password":
        context["password_changed"] = False
        form = StyledPasswordChangeForm(
            user=request.user, data=request.POST if request.method == "POST" else None,
        )
        if request.method == "POST" and form.is_valid():
            changed_user = form.save()
            update_session_auth_hash(request, changed_user)
            if request.headers.get("X-Customer-Panel") != "1":
                messages.success(request, "Your password has been updated.")
                return redirect("accounts:dashboard")
            context["password_changed"] = True
            form = StyledPasswordChangeForm(user=request.user)
        context["password_form"] = form

    if request.headers.get("X-Customer-Panel") == "1":
        return render(request, f"accounts/panels/{tab}.html", context)
    return render(request, "accounts/dashboard.html", context)
