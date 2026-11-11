"""Idempotent local initial categories; never creates fake seller products."""
from django.core.management.base import BaseCommand
from apps.catalog.models import Category, Currency

CATEGORIES = (
    ("Electronics", "electronics", None),
    ("Audio", "audio", "electronics"),
    ("Wearables", "wearables", "electronics"),
    ("Computing", "computing", "electronics"),
    ("Gaming", "gaming", "electronics"),
    ("Photography", "photography", "electronics"),
    ("Lifestyle", "lifestyle", None),
)


class Command(BaseCommand):
    help = "Create base catalog categories and BDT currency (safe to run repeatedly)."

    def handle(self, *args, **options):
        Currency.objects.get_or_create(
            code="BDT", defaults={"name": "Bangladeshi Taka", "symbol": "৳", "decimal_places": 2}
        )
        parents = {}
        for name, slug, parent_slug in CATEGORIES:
            category, _ = Category.objects.get_or_create(
                slug=slug, defaults={"name": name, "parent": parents.get(parent_slug)}
            )
            parents[slug] = category
        self.stdout.write(self.style.SUCCESS("Catalog categories ready."))
