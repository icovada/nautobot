# Generated manually for CircuitTermination polymorphic restructuring

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("circuits", "0023_populate_circuittermination_cabletermination"),
        ("dcim", "0082_add_cabletermination_table"),
    ]

    operations = [
        migrations.AddField(
            model_name="circuittermination",
            name="cabletermination_ptr",
            field=models.OneToOneField(
                auto_created=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                to="dcim.cabletermination",
            ),
        ),
    ]
