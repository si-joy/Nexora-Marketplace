from django.urls import path

from . import public_views, seller_views, views

app_name = "catalog"
urlpatterns = [
    path("market/", public_views.marketplace_list, name="marketplace_list"),
    path("market/product/<slug:slug>/", public_views.marketplace_detail, name="marketplace_detail"),
    path("market/store/<slug:slug>/", public_views.marketplace_store, name="marketplace_store"),
    path("seller/products/", seller_views.product_dashboard, name="seller_products"),
    path("seller/products/new/", seller_views.product_create, name="seller_product_create"),
    path("seller/products/<int:pk>/edit/", seller_views.product_edit, name="seller_product_edit"),
    path("seller/products/<int:pk>/submit/", seller_views.product_submit, name="seller_product_submit"),
    path("shop/", views.product_list, name="shop"),
    path("categories/", views.category_list, name="categories"),
    path("category/<slug:slug>/", views.category_detail, name="category_detail"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("stores/", views.store_list, name="stores"),
    path("store/<slug:slug>/", views.store_detail, name="store_detail"),
]
