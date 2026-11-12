from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render

from .demo_data import DEMO_CATEGORIES, DEMO_PRODUCTS, DEMO_STORES
from .selectors import get_category, get_product, get_store, get_store_products, list_products


def _demo_gallery(product):
    """Five visibly distinct presentations of the ONE original demo illustration.

    These are styling/crop treatments, not additional product photographs.
    """
    views = (
        ("hero", "Main view", "Main", "Full product illustration"),
        ("detail", "Close-up", "Detail", "Zoomed illustration detail"),
        ("angle", "Tilted view", "Angle", "Stylized angled artwork"),
        ("outline", "Minimal view", "Minimal", "Clean monochrome presentation"),
        ("showcase", "Showcase", "Display", "Illustration on a contrasting backdrop"),
    )
    return [
        {
            "src": product["image"],
            "alt": f"{product['name']} – {description.lower()}",
            "art_class": f"product-art--{product['visual']}",
            "view": view,
            "label": label,
            "short_label": short,
            "description": description,
            "index": index,
        }
        for index, (view, label, short, description) in enumerate(views, start=1)
    ]

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
