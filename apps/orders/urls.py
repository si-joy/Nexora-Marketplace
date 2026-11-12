from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.customer_orders, name="customer_orders"),
    path("orders/<int:order_id>/", views.customer_order_detail, name="customer_order_detail"),
    path("orders/lines/<int:line_id>/cancel/", views.customer_cancel_line, name="customer_cancel_line"),
    path("seller/orders/", views.seller_orders, name="seller_orders"),
    path("seller/orders/lines/<int:line_id>/update/", views.seller_update_line, name="seller_update_line"),
]
