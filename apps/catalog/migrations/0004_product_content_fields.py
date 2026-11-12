from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0003_sync_implicit_primary_key_state"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="highlights",
            field=models.TextField(blank=True, help_text="Seller-defined product highlights, one per line."),
        ),
        migrations.AddField(
            model_name="product",
            name="specifications",
            field=models.JSONField(blank=True, default=dict, help_text="Seller-defined technical specifications."),
        ),
    ]
