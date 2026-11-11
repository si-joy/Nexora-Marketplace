from django.urls import reverse


def test_old_cart_url_redirects_to_shop_drawer(client):
    response = client.get(reverse("shopping:cart"))
    assert response.status_code == 302
    assert response.url == f"{reverse('catalog:shop')}?cart=open"


def test_shared_cart_drawer_is_rendered_on_home_and_shop(client):
    for url in (reverse("core:home"), reverse("catalog:shop")):
        response = client.get(url)
        assert response.status_code == 200
        assert b'id="cart-drawer"' in response.content
        assert b'data-open-bag' in response.content
        assert b'data-cart-subtotal' in response.content
        assert b'data-add-bag' in response.content


def test_wishlist_includes_cards_for_saved_demo_ids(client):
    response = client.get(reverse("shopping:wishlist"))
    assert response.status_code == 200
    assert b"Your wishlist" in response.content
    assert b'id="wishlist-grid"' in response.content
    assert b'data-product-id="studio-headphones"' in response.content
    assert b'demo-catalog-json' in response.content
