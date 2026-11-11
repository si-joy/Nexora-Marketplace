from django.db import migrations


def create_bdt(apps, schema_editor):
    Currency = apps.get_model("catalog", "Currency")
    Currency.objects.using(schema_editor.connection.alias).get_or_create(
        code="BDT", defaults={"name": "Bangladeshi Taka", "symbol": "৳", "decimal_places": 2, "is_active": True}
    )


class Migration(migrations.Migration):
    dependencies = [("catalog", "0001_initial")]
    operations = [migrations.RunPython(create_bdt, migrations.RunPython.noop)]
