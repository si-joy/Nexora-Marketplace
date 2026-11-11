"""Client-side demo shopping bag with a shared modal drawer on every page."""
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from apps.catalog.demo_data import DEMO_PRODUCTS


def cart(request):
    """Keep old /cart/ links working by opening the drawer on the Shop page."""
    return HttpResponseRedirect(f"{reverse('catalog:shop')}?cart=open")


def wishlist(request):
    """Render catalog cards; the browser filters these by saved wishlist IDs."""
    return render(request, "pages/wishlist.html", {"demo_products": DEMO_PRODUCTS})
