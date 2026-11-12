"""Shared UX regression checks for storefront, marketplace, and seller journeys."""

import pytest
from django.urls import reverse


def test_home_links_to_approved_marketplace(client):
    response = client.get(reverse("core:home"))
    assert response.status_code == 200
    html = response.content.decode()
    assert "Explore seller listings" in html
    assert reverse("catalog:marketplace_list") in html
    assert "Demo products, wishlist and shopping bag" in html


def test_shared_footer_and_cart_copy_is_accurate(client):
    response = client.get(reverse("core:home"))
    html = response.content.decode()
    assert "Checkout not yet live" in html
    assert "Approved seller listings" in html
    assert "Demo shopping bag" in html
    assert "Inventory, live cart, checkout and payments are not implemented yet" not in html


def test_demo_wishlist_explains_local_storage(client):
    response = client.get(reverse("shopping:wishlist"))
    assert response.status_code == 200
    html = response.content.decode()
    assert "Demo wishlist saved in this browser" in html
    assert 'id="wishlist-grid"' in html


@pytest.mark.django_db
def test_approved_marketplace_empty_search_has_clear_action(client):
    response = client.get(reverse("catalog:marketplace_list"), {"q": "nonexistent-example"})
    assert response.status_code == 200
    html = response.content.decode()
    assert "No approved listings match" in html
    assert "Clear search" in html
    assert reverse("catalog:marketplace_list") in html
