from django.urls import reverse


def test_home_page_loads(client):
    response = client.get(reverse("core:home"))
    assert response.status_code == 200
    assert b"Trending right now" in response.content
    assert b"data-theme-toggle" in response.content
    assert b"data-product-id" in response.content
    assert b"data-add-bag" in response.content


def test_home_page_has_sample_products(client):
    response = client.get(reverse("core:home"))
    assert len(response.context["demo_products"]) == 4
    assert len(response.context["demo_categories"]) == 6
