"""Browser demo cart and authenticated database-backed marketplace cart APIs."""
import json

from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.cache import never_cache

from apps.catalog.demo_data import DEMO_PRODUCTS
from apps.catalog.orm_selectors import live_products

from .services import add_to_cart, cart_snapshot, clear_cart, set_cart_quantity
from .models import MarketplaceWishlistItem
from .saved_items import (saved_snapshot, change_demo_cart, clear_demo_cart, toggle_demo_wishlist, toggle_marketplace_wishlist)


def cart(request):
    return HttpResponseRedirect(f"{reverse('catalog:shop')}?cart=open")


@never_cache
def wishlist(request):
    marketplace_favorites = []
    if request.user.is_authenticated and request.user.is_active:
        ids = MarketplaceWishlistItem.objects.filter(user=request.user).values_list("product_id", flat=True)
        marketplace_favorites = list(live_products().filter(pk__in=ids))
    return render(request, "pages/wishlist.html", {"demo_products": DEMO_PRODUCTS, "marketplace_favorites": marketplace_favorites})


def _error(message, status=400):
    return JsonResponse({"ok": False, "error": message}, status=status)


def _json_body(request):
    if request.content_type != "application/json":
        raise ValidationError("Send an application/json request.")
    if len(request.body) > 4096:
        raise ValidationError("Request is too large.")
    try:
        value = json.loads(request.body)
    except (UnicodeDecodeError, ValueError):
        raise ValidationError("Invalid JSON request.") from None
    if not isinstance(value, dict):
        raise ValidationError("Expected a JSON object.")
    return value


def _positive_id(value):
    if type(value) is not int or value <= 0:
        raise ValidationError("Invalid product variant.")
    return value


def _auth_required(request):
    return request.user.is_authenticated and request.user.is_active


@never_cache
@require_GET
def real_cart_get(request):
    return JsonResponse(cart_snapshot(request.user))


@require_POST
def real_cart_add(request):
    if not _auth_required(request):
        return _error("Sign in to use your marketplace bag.", 401)
    try:
        data = _json_body(request)
        variant_id = _positive_id(data.get("variant_id"))
        return JsonResponse(add_to_cart(
            user=request.user, variant_id=variant_id, quantity=data.get("quantity")
        ))
    except ValidationError as error:
        return _error("; ".join(error.messages))


@require_POST
def real_cart_update(request, variant_id):
    if not _auth_required(request):
        return _error("Sign in to use your marketplace bag.", 401)
    try:
        data = _json_body(request)
        return JsonResponse(set_cart_quantity(
            user=request.user, variant_id=variant_id, quantity=data.get("quantity")
        ))
    except ValidationError as error:
        return _error("; ".join(error.messages))


@require_POST
def real_cart_clear(request):
    if not _auth_required(request):
        return _error("Sign in to use your marketplace bag.", 401)
    try:
        _json_body(request)
        return JsonResponse(clear_cart(user=request.user))
    except ValidationError as error:
        return _error("; ".join(error.messages))


@never_cache
@require_GET
def account_saved_get(request):
    return JsonResponse(saved_snapshot(request.user))


@require_POST
def account_saved_change(request):
    if not _auth_required(request):
        return _error("Sign in to save items to your account.", 401)
    try:
        data = _json_body(request)
        action = data.get("action")
        if action == "demo_cart_set":
            snapshot = change_demo_cart(
                user=request.user, product_id=data.get("product_id"),
                quantity=data.get("quantity"),
            )
        elif action == "demo_cart_clear":
            snapshot = clear_demo_cart(user=request.user)
        elif action == "demo_wishlist_toggle":
            snapshot = toggle_demo_wishlist(user=request.user, product_id=data.get("product_id"))
        elif action == "marketplace_wishlist_toggle":
            snapshot = toggle_marketplace_wishlist(user=request.user, product_id=data.get("product_id"))
        else:
            raise ValidationError("Unknown saved-item action.")
        return JsonResponse(snapshot)
    except ValidationError as error:
        return _error("; ".join(error.messages))
