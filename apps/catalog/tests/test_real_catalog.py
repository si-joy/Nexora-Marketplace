"""Behavioral coverage for the real catalog; demo shop tests remain unchanged."""
from io import BytesIO
from decimal import Decimal

import pytest
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.catalog.models import Category, Product, ProductVariantPrice
from apps.catalog.services import approve_product, create_product, submit_product, update_product
from apps.vendors.models import Store
from apps.vendors.services import review_application, submit_application

User = get_user_model()


def jpeg_photo():
    bio = BytesIO()
    Image.new("RGB", (32, 32), "blue").save(bio, format="JPEG")
    return SimpleUploadedFile("product.jpg", bio.getvalue(), content_type="image/jpeg")


@pytest.fixture
def approved_seller(db):
    user = User.objects.create_user(email="seller-v6@example.com", password="ComplexPass456!")
    admin = User.objects.create_superuser(email="admin-v6@example.com", password="ComplexPass456!")
    profile = submit_application(user=user, business_name="Real Shop", contact_phone="0123456789")
    review_application(profile_id=profile.pk, reviewer=admin, decision="approve")
    return user, admin, Store.objects.get(seller=profile)


@pytest.fixture
def category(db):
    return Category.objects.create(name="Audio", slug="audio", is_active=True)


def cleaned(category, image=None):
    return {"name": "Real Headphones", "category": category, "brand": None,
            "short_description": "Wireless audio", "description": "Studio-quality sound.",
            "sku": "REAL-HP-0001", "price_bdt": Decimal("2499.00"), "image": image}


