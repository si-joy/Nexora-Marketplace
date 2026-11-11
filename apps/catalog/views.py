from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render

from .demo_data import DEMO_CATEGORIES, DEMO_PRODUCTS, DEMO_STORES
from .selectors import get_category, get_product, get_store, get_store_products, list_products


def _demo_gallery(product):
    palettes = [
        (product["image"], f"product-art--{product['visual']}", "Main view"),
        (product["image"], "product-art--wearables", "Lifestyle view"),
        (product["image"], "product-art--computing", "Side detail"),
        (product["image"], "product-art--photography", "Packaging preview"),
        (product["image"], "product-art--lifestyle", "In-room styling"),
    ]
    gallery = []
    for index, (image, art_class, label) in enumerate(palettes, start=1):
        gallery.append({
            "src": image,
            "alt": f"{product['name']} {label.lower()}",
            "art_class": art_class,
            "label": label,
            "index": index,
        })
    return gallery


def product_list(request):
    query = request.GET.get("q", "")[:120].strip()
    category = request.GET.get("category", "")[:40]
    sort = request.GET.get("sort", "featured")
    if sort not in {"featured", "price_asc", "price_desc", "name"}:
        sort = "featured"
    if category and not get_category(category):
        category = ""
    items = list_products(category=category, query=query, sort=sort)
    page = Paginator(items, 6).get_page(request.GET.get("page", 1))
    return render(request, "pages/shop.html", {
        "page": page, "count": len(items), "query": query,
        "selected_category": category, "selected_sort": sort,
    })


def category_list(request):
    return render(request, "pages/categories.html", {"categories": DEMO_CATEGORIES})


def category_detail(request, slug):
    category = get_category(slug)
    if category is None:
        raise Http404("Category not found")
    return render(request, "pages/category_detail.html", {
        "category": category, "products": list_products(category=slug),
    })


def product_detail(request, slug):
    product = get_product(slug)
    if product is None:
        raise Http404("Product not found")
    related = [p for p in DEMO_PRODUCTS if p["id"] != slug and p["category_slug"] == product["category_slug"]][:4]
    if not related:
        related = [p for p in DEMO_PRODUCTS if p["id"] != slug][:4]
    return render(request, "pages/product_detail.html", {
        "product": product,
        "related": related,
        "gallery": _demo_gallery(product),
    })


def store_list(request):
    stores = [{**s, "product_count": len(get_store_products(s["slug"]))} for s in DEMO_STORES]
    return render(request, "pages/stores.html", {"stores": stores})


def store_detail(request, slug):
    store = get_store(slug)
    if store is None:
        raise Http404("Store not found")
    return render(request, "pages/store_detail.html", {"store": store, "products": get_store_products(slug)})
