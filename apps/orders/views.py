"""Authenticated order requests, tracking and seller-only status changes."""
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.catalog.services.products import require_seller_store

from .forms import CheckoutForm
from .models import Order, OrderItem
from .services import checkout_preview, customer_cancel, place_order, seller_transition


def _direct_params(request):
    raw_variant = request.POST.get("variant") if request.method == "POST" else request.GET.get("variant")
    raw_quantity = request.POST.get("quantity") if request.method == "POST" else request.GET.get("quantity")
    if raw_variant in (None, ""):
        return None, 1
    try:
        variant_id = int(raw_variant)
        quantity = int(raw_quantity or "1")
    except (ValueError, TypeError):
        raise ValidationError("Invalid product selection.") from None
    if not (0 < variant_id and 1 <= quantity <= 99):
        raise ValidationError("Invalid product selection or quantity.")
    return variant_id, quantity


@login_required
def checkout(request):
    if request.method == "GET":
        request.session["order_checkout_token"] = str(uuid4())
    token = request.session.get("order_checkout_token")
    try:
        variant_id, quantity = _direct_params(request)
        lines, subtotal = checkout_preview(
            user=request.user, variant_id=variant_id, quantity=quantity
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
        return redirect("shopping:cart")

    quote = {
        "total": str(subtotal),
        "items": [[item["variant"].pk, item["quantity"]] for item in lines],
    }
    if request.method == "GET":
        request.session["order_checkout_quote"] = quote

    form = CheckoutForm(
        request.POST or None,
        initial={
            "contact_name": request.user.get_full_name() or "",
        },
    )
    if request.method == "POST":
        if request.POST.get("checkout_token") != token or not token:
            form.add_error(None, "Checkout expired. Reload this page and try again.")
        elif request.session.get("order_checkout_quote") != quote:
            form.add_error(None, "Your bag or prices changed. Reload checkout to review the current total.")
        elif form.is_valid():
            try:
                order = place_order(
                    user=request.user, token=token,
                    details=form.cleaned_data, variant_id=variant_id, quantity=quantity,
                    expected_total=subtotal,
                )
            except ValidationError as error:
                form.add_error(None, error)
            else:
                request.session.pop("order_checkout_token", None)
                request.session.pop("order_checkout_quote", None)
                messages.success(request, "Your cash-on-delivery order request was saved.")
                return redirect("orders:customer_order_detail", order_id=order.pk)
    return render(request, "orders/checkout.html", {
        "form": form, "lines": lines, "subtotal": subtotal, "checkout_token": token,
        "variant_id": variant_id, "quantity": quantity,
    })


@login_required
def customer_orders(request):
    orders = Order.objects.filter(buyer=request.user).prefetch_related("lines")
    return render(request, "orders/customer_orders.html", {"orders": orders})


@login_required
def customer_order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.filter(buyer=request.user).prefetch_related("lines"),
        pk=order_id,
    )
    return render(request, "orders/customer_order_detail.html", {"order": order})


@login_required
@require_POST
def customer_cancel_line(request, line_id):
    try:
        line = customer_cancel(user=request.user, line_id=line_id)
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
        return redirect("orders:customer_orders")
    messages.success(request, "The pending item was cancelled and reserved stock released.")
    return redirect("orders:customer_order_detail", order_id=line.order_id)


@login_required
def seller_orders(request):
    store = require_seller_store(request.user)
    lines = OrderItem.objects.filter(store=store).select_related(
        "order", "order__buyer", "variant"
    ).order_by("-order__created_at", "-pk")[:150]
    return render(request, "orders/seller_orders.html", {"store": store, "lines": lines})


@login_required
@require_POST
def seller_update_line(request, line_id):
    store = require_seller_store(request.user)
    line = get_object_or_404(OrderItem.objects.filter(store=store), pk=line_id)
    try:
        seller_transition(
            seller=request.user, line_id=line.pk,
            new_status=request.POST.get("status", ""),
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    else:
        messages.success(request, "Order status updated.")
    return redirect("orders:seller_orders")
