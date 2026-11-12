from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.views.decorators.cache import never_cache
from django.shortcuts import redirect, render

from .forms import SellerApplicationForm
from .models import SellerProfile, Store
from .services import submit_application


@login_required
def apply(request):
    profile = SellerProfile.objects.filter(user=request.user).first()
    if profile and profile.status != SellerProfile.Status.REJECTED:
        return redirect("vendors:dashboard")

    form = SellerApplicationForm(request.POST or None, initial={
        "business_name": profile.business_name if profile else "",
        "contact_phone": profile.contact_phone if profile else "",
        "description": profile.description if profile else "",
    })
    if request.method == "POST" and form.is_valid():
        try:
            submit_application(user=request.user, **form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Your seller application was submitted for review.")
            return redirect("vendors:dashboard")
    return render(request, "vendors/apply.html", {"form": form, "is_reapplication": bool(profile)})


SELLER_TABS = frozenset({"overview", "products", "stock", "orders"})


@login_required
@never_cache
def dashboard(request):
    """Seller workspace with independently rendered, account-scoped panels.

    Normal navigation delivers a complete page. The enhancement sends the
    X-Seller-Panel header and receives only the selected right-hand panel.
    """
    profile = SellerProfile.objects.filter(user=request.user).first()
    if profile is None:
        return redirect("vendors:apply")
    if profile.status != SellerProfile.Status.APPROVED:
        return render(request, "vendors/application_status.html", {"profile": profile})
    store = Store.objects.filter(seller=profile, status=Store.Status.ACTIVE).first()
    if store is None:
        return render(
            request, "vendors/application_status.html",
            {"profile": profile, "store_unavailable": True},
        )

    tab = request.GET.get("tab", "overview")
    if tab not in SELLER_TABS:
        tab = "overview"

    context = {"profile": profile, "store": store, "active_tab": tab}
    if tab == "overview":
        context.update({
            "product_count": store.products.count(),
            "order_count": store.order_lines.count(),
            "pending_order_count": store.order_lines.filter(status="pending").count(),
        })
    elif tab == "products":
        from apps.catalog.models import Product

        products = (
            Product.objects.filter(store=store)
            .select_related("category")
            .prefetch_related("images", "variants__prices__currency")
            .order_by("-updated_at", "-pk")
        )
        context["page"] = Paginator(products, 20).get_page(request.GET.get("page"))
    elif tab == "stock":
        from apps.catalog.models import ProductVariant
        from apps.inventory.models import Stock

        variants = (
            ProductVariant.objects.filter(product__store=store)
            .select_related("product")
            .order_by("product__name", "sku", "pk")
        )
        page = Paginator(variants, 30).get_page(request.GET.get("page"))
        stocks = {
            item.variant_id: item
            for item in Stock.objects.filter(
                variant_id__in=[variant.pk for variant in page.object_list]
            )
        }
        context["page"] = page
        context["rows"] = [
            {
                "variant": variant,
                "quantity": stocks[variant.pk].quantity if variant.pk in stocks else 0,
                "reserved": stocks[variant.pk].reserved_quantity if variant.pk in stocks else 0,
                "available": stocks[variant.pk].available if variant.pk in stocks else 0,
            }
            for variant in page.object_list
        ]
    elif tab == "orders":
        from apps.orders.models import OrderItem

        orders = (
            OrderItem.objects.filter(store=store)
            .select_related("order", "variant")
            .order_by("-order__created_at", "-pk")
        )
        context["page"] = Paginator(orders, 30).get_page(request.GET.get("page"))

    if request.headers.get("X-Seller-Panel") == "1":
        return render(request, f"vendors/panels/{tab}.html", context)
    return render(request, "vendors/dashboard.html", context)
