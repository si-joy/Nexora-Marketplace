from django import forms


class StockAdjustmentForm(forms.Form):
    delta = forms.IntegerField(
        min_value=-100_000,
        max_value=100_000,
        label="Change stock by",
        help_text="Enter +10 to add 10 units or -3 to reduce by 3.",
        widget=forms.NumberInput(attrs={"placeholder": "e.g. +10 or -3", "step": "1"}),
    )
    note = forms.CharField(
        required=False,
        max_length=240,
        label="Reason (optional)",
        widget=forms.TextInput(attrs={"placeholder": "Received shipment / damaged stock"}),
    )

    def clean_delta(self):
        value = self.cleaned_data["delta"]
        if value == 0:
            raise forms.ValidationError("Adjustment cannot be zero.")
        return value
