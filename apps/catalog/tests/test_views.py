from django.urls import reverse


def test_shop_has_independent_page(client):
    response = client.get(reverse("catalog:shop"))
    assert response.status_code == 200
    assert b"Shop the collection" in response.content
    assert len(response.context["page"].object_list) == 6
    assert response.context["page"].has_next()


def test_product_search_is_server_side(client):
    response = client.get(reverse("catalog:shop"), {"q": "headphones"})
    assert response.status_code == 200
    assert response.context["count"] == 1
    # Page HTML also contains an embedded complete demo catalog JSON for the
    # browser-only cart. Check rendered product cards, not arbitrary text.
    assert b'data-product-id="studio-headphones"' in response.content
    assert b'data-product-id="metro-backpack"' not in response.content


def test_shop_category_filter_and_sort(client):
    response = client.get(reverse("catalog:shop"), {"category": "audio", "sort": "price_asc"})
    items = response.context["page"].object_list
    assert len(items) == 3
    assert [p["price_value"] for p in items] == [2490, 3790, 4990]


def test_category_listing_and_detail(client):
    assert client.get(reverse("catalog:categories")).status_code == 200
    response = client.get(reverse("catalog:category_detail", args=["gaming"]))
    assert response.status_code == 200
    assert b"Pulse Wireless Controller" in response.content
    assert client.get(reverse("catalog:category_detail", args=["missing"])).status_code == 404


def test_product_detail_and_404(client):
    response = client.get(reverse("catalog:product_detail", args=["orbit-watch"]))
    assert response.status_code == 200
    assert b"Orbit Smartwatch Series 5" in response.content
    assert b"data-add-bag" in response.content
    assert client.get(reverse("catalog:product_detail", args=["unknown"])).status_code == 404


def test_stores_are_separate_pages(client):
    assert client.get(reverse("catalog:stores")).status_code == 200
    response = client.get(reverse("catalog:store_detail", args=["northstar-audio"]))
    assert response.status_code == 200
    # A global demo-catalog JSON is present on every page; only this store's
    # product cards should appear in the rendered listing.
    assert b'data-product-id="studio-headphones"' in response.content
    assert b'data-product-id="airbook-laptop"' not in response.content
    assert client.get(reverse("catalog:store_detail", args=["unknown"])).status_code == 404


def test_demo_gallery_has_five_distinct_view_states(client):
    response = client.get(reverse("catalog:product_detail", args=["pods-lite"]))
    assert response.status_code == 200
    gallery = response.context["gallery"]
    assert len(gallery) == 5
    assert len({item["view"] for item in gallery}) == 5
    assert len({item["label"] for item in gallery}) == 5
    # One source illustration, honestly presented in five styles.
    assert len({item["src"] for item in gallery}) == 1
    html = response.content.decode()
    assert html.count("data-gallery-thumb ") == 5
    assert 'data-gallery-nav="prev"' in html
    assert 'data-gallery-nav="next"' in html
    assert 'data-gallery-position' in html
    assert 'data-gallery-title' in html
    assert 'data-gallery-description' in html
    assert 'data-detail-quantity' in html
    assert 'data-demo-qty-minus' in html
    assert 'data-demo-qty-plus' in html
    assert 'data-add-bag' in html
    assert 'data-favorite-toggle' in html


def test_demo_gallery_no_longer_claims_five_photographs(client):
    response = client.get(reverse("catalog:product_detail", args=["studio-headphones"]))
    html = response.content.decode()
    assert "5 Photos" not in html
    assert "Gallery preview" not in html
    assert "not additional product photos" in html
    assert "Details & specifications" in html
    assert "You may also like" in html
