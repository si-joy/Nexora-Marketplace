from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
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


@login_required
def dashboard(request):
    profile = SellerProfile.objects.filter(user=request.user).first()
    if profile is None:
        return redirect("vendors:apply")
    if profile.status != SellerProfile.Status.APPROVED:
        return render(request, "vendors/application_status.html", {"profile": profile})
    store = Store.objects.filter(seller=profile, status=Store.Status.ACTIVE).first()
    if store is None:
        return render(request, "vendors/application_status.html", {"profile": profile, "store_unavailable": True})
    return render(request, "vendors/dashboard.html", {
        "profile": profile, "store": store, "product_count": store.products.count(),
        "order_count": store.order_lines.count(),
        "pending_order_count": store.order_lines.filter(status="pending").count(),
    })
