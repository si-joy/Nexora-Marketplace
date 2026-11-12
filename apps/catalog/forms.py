"""Seller input validation: catalog metadata, default SKU, BDT pricing and up to five gallery photos."""
from decimal import Decimal
from pathlib import Path

from django import forms
from PIL import Image, UnidentifiedImageError

from .models import Brand, Category, Product, ProductVariant


class ProductForm(forms.Form):
    name = forms.CharField(max_length=200, strip=True)
    category = forms.ModelChoiceField(queryset=Category.objects.none())
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.none(), required=False,
        label="Existing brand",
        help_text="",
    )
    new_brand_name = forms.CharField(
        max_length=120, required=False, label="Create a new brand",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Acme Beauty"}),
        help_text="Can't find your brand? Type its name here; you can leave Existing brand blank.",
    )
    short_description = forms.CharField(max_length=240, required=False, widget=forms.Textarea(attrs={"rows": 2}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 6}))
    highlights = forms.CharField(
        required=False, max_length=1400, label="Key highlights (one per line)",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Wireless Bluetooth\n40-hour battery\nFast charging"}),
        help_text="Up to 6 short highlights, each on a separate line.",
    )
    specifications_text = forms.CharField(
        required=False, max_length=2400, label="Specifications (one key: value per line)",
        widget=forms.Textarea(attrs={"rows": 5, "placeholder": "Connectivity: Bluetooth\nBattery: 40 hours\nWarranty: 1 year"}),
        help_text="Up to 12 specifications, formatted as Name: Value.",
    )
    sku = forms.CharField(max_length=80)
    price_bdt = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01"),
        label="Regular price (BDT)",
        help_text="Original price before any discount. Required.",
    )
    sale_price_bdt = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01"),
        required=False, label="Sale price (BDT) — optional",
        help_text="Must be lower than the regular price. Leave empty for no discount.",
    )
    initial_stock = forms.IntegerField(required=False, min_value=0, max_value=100_000, label="Initial stock", help_text="New products only. Leave blank for zero; edit stock separately after saving.")
    # Backward compatibility for existing single-image form submissions. Not shown in the V8 UI.
    image = forms.ImageField(required=False)
    image_1 = forms.ImageField(required=False, help_text="Main image · JPEG, PNG or WEBP · up to 5 MB.")
    image_2 = forms.ImageField(required=False)
    image_3 = forms.ImageField(required=False)
    image_4 = forms.ImageField(required=False)
    image_5 = forms.ImageField(required=False)

    def __init__(self, *args, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product
        input_class = "mt-2 block w-full rounded-xl border border-line bg-surface-soft px-4 py-3 text-sm text-foreground outline-none focus:border-primary"
        for name, field in self.fields.items():
            field.widget.attrs["class"] = input_class
            if name.startswith("image_"):
                field.widget.attrs["accept"] = ".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                field.widget.attrs["class"] = "absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0"
                field.widget.attrs["aria-label"] = f"Choose or replace gallery image {name.split('_')[-1]}"
        self.fields["category"].queryset = Category.objects.filter(is_active=True).order_by("name")
        self.fields["brand"].queryset = Brand.objects.filter(is_active=True).order_by("name")
        if product is not None and not self.is_bound:
            variant = product.variants.first()
            self.initial = {
                "name": product.name,
                "category": product.category_id,
                "brand": product.brand_id,
                "new_brand_name": "",
                "short_description": product.short_description,
                "description": product.description,
                "highlights": product.highlights,
                "specifications_text": "\n".join(f"{key}: {value}" for key, value in (product.specifications or {}).items()),
                "sku": variant.sku if variant else "",
                "price_bdt": product.bdt_compare_at_price or product.bdt_price,
                "sale_price_bdt": product.bdt_price if product.bdt_compare_at_price else None,
            }

    def clean_highlights(self):
        raw = self.cleaned_data.get("highlights", "")
        lines = [line.strip().lstrip("•- ").strip() for line in raw.splitlines() if line.strip()]
        if len(lines) > 6 or any(len(line) > 180 for line in lines):
            raise forms.ValidationError("Enter at most 6 highlights, each up to 180 characters.")
        return "\n".join(lines)

    def clean_specifications_text(self):
        raw = self.cleaned_data.get("specifications_text", "")
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if len(lines) > 12:
            raise forms.ValidationError("Enter no more than 12 specifications.")
        specs = {}
        for line in lines:
            key, sep, value = line.partition(":")
            key, value = key.strip(), value.strip()
            if not sep or not key or not value or len(key) > 60 or len(value) > 180:
                raise forms.ValidationError("Each specification must be Name: Value (name ≤60, value ≤180 characters).")
            if key.casefold() in (k.casefold() for k in specs):
                raise forms.ValidationError("Specification names must be unique.")
            specs[key] = value
        return specs

    def clean_sku(self):
        sku = self.cleaned_data["sku"].strip().upper()
        variants = ProductVariant.objects.filter(sku__iexact=sku)
        if self.product is not None:
            variants = variants.exclude(product=self.product)
        if variants.exists():
            raise forms.ValidationError("This SKU is already used by another product.")
        return sku

    def _clean_uploaded_image(self, uploaded):
        if not uploaded:
            return uploaded
        if uploaded.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Image size must not exceed 5 MB.")
        try:
            uploaded.seek(0)
            with Image.open(uploaded) as photo:
                image_format = photo.format
                if photo.width * photo.height > 36_000_000:
                    raise forms.ValidationError("Image dimensions are too large.")
                photo.verify()
            uploaded.seek(0)
        except (UnidentifiedImageError, OSError, ValueError):
            raise forms.ValidationError("Upload a valid JPEG, PNG or WEBP image.") from None
        if image_format not in {"JPEG", "PNG", "WEBP"}:
            raise forms.ValidationError("Only JPEG, PNG and WEBP images are accepted.")
        extension = Path(uploaded.name).suffix.lower()
        formats = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}
        if formats.get(extension) != image_format:
            raise forms.ValidationError("File extension must match the uploaded image format.")
        return uploaded

    def clean(self):
        cleaned = super().clean()
        brand = cleaned.get("brand")
        new_name = (cleaned.get("new_brand_name") or "").strip()
        if brand and new_name:
            self.add_error("new_brand_name", "Select an existing brand OR type a new name, not both.")
        if new_name and not any(character.isalnum() for character in new_name):
            self.add_error("new_brand_name", "Enter a recognizable brand name.")

        regular = cleaned.get("price_bdt")
        sale = cleaned.get("sale_price_bdt")
        if regular is not None and sale is not None and sale >= regular:
            self.add_error("sale_price_bdt", "Sale price must be lower than the regular price.")
        images = []
        image_slots = {}

        # Slot indexes are stable between create and edit. A file selected for
        # an existing slot replaces that photo; empty slots add a new photo.
        for index in range(5):
            name = f"image_{index + 1}"
            uploaded = cleaned.get(name)
            if uploaded:
                cleaned[name] = self._clean_uploaded_image(uploaded)
                image_slots[index] = cleaned[name]
                images.append(cleaned[name])

        legacy = cleaned.get("image")
        if legacy:
            cleaned["image"] = self._clean_uploaded_image(legacy)
            images.append(cleaned["image"])

        existing_slots = (
            set(self.product.images.values_list("sort_order", flat=True))
            if self.product is not None else set()
        )
        new_count = sum(1 for position in image_slots if position not in existing_slots)
        if legacy:
            new_count += 1
        if len(existing_slots) + new_count > 5:
            raise forms.ValidationError(
                "The gallery has five slots. Replace an existing image instead of adding a sixth."
            )

        # Preserve old callers that inspect the images list, while the upload
        # service uses image_slots to distinguish replacements from additions.
        cleaned["images"] = images
        cleaned["image_slots"] = image_slots
        return cleaned
