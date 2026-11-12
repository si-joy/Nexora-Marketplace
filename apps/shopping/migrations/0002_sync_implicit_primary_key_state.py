# Reconcile implicit Django PK metadata with earlier hand-written BigAutoField migrations.
# The physical PK column is already BigAutoField. Only migration STATE changes.
from django.db import migrations, models


def django_implicit_pk():
    return models.BigAutoField(
        auto_created=True,
        primary_key=True,
        serialize=False,
        verbose_name="ID",
    )


class Migration(migrations.Migration):
    dependencies = [("shopping", "0001_initial")]

    operations = [
        migrations.SeparateDatabaseAndState(
            # No SQL: these ID columns already exist with the correct DB type.
            database_operations=[],
            state_operations=[
            migrations.AlterField(
                model_name="cart",
                name="id",
                field=django_implicit_pk(),
            ),
            migrations.AlterField(
                model_name="cartitem",
                name="id",
                field=django_implicit_pk(),
            ),
            ],
        ),
    ]
