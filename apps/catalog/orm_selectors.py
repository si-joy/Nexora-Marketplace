"""Optimized database reads for the real marketplace catalog (separate from demo)."""
from django.db.models import Q

from apps.vendors.models import SellerProfile, Store
from .models import Product


def live_products():
    return (Product.objects.filter(
        status=Product.Status.PUBLISHED,
        store__status=Store.Status.ACTIVE,
        store__seller__status=SellerProfile.Status.APPROVED,
        category__is_active=True,
    ).select_related("store", "category", "brand")
     .prefetch_related("images", "variants__prices__currency", "variants__stock"))


def search_live_products(query="", category=""):
    items = live_products()
    if query:
        items = items.filter(Q(name__icontains=query) | Q(short_description__icontains=query) | Q(variants__sku__icontains=query)).distinct()
    if category:
        items = items.filter(category__slug=category)
    return items
