"""Seller-only product management (all writes through services)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProductForm
from .models import Product
from .services.products import create_product, require_seller_store, submit_product, update_product


@login_required
def product_dashboard(request):
    store = require_seller_store(request.user)
    products = (Product.objects.filter(store=store)
                .select_related("category")
                .prefetch_related("images", "variants__prices__currency"))
    return render(request, "catalog/seller/product_dashboard.html", {"store": store, "products": products})


@login_required
def product_create(request):
    require_seller_store(request.user)
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            product = create_product(seller=request.user, cleaned=form.cleaned_data)
        except (IntegrityError, ValidationError) as error:
            form.add_error(None, "Unable to save product. Verify that the SKU is unique and try again.")
        else:
            messages.success(request, "Product draft saved. Submit it for review when ready.")
            return redirect("catalog:seller_product_edit", pk=product.pk)
    return render(request, "catalog/seller/product_form.html", {"form": form, "editing": False})


@login_required
def product_edit(request, pk):
    store = require_seller_store(request.user)
    product = get_object_or_404(
        Product.objects.filter(store=store).prefetch_related("images", "variants__prices__currency"), pk=pk
    )
    form = ProductForm(request.POST or None, request.FILES or None, product=product)
    if request.method == "POST" and form.is_valid():
        try:
            update_product(seller=request.user, product_id=product.pk, cleaned=form.cleaned_data)
        except (IntegrityError, ValidationError):
            form.add_error(None, "Unable to save product. Check the SKU and try again.")
        else:
            messages.success(request, "Product saved as draft; admin approval is needed to publish.")
            return redirect("catalog:seller_product_edit", pk=pk)
    return render(request, "catalog/seller/product_form.html", {
        "form": form, "editing": True, "product": product,
    })


@login_required
def product_submit(request, pk):
    if request.method != "POST":
        raise Http404("Not found")
    store = require_seller_store(request.user)
    product = get_object_or_404(Product, pk=pk, store=store)
    try:
        submit_product(seller=request.user, product_id=product.pk)
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    else:
        messages.success(request, "Product submitted for admin review.")
    return redirect("catalog:seller_product_edit", pk=pk)
