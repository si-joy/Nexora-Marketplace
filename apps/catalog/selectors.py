"""Read-only preview catalog selectors (will become ORM selectors later)."""
from .demo_data import DEMO_CATEGORIES, DEMO_PRODUCTS, DEMO_STORES


def list_products(*, category=None, query="", sort="featured"):
    items = [p for p in DEMO_PRODUCTS if not category or p["category_slug"] == category]
    if query:
        normalized = query.casefold().strip()
        items = [p for p in items if normalized in f'{p["name"]} {p["subtitle"]} {p["category"]}'.casefold()]
    if sort == "price_asc":
        items.sort(key=lambda p: p["price_value"])
    elif sort == "price_desc":
        items.sort(key=lambda p: p["price_value"], reverse=True)
    elif sort == "name":
        items.sort(key=lambda p: p["name"].casefold())
    return items


def get_product(slug):
    return next((p for p in DEMO_PRODUCTS if p["id"] == slug), None)


def get_category(slug):
    return next((c for c in DEMO_CATEGORIES if c["slug"] == slug), None)


def get_store(slug):
    return next((s for s in DEMO_STORES if s["slug"] == slug), None)


def get_store_products(slug):
    return [p for p in DEMO_PRODUCTS if p["store_slug"] == slug]
