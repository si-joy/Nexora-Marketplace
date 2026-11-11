from django.urls import path

from . import views

app_name = "vendors"
urlpatterns = [
    path("apply/", views.apply, name="apply"),
    path("dashboard/", views.dashboard, name="dashboard"),
]
