"""Browser demo cart and authenticated database-backed marketplace cart APIs."""
import json

from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from apps.catalog.demo_data import DEMO_PRODUCTS

from .services import add_to_cart, cart_snapshot, clear_cart, set_cart_quantity


def cart(request):
    return HttpResponseRedirect(f"{reverse('catalog:shop')}?cart=open")


def wishlist(request):
    return render(request, "pages/wishlist.html", {"demo_products": DEMO_PRODUCTS})


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
