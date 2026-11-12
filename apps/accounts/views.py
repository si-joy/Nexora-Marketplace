from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import CustomerRegistrationForm


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = CustomerRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome to Nexora! Your account is ready.")
        return redirect("accounts:dashboard")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def dashboard(request):
    from apps.vendors.models import SellerProfile

    seller_profile = SellerProfile.objects.filter(user=request.user).first()
    from apps.orders.models import Order
    order_count = Order.objects.filter(buyer=request.user).count()
    return render(request, "accounts/dashboard.html", {
        "seller_profile": seller_profile, "order_count": order_count,
    })
