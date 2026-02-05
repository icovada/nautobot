# Generated manually for final CircuitTermination structure

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("circuits", "0025_link_circuittermination_ptr"),
    ]

    operations = [
        # Remove old fields first (including the old id primary key)
        migrations.RemoveField(model_name="circuittermination", name="cable"),
        migrations.RemoveField(model_name="circuittermination", name="_cable_peer_id"),
        migrations.RemoveField(model_name="circuittermination", name="_cable_peer_type"),
        migrations.RemoveField(model_name="circuittermination", name="created"),
        migrations.RemoveField(model_name="circuittermination", name="last_updated"),
        migrations.RemoveField(model_name="circuittermination", name="_custom_field_data"),
        migrations.RemoveField(model_name="circuittermination", name="tags"),
        migrations.RemoveField(model_name="circuittermination", name="id"),
        # Now make cabletermination_ptr non-nullable and set as primary key
        migrations.AlterField(
            model_name="circuittermination",
            name="cabletermination_ptr",
            field=models.OneToOneField(
                auto_created=True,
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                primary_key=True,
                serialize=False,
                to="dcim.cabletermination",
            ),
        ),
    ]
