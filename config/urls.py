from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("account/", include("apps.accounts.urls")),
    path("seller/", include("apps.vendors.urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.catalog.urls")),
    path("", include("apps.shopping.urls")),
    path("", include("apps.inventory.urls")),
    path("", include("apps.orders.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
