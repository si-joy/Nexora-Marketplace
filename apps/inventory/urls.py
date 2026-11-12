from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("seller/inventory/", views.inventory_list, name="list"),
    path("seller/inventory/<int:variant_id>/", views.inventory_adjust, name="adjust"),
]
