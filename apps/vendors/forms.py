from django import forms

from apps.accounts.forms import apply_field_styles


class SellerApplicationForm(forms.Form):
    business_name = forms.CharField(max_length=120, label="Business or store name")
    contact_phone = forms.CharField(max_length=30, label="Business contact number")
    description = forms.CharField(
        max_length=1000, label="Tell us about your store",
        required=False, widget=forms.Textarea(attrs={"rows": 4})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_field_styles(self)

    def clean_business_name(self):
        value = " ".join(self.cleaned_data["business_name"].split())
        if len(value) < 3:
            raise forms.ValidationError("Please enter a business name of at least 3 characters.")
        return value
