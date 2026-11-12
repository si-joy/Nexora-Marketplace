"""Public marketplace listings backed by SQLite/PostgreSQL, not demo JSON."""
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from apps.vendors.models import SellerProfile, Store
from .orm_selectors import live_products, search_live_products


def _product_highlights(product):
    lines = [line.strip("•- 	") for line in (product.description or "").splitlines() if line.strip()]
    if not lines and product.short_description:
        lines = [part.strip() for part in product.short_description.split("·") if part.strip()]
    bullets = lines[:5]
    if not bullets:
        bullets = [
            f"Category: {product.category.name}",
            f"Sold by: {product.store.name}",
        ]
        if product.brand:
            bullets.insert(1, f"Brand: {product.brand.name}")
        variant = product.shop_variant
        if variant and variant.sku:
            bullets.append(f"SKU: {variant.sku}")
    return bullets


def marketplace_list(request):
    query = request.GET.get("q", "").strip()[:120]
    items = search_live_products(query=query)
    page = Paginator(items, 12).get_page(request.GET.get("page"))
    return render(request, "catalog/public/marketplace_list.html", {"page": page, "query": query})


def marketplace_detail(request, slug):
    product = get_object_or_404(live_products(), slug=slug)
    gallery = list(product.images.all()[:5])
    product.shop_variant = next((variant for variant in product.variants.all() if variant.is_default and variant.is_active), None)
    return render(request, "catalog/public/marketplace_detail.html", {
        "product": product,
        "gallery": gallery,
        "highlights": _product_highlights(product),
        "specifications": list((product.specifications or {}).items()),
    })


def marketplace_store(request, slug):
    store = get_object_or_404(
        Store.objects.filter(status=Store.Status.ACTIVE, seller__status=SellerProfile.Status.APPROVED),
        slug=slug,
    )
    page = Paginator(live_products().filter(store=store), 12).get_page(request.GET.get("page"))
    return render(request, "catalog/public/marketplace_store.html", {"store": store, "page": page})
