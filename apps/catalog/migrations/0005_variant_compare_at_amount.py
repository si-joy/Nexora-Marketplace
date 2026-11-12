from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0004_product_content_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="productvariantprice",
            name="compare_at_amount",
            field=models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True),
        ),
        migrations.AddConstraint(
            model_name="productvariantprice",
            constraint=models.CheckConstraint(
                condition=Q(compare_at_amount__isnull=True) | Q(compare_at_amount__gt=F("amount")),
                name="cat_compare_higher",
            ),
        ),
    ]
