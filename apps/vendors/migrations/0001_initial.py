from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SellerProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("business_name", models.CharField(max_length=120)),
                ("contact_phone", models.CharField(max_length=30)),
                ("description", models.TextField(blank=True, max_length=1000)),
                ("status", models.CharField(choices=[("pending", "Pending review"), ("under_review", "Under review"), ("approved", "Approved"), ("rejected", "Rejected"), ("suspended", "Suspended")], default="pending", max_length=12)),
                ("submitted_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_note", models.TextField(blank=True)),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="seller_reviews", to=settings.AUTH_USER_MODEL)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="seller_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-submitted_at",)},
        ),
        migrations.CreateModel(
            name="Store",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(max_length=160, unique=True)),
                ("description", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("suspended", "Suspended")], default="draft", max_length=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("seller", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="store", to="vendors.sellerprofile")),
            ],
        ),
        migrations.AddIndex(
            model_name="sellerprofile",
            index=models.Index(fields=["status", "submitted_at"], name="vendors_sel_status_97b0bf_idx"),
        ),
    ]
