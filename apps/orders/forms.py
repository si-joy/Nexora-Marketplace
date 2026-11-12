"""Checkout shipping/contact form. We never accept prices from the browser."""
import re
from django import forms


class CheckoutForm(forms.Form):
    contact_name = forms.CharField(max_length=120, min_length=2, label="Full name")
    phone = forms.CharField(max_length=24, label="Phone number")
    address_line = forms.CharField(
        max_length=255, min_length=10, label="Street address",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "House, road, neighborhood"}),
    )
    area = forms.CharField(max_length=100, label="City / district")
    postal_code = forms.CharField(max_length=16, required=False, label="Postal code (optional)")
    notes = forms.CharField(
        max_length=500, required=False, label="Delivery notes (optional)",
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    agree = forms.BooleanField(
        label="I understand this is a manual cash-on-delivery order request. No online payment is processed.",
    )

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not re.fullmatch(r"\+?[0-9][0-9\s-]{7,22}", phone):
            raise forms.ValidationError("Enter a valid phone number (8–24 characters).")
        return phone
