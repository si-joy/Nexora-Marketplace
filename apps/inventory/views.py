from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from apps.catalog.models import ProductVariant
from apps.catalog.services.products import require_seller_store

from .forms import StockAdjustmentForm
from .models import Stock, StockMovement
from .services import adjust_stock


@login_required
def inventory_list(request):
    store = require_seller_store(request.user)
    variants = (
        ProductVariant.objects.filter(product__store=store)
        .select_related("product", "product__category")
        .order_by("product__name", "sku")
    )
    stocks = {
        obj.variant_id: obj
        for obj in Stock.objects.filter(variant__product__store=store)
    }
    rows = []
    for variant in variants:
        stock = stocks.get(variant.pk)
        rows.append({
            "variant": variant,
            "quantity": stock.quantity if stock else 0,
            "available": stock.available if stock else 0,
            "reserved": stock.reserved_quantity if stock else 0,
        })
    return render(request, "inventory/list.html", {"rows": rows, "store": store})


@login_required
def inventory_adjust(request, variant_id):
    store = require_seller_store(request.user)
    variant = get_object_or_404(
        ProductVariant.objects.select_related("product"),
        pk=variant_id,
        product__store=store,
    )
    form = StockAdjustmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            adjust_stock(seller=request.user, variant_id=variant.pk, **form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Stock updated and recorded in the movement history.")
            return redirect("inventory:list")

    stock = Stock.objects.filter(variant=variant).first()
    movements = (
        StockMovement.objects.filter(stock=stock).select_related("actor")[:15]
        if stock else []
    )
    return render(request, "inventory/adjust.html", {
        "variant": variant,
        "form": form,
        "stock": stock,
        "movements": movements,
    })
