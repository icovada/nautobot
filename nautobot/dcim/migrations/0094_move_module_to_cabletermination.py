# Migration: Add module FK to CableTermination, update ComponentModel.device to nullable

import django.db.models.deletion
from django.db import migrations, models

import nautobot.core.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ("dcim", "0093_powerfeed__name_powerfeed_description_and_more"),
    ]

    operations = [
        # 1. Add module field to CableTermination table
        migrations.AddField(
            model_name="cabletermination",
            name="module",
            field=nautobot.core.models.fields.ForeignKeyWithAutoRelatedName(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="dcim.module",
            ),
        ),
    ]
