"""Sale pricing is real BDT price; crossed-out amount is for display only."""
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalog.forms import ProductForm
from apps.catalog.models import Brand, ProductVariantPrice
from apps.catalog.services.products import create_product, update_product
from apps.shopping.services import _price

from .test_real_catalog import approved_seller, category, cleaned, jpeg_photo


@pytest.mark.django_db
def test_seller_form_accepts_valid_regular_and_sale_price(category):
    form = ProductForm({
        "name": "Discounted Audio", "category": category.pk, "brand": "",
        "new_brand_name": "Acme Audio", "sku": "SALE-TEST-01",
        "price_bdt": "950.00", "sale_price_bdt": "650.00",
    })
    assert form.is_valid(), form.errors.as_json()
    assert form.cleaned_data["sale_price_bdt"] == Decimal("650.00")


@pytest.mark.django_db
def test_seller_form_rejects_equal_or_higher_sale_and_brand_conflicts(category):
    brand = Brand.objects.create(name="Existing Brand", slug="existing-brand")
    base = {
        "name": "Sale Test", "category": category.pk, "sku": "SALE-TEST-02",
        "price_bdt": "950.00",
    }
    for bad in ("950.00", "1050.00"):
        form = ProductForm({**base, "sale_price_bdt": bad})
        assert not form.is_valid()
        assert "sale_price_bdt" in form.errors
    form = ProductForm({**base, "brand": brand.pk, "new_brand_name": "Another Brand"})
    assert not form.is_valid()
    assert "new_brand_name" in form.errors


@pytest.mark.django_db
def test_create_sale_price_is_cart_price_and_original_is_crossed_out(
    client, approved_seller, category, settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path / "media"
    seller, _, _ = approved_seller
    # The card must actually render an uploaded image before checking its CSS.
    values = cleaned(category, jpeg_photo())
    values["new_brand_name"] = "Acme Beauty"
    values["price_bdt"] = Decimal("950.00")
    values["sale_price_bdt"] = Decimal("650.00")
    product = create_product(seller=seller, cleaned=values)
    variant = product.variants.first()
    price = ProductVariantPrice.objects.get(variant=variant)
    assert product.brand.name == "Acme Beauty"
    assert price.amount == Decimal("650.00")
    assert price.compare_at_amount == Decimal("950.00")
    assert product.bdt_price == Decimal("650.00")
    assert product.bdt_compare_at_price == Decimal("950.00")
    assert _price(variant.pk) == Decimal("650.00")
    product.status = product.Status.PUBLISHED
    product.save(update_fields=["status"])
    response = client.get(reverse("catalog:marketplace_detail", args=[product.slug]))
    assert response.status_code == 200
    html = response.content.decode()
    assert "৳650.00" in html
    assert "<del" in html
    assert "৳950.00" in html
    assert "Acme Beauty" in html
    # The same live listing must fill the entire card frame without letterboxing.
    listing_html = client.get(reverse("catalog:marketplace_list")).content.decode()
    assert product.name in listing_html
    assert 'aspect-[4/3] overflow-hidden' in listing_html
    assert 'src="' + product.primary_image.image.url + '"' in listing_html
    assert 'absolute inset-0 h-full w-full object-cover object-center' in listing_html



@pytest.mark.django_db
def test_edit_price_without_sale_clears_old_discount_and_preserves_brand(
    approved_seller, category
):
    seller, _, _ = approved_seller
    values = cleaned(category)
    values.update({
        "price_bdt": Decimal("1200.00"),
        "sale_price_bdt": Decimal("850.00"),
        "new_brand_name": "Reusable Brand",
    })
    product = create_product(seller=seller, cleaned=values)
    brand = product.brand
    values["price_bdt"] = Decimal("1100.00")
    values["sale_price_bdt"] = None
    values["new_brand_name"] = "reusable brand"
    update_product(seller=seller, product_id=product.pk, cleaned=values)
    product.refresh_from_db()
    assert product.brand_id == brand.pk
    assert Brand.objects.filter(name__iexact="reusable brand").count() == 1
    assert product.bdt_price == Decimal("1100.00")
    assert product.bdt_compare_at_price is None


@pytest.mark.django_db
def test_edit_form_prepopulates_sale_and_original(category, approved_seller):
    seller, _, _ = approved_seller
    values = cleaned(category)
    values["price_bdt"] = Decimal("950.00")
    values["sale_price_bdt"] = Decimal("650.00")
    product = create_product(seller=seller, cleaned=values)
    form = ProductForm(product=product)
    assert form.initial["price_bdt"] == Decimal("950.00")
    assert form.initial["sale_price_bdt"] == Decimal("650.00")


@pytest.mark.django_db
def test_seller_brand_editor_is_compact_and_toggles_on_validation_error(
    client, approved_seller, category
):
    seller, _, _ = approved_seller
    client.force_login(seller)
    page = client.get(reverse("catalog:seller_product_create"))
    assert page.status_code == 200
    html = page.content.decode()
    assert 'data-brand-editor' in html
    assert 'data-brand-mode-toggle' in html
    assert 'aria-expanded="false"' in html
    assert 'id="seller-new-brand" data-brand-new hidden' in html
    assert 'js/seller-brand.js' in html
    assert 'rounded-xl border border-dashed border-line bg-surface-soft p-3' not in html

    response = client.post(reverse("catalog:seller_product_create"), {
        "name": "Brand test", "category": category.pk,
        "new_brand_name": "New beauty", "price_bdt": "950.00",
        "sale_price_bdt": "950.00", "sku": "BRAND-VALIDATION-101",
    })
    assert response.status_code == 200
    assert 'aria-expanded="true"' in response.content.decode()
    assert 'id="seller-new-brand" data-brand-new hidden' not in response.content.decode()



@pytest.mark.django_db
def test_catalog_product_image_wrappers_use_full_cover(client, approved_seller, category):
    seller, _, _ = approved_seller
    values = cleaned(category)
    product = create_product(seller=seller, cleaned=values)
    product.status = product.Status.PUBLISHED
    product.save(update_fields=["status"])

    from django.template.loader import get_template
    from pathlib import Path

    snippets = {
        "catalog/public/product_tile.html": "absolute inset-0 h-full w-full object-cover object-center",
        "catalog/public/marketplace_detail.html": "absolute inset-0 h-full w-full object-cover object-center",
        "catalog/seller/product_form.html": "absolute inset-0 h-full w-full object-cover object-center",
        "components/cards/product_preview.html": "absolute inset-0 h-full w-full object-cover object-center",
        "pages/categories.html": "absolute inset-0 h-full w-full object-cover object-center",
        "pages/category_detail.html": "absolute inset-0 h-full w-full object-cover object-center",
        "pages/home.html": "absolute inset-0 h-full w-full object-cover object-center",
    }
    for template_name, snippet in snippets.items():
        source = Path(get_template(template_name).origin.name).read_text(encoding="utf-8")
        assert snippet in source, template_name

    page = client.get(reverse("catalog:marketplace_list"))
    assert page.status_code == 200
    assert 'object-cover object-center' in page.content.decode()
