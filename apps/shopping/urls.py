from django.urls import path

from . import views

app_name = "shopping"
urlpatterns = [
    path("cart/", views.cart, name="cart"),
    path("api/account-saved/", views.account_saved_get, name="account_saved_get"),
    path("api/account-saved/change/", views.account_saved_change, name="account_saved_change"),
    path("wishlist/", views.wishlist, name="wishlist"),
    path("api/market-cart/", views.real_cart_get, name="real_cart_get"),
    path("api/market-cart/add/", views.real_cart_add, name="real_cart_add"),
    path("api/market-cart/update/<int:variant_id>/", views.real_cart_update, name="real_cart_update"),
    path("api/market-cart/clear/", views.real_cart_clear, name="real_cart_clear"),
]
