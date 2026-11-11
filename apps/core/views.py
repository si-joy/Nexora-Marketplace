from django.shortcuts import render

from apps.catalog.demo_data import DEMO_CATEGORIES, DEMO_PRODUCTS


def home(request):
    return render(request, "pages/home.html", {
        "demo_products": DEMO_PRODUCTS[:4],
        "demo_categories": DEMO_CATEGORIES,
    })
