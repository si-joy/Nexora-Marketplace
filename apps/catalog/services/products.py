"""All catalog writes pass through these transaction-protected services."""
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.vendors.models import SellerProfile, Store
from apps.catalog.models import Currency, Product, ProductImage, ProductVariant, ProductVariantPrice


def get_seller_store(user):
    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied("Sign in as an approved seller.")
    return Store.objects.filter(
        seller__user=user,
        seller__status=SellerProfile.Status.APPROVED,
        status=Store.Status.ACTIVE,
    ).first()


def require_seller_store(user):
    store = get_seller_store(user)
    if not store:
        raise PermissionDenied("An active, approved seller store is required.")
    return store


def _bdt():
    currency, _ = Currency.objects.get_or_create(
        code="BDT", defaults={"name": "Bangladeshi Taka", "symbol": "৳", "decimal_places": 2}
    )
    if not currency.is_active:
        raise ValidationError("BDT pricing is currently unavailable.")
    return currency


def _save_product_images(product, cleaned):
    """Save one photo per slot (0..4), replacing photos in occupied slots.

    Older API/service callers may still pass a legacy image or images list.
    Unselected slots and their existing images are never altered.
    """
    existing = {
        image.sort_order: image
        for image in ProductImage.objects.filter(product=product).order_by("sort_order", "id")
    }
    slots = dict(cleaned.get("image_slots") or {})
    if "image_slots" not in cleaned:
        uploads = list(cleaned.get("images") or [])
        if not uploads and cleaned.get("image"):
            uploads = [cleaned["image"]]
    else:
        uploads = [cleaned["image"]] if cleaned.get("image") else []

    for uploaded in uploads:
        vacant = next((i for i in range(5) if i not in existing and i not in slots), None)
        if vacant is None:
            raise ValidationError("A product can have no more than five gallery images.")
        slots[vacant] = uploaded

    if any(type(index) is not int or index not in range(5) for index in slots):
        raise ValidationError("Invalid gallery image slot.")
    if len(existing) + sum(1 for index in slots if index not in existing) > 5:
        raise ValidationError("A product can have no more than five gallery images.")

    for index, uploaded in sorted(slots.items()):
        if index in existing:
            photo = existing[index]
            photo.image = uploaded
            photo.alt_text = product.name
            photo.save(update_fields=["image", "alt_text"])
        else:
            ProductImage.objects.create(
                product=product, image=uploaded,
                alt_text=product.name, sort_order=index,
            )


@transaction.atomic
def create_product(*, seller, cleaned):
    store = require_seller_store(seller)
    product = Product.objects.create(
        store=store,
        name=cleaned["name"],
        slug=f"{slugify(cleaned['name'])[:195] or 'product'}-{uuid4().hex[:12]}",
        category=cleaned["category"],
        brand=cleaned.get("brand"),
        short_description=cleaned.get("short_description", ""),
        description=cleaned.get("description", ""),
        highlights=cleaned.get("highlights", ""),
        specifications=cleaned.get("specifications_text", {}),
    )
    variant = ProductVariant.objects.create(product=product, sku=cleaned["sku"].strip().upper(), is_default=True)
    ProductVariantPrice.objects.create(variant=variant, currency=_bdt(), amount=cleaned["price_bdt"])
    _save_product_images(product, cleaned)
    initial_stock = cleaned.get("initial_stock")
    if initial_stock is not None:
        if type(initial_stock) is not int or initial_stock < 0 or initial_stock > 100_000:
            raise ValidationError("Initial stock must be a whole number between 0 and 100,000.")
        if initial_stock:
            from apps.inventory.services import adjust_stock
            adjust_stock(seller=seller, variant_id=variant.pk, delta=initial_stock, note="Initial stock on product creation")
    return product


@transaction.atomic
def update_product(*, seller, product_id, cleaned):
    store = require_seller_store(seller)
    product = Product.objects.select_for_update().get(pk=product_id, store=store)
    if product.status == Product.Status.ARCHIVED:
        raise ValidationError("Archived products cannot be edited.")
    product.name = cleaned["name"]
    product.category = cleaned["category"]
    product.brand = cleaned.get("brand")
    product.short_description = cleaned.get("short_description", "")
    product.description = cleaned.get("description", "")
    product.highlights = cleaned.get("highlights", "")
    product.specifications = cleaned.get("specifications_text", {})
    product.status = Product.Status.DRAFT  # Edits to published items require re-approval.
    product.reviewed_by = None
    product.moderation_note = ""
    product.published_at = None
    product.save(update_fields=[
        "name", "category", "brand", "short_description", "description", "highlights", "specifications", "status",
        "reviewed_by", "moderation_note", "published_at", "updated_at",
    ])
    variant = ProductVariant.objects.select_for_update().get(product=product, is_default=True)
    variant.sku = cleaned["sku"].strip().upper()
    variant.save(update_fields=["sku"])
    ProductVariantPrice.objects.update_or_create(
        variant=variant, currency=_bdt(), defaults={"amount": cleaned["price_bdt"]}
    )
    _save_product_images(product, cleaned)
    return product


@transaction.atomic
def submit_product(*, seller, product_id):
    store = require_seller_store(seller)
    product = Product.objects.select_for_update().get(pk=product_id, store=store)
    if product.status not in {Product.Status.DRAFT, Product.Status.REJECTED}:
        raise ValidationError("Only draft or rejected products can be submitted.")
    if not product.category.is_active or not product.images.exists():
        raise ValidationError("Select an active category and upload at least one product image before submitting.")
    if not ProductVariantPrice.objects.filter(variant__product=product, variant__is_active=True, currency_id="BDT").exists():
        raise ValidationError("A valid BDT price is required.")
    product.status = Product.Status.PENDING
    product.moderation_note = ""
    product.save(update_fields=["status", "moderation_note", "updated_at"])
    return product


@transaction.atomic
def approve_product(*, reviewer, product_id, approve=True):
    if not reviewer.is_authenticated or not reviewer.is_staff or not reviewer.has_perm("catalog.change_product"):
        raise PermissionDenied("Only authorized staff may review products.")
    product = Product.objects.select_for_update().select_related("store", "store__seller").get(pk=product_id)
    if product.status != Product.Status.PENDING:
        raise ValidationError("Only pending products may be reviewed.")
    if product.store.status != Store.Status.ACTIVE or product.store.seller.status != SellerProfile.Status.APPROVED:
        raise ValidationError("Seller store is not approved and active.")
    if not product.category.is_active or not product.images.exists():
        raise ValidationError("Product requires an active category and at least one image.")
    product.status = Product.Status.PUBLISHED if approve else Product.Status.REJECTED
    product.reviewed_by = reviewer
    product.published_at = timezone.now() if approve else None
    product.save(update_fields=["status", "reviewed_by", "published_at", "updated_at"])
    return product
