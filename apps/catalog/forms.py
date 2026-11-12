"""Seller input validation: catalog metadata, default SKU, BDT pricing and up to five gallery photos."""
from decimal import Decimal
from pathlib import Path

from django import forms
from PIL import Image, UnidentifiedImageError

from .models import Brand, Category, Product, ProductVariant


class ProductForm(forms.Form):
    name = forms.CharField(max_length=200, strip=True)
    category = forms.ModelChoiceField(queryset=Category.objects.none())
    brand = forms.ModelChoiceField(queryset=Brand.objects.none(), required=False)
    short_description = forms.CharField(max_length=240, required=False, widget=forms.Textarea(attrs={"rows": 2}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 6}))
    sku = forms.CharField(max_length=80)
    price_bdt = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
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
        self.fields["category"].queryset = Category.objects.filter(is_active=True).order_by("name")
        self.fields["brand"].queryset = Brand.objects.filter(is_active=True).order_by("name")
        if product is not None and not self.is_bound:
            variant = product.variants.first()
            self.initial = {
                "name": product.name,
                "category": product.category_id,
                "brand": product.brand_id,
                "short_description": product.short_description,
                "description": product.description,
                "sku": variant.sku if variant else "",
                "price_bdt": product.bdt_price,
            }

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
        images = []
        for name in ("image", "image_1", "image_2", "image_3", "image_4", "image_5"):
            uploaded = cleaned.get(name)
            if uploaded:
                cleaned[name] = self._clean_uploaded_image(uploaded)
                images.append(cleaned[name])
        existing_count = self.product.images.count() if self.product is not None else 0
        if existing_count + len(images) > 5:
            raise forms.ValidationError("A product can have at most 5 gallery images.")
        cleaned["images"] = images
        return cleaned