@pytest.mark.django_db
def test_seller_create_submit_approve_and_public_visibility(client, approved_seller, category, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    seller, reviewer, store = approved_seller
    client.force_login(seller)
    response = client.post(reverse("catalog:seller_product_create"), {**cleaned(category, jpeg_photo()), "category": category.pk, "brand": ""})
    assert response.status_code == 302
    product = Product.objects.get(store=store)
    assert product.status == Product.Status.DRAFT
    assert ProductVariantPrice.objects.get(variant__product=product).amount == Decimal("2499.00")
    assert client.get(reverse("catalog:marketplace_detail", args=[product.slug])).status_code == 404
    response = client.post(reverse("catalog:seller_product_submit", args=[product.pk]))
    assert response.status_code == 302
    product.refresh_from_db()
    assert product.status == Product.Status.PENDING
    assert client.get(reverse("catalog:marketplace_detail", args=[product.slug])).status_code == 404
    with pytest.raises(PermissionDenied):
        approve_product(reviewer=seller, product_id=product.pk)
    approve_product(reviewer=reviewer, product_id=product.pk)
    assert client.get(reverse("catalog:marketplace_detail", args=[product.slug])).status_code == 200
    assert b"Real Headphones" in client.get(reverse("catalog:marketplace_list")).content


@pytest.mark.django_db
def test_editing_published_product_resets_approval(approved_seller, category, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    seller, reviewer, store = approved_seller
    product = create_product(seller=seller, cleaned=cleaned(category, jpeg_photo()))
    submit_product(seller=seller, product_id=product.pk)
    approve_product(reviewer=reviewer, product_id=product.pk)
    new_data = cleaned(category)
    new_data["name"] = "Renamed Headphones"
    update_product(seller=seller, product_id=product.pk, cleaned=new_data)
    product.refresh_from_db()
    assert product.status == Product.Status.DRAFT
    assert product.published_at is None
    assert not Product.objects.filter(status=Product.Status.PUBLISHED, store=store).exists()


@pytest.mark.django_db
def test_seller_without_approval_cannot_create_product(category):
    customer = User.objects.create_user(email="customer-v6@example.com", password="ComplexPass456!")
    with pytest.raises(PermissionDenied):
        create_product(seller=customer, cleaned=cleaned(category))


@pytest.mark.django_db
def test_cannot_submit_without_image(approved_seller, category):
    seller, _, _ = approved_seller
    product = create_product(seller=seller, cleaned=cleaned(category))
    with pytest.raises(ValidationError):
        submit_product(seller=seller, product_id=product.pk)


@pytest.mark.django_db
def test_cross_seller_edit_is_blocked(client, approved_seller, category):
    seller, _, _ = approved_seller
    product = create_product(seller=seller, cleaned=cleaned(category))
    stranger = User.objects.create_user(email="stranger-v6@example.com", password="ComplexPass456!")
    client.force_login(stranger)
    assert client.get(reverse("catalog:seller_product_edit", args=[product.pk])).status_code == 403
    assert client.post(reverse("catalog:seller_product_submit", args=[product.pk])).status_code == 403


@pytest.mark.django_db
def test_unapproved_product_never_public(approved_seller, category, client):
    seller, _, _ = approved_seller
    product = create_product(seller=seller, cleaned=cleaned(category))
    assert client.get(reverse("catalog:marketplace_list")).status_code == 200
    assert b"Real Headphones" not in client.get(reverse("catalog:marketplace_list")).content
    assert client.get(reverse("catalog:marketplace_detail", args=[product.slug])).status_code == 404



@pytest.mark.django_db
def test_gallery_list_uploads_keep_original_order(approved_seller, category, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    seller, _, _ = approved_seller
    values = cleaned(category)
    values["images"] = [jpeg_photo(), jpeg_photo()]
    product = create_product(seller=seller, cleaned=values)
    photos = list(product.images.order_by("sort_order", "id"))
    assert len(photos) == 2
    assert [photo.sort_order for photo in photos] == [0, 1]
    assert all(photo.image.name for photo in photos)


@pytest.mark.django_db
def test_legacy_image_field_is_accepted_by_product_form(category):
    from apps.catalog.forms import ProductForm

    data = cleaned(category)
    uploaded = data.pop("image")
    assert uploaded is None
    form = ProductForm(
        data={**data, "category": category.pk, "brand": ""},
        files={"image": jpeg_photo()},
    )
    assert form.is_valid(), form.errors.as_json()
    assert len(form.cleaned_data["images"]) == 1

@pytest.mark.django_db
def test_marketplace_tile_shows_cart_icon_for_stocked_product(client, approved_seller, category):
    from apps.inventory.models import Stock

    seller, _, _ = approved_seller
    product = create_product(seller=seller, cleaned=cleaned(category))
    product.status = Product.Status.PUBLISHED
    product.save(update_fields=["status"])
    variant = product.variants.get(is_default=True)
    Stock.objects.create(variant=variant, quantity=4)
    response = client.get(reverse("catalog:marketplace_list"))
    assert response.status_code == 200
    html = response.content.decode()
    assert 'data-add-real-bag' in html
    assert f'data-variant-id="{variant.pk}"' in html
    assert "Buy now" in html
    assert "Checkout coming soon" in html


@pytest.mark.django_db
def test_marketplace_tile_disables_cart_when_out_of_stock(client, approved_seller, category):
    seller, _, _ = approved_seller
    product = create_product(seller=seller, cleaned=cleaned(category))
    product.status = Product.Status.PUBLISHED
    product.save(update_fields=["status"])
    response = client.get(reverse("catalog:marketplace_list"))
    assert response.status_code == 200
    html = response.content.decode()
    assert "Currently unavailable" in html
    assert 'data-add-real-bag' not in html


def test_demo_product_card_retains_browser_cart_action(client):
    response = client.get(reverse("core:home"))
    assert response.status_code == 200
    assert b"Buy now" in response.content
    assert b"data-add-bag" in response.content
    assert b"Checkout coming soon" in response.content


@pytest.mark.django_db
def test_seller_uploads_render_on_refined_real_detail(client, approved_seller, category, settings, tmp_path):
    from apps.inventory.models import Stock

    settings.MEDIA_ROOT = tmp_path / "media"
    seller, reviewer, _ = approved_seller
    fields = cleaned(category, jpeg_photo())
    fields["highlights"] = "Bluetooth audio\n40-hour playback"
    fields["specifications_text"] = {
        "Connectivity": "Bluetooth",
        "Battery": "40 hours",
    }
    product = create_product(seller=seller, cleaned=fields)
    variant = product.variants.get(is_default=True)
    Stock.objects.create(variant=variant, quantity=8)
    submit_product(seller=seller, product_id=product.pk)
    approve_product(reviewer=reviewer, product_id=product.pk)
    response = client.get(reverse("catalog:marketplace_detail", args=[product.slug]))
    assert response.status_code == 200
    html = response.content.decode()
    assert "Bluetooth audio" in html
    assert "40-hour playback" in html
    assert "Connectivity" in html and "Bluetooth" in html
    assert 'data-gallery-main-image' in html
    assert 'data-add-real-bag' in html
    assert 'data-real-qty' in html
    assert 'data-marketplace-favorite' in html
    assert "Details & specifications" in html
    assert response.context["specifications"] == [
        ("Connectivity", "Bluetooth"), ("Battery", "40 hours"),
    ]


@pytest.mark.django_db
def test_seller_form_parses_and_validates_highlights_and_specs(category):
    from apps.catalog.forms import ProductForm

    payload = {
        "name": "Seller Editable Item", "category": category.pk, "brand": "",
        "sku": "FORM-SPEC-001", "price_bdt": "350.00",
        "highlights": "Fast charging\nWater resistant",
        "specifications_text": "Color: Black\nBattery: 30 hours",
    }
    form = ProductForm(data=payload)
    assert form.is_valid(), form.errors.as_json()
    assert form.cleaned_data["highlights"].splitlines() == [
        "Fast charging", "Water resistant"
    ]
    assert form.cleaned_data["specifications_text"] == {
        "Color": "Black", "Battery": "30 hours"
    }
    form = ProductForm(data={**payload, "specifications_text": "Bad specification"})
    assert not form.is_valid()
    assert "specifications_text" in form.errors


@pytest.mark.django_db
def test_seller_gallery_edit_has_five_inline_slots_and_saved_previews(
    client, approved_seller, category, settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path / "media"
    seller, _, _ = approved_seller
    values = cleaned(category)
    values["images"] = [jpeg_photo(), jpeg_photo()]
    product = create_product(seller=seller, cleaned=values)
    client.force_login(seller)

    response = client.get(reverse("catalog:seller_product_edit", args=[product.pk]))
    assert response.status_code == 200
    html = response.content.decode()
    assert html.count('data-gallery-upload-slot') == 5
    assert html.count('data-gallery-upload-preview') == 5
    assert html.count('data-gallery-upload-placeholder') == 5
    assert 'js/seller-gallery.js' in html
    assert product.images.first().image.url in html
    assert 'Saved · tap to replace' in html
    assert 'Tap to upload' in html


@pytest.mark.django_db
def test_seller_can_replace_one_slot_in_full_five_photo_gallery(
    approved_seller, category, settings, tmp_path
):
    from apps.catalog.forms import ProductForm

    settings.MEDIA_ROOT = tmp_path / "media"
    seller, _, _ = approved_seller
    values = cleaned(category)
    values["images"] = [jpeg_photo() for _ in range(5)]
    product = create_product(seller=seller, cleaned=values)

    original = {
        picture.sort_order: picture.image.name
        for picture in product.images.all()
    }
    form = ProductForm(
        data={
            "name": product.name, "category": category.pk, "brand": "",
            "sku": "REAL-HP-0001", "price_bdt": "2499.00",
        },
        files={"image_3": jpeg_photo()},
        product=product,
    )
    assert form.is_valid(), form.errors.as_json()
    update_product(seller=seller, product_id=product.pk, cleaned=form.cleaned_data)

    updated = {
        picture.sort_order: picture.image.name
        for picture in product.images.all()
    }
    assert sorted(updated) == [0, 1, 2, 3, 4]
    assert updated[2] != original[2]
    assert all(updated[index] == original[index] for index in (0, 1, 3, 4))


@pytest.mark.django_db
def test_upload_slots_create_real_gallery_with_correct_sequence(
    client, approved_seller, category, settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path / "media"
    seller, _, _ = approved_seller
    client.force_login(seller)
    response = client.post(reverse("catalog:seller_product_create"), {
        "name": "Gallery Upload Test",
        "category": str(category.pk),
        "brand": "",
        "sku": "GALLERY-EDIT-002",
        "price_bdt": "550.00",
        "image_1": jpeg_photo(),
        "image_2": jpeg_photo(),
        "image_5": jpeg_photo(),
    })
    assert response.status_code == 302
    product = Product.objects.get(name="Gallery Upload Test")
    assert list(product.images.values_list("sort_order", flat=True)) == [0, 1, 4]
    edit_html = client.get(
        reverse("catalog:seller_product_edit", args=[product.pk])
    ).content.decode()
    assert edit_html.count("Saved · tap to replace") == 3
    assert edit_html.count("Tap to upload") == 2
