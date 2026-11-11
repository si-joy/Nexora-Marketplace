"""Temporary catalog JSON is deliberately limited to non-sensitive public sample data."""
from .demo_data import DEMO_CATEGORIES, DEMO_PRODUCTS


def demo_catalog(request):
    return {"demo_catalog_products": DEMO_PRODUCTS, "demo_categories": DEMO_CATEGORIES}
