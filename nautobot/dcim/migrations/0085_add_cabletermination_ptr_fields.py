# Generated manually for CableTermination polymorphic restructuring

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0084_populate_powerfeed_cabletermination"),
    ]

    operations = [
        # Add cabletermination_ptr to all child models (nullable initially)
        migrations.AddField(
            model_name="consoleport",
            name="cabletermination_ptr",
            field=models.OneToOneField(
                auto_created=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                to="dcim.cabletermination",
            ),
        ),
        migrations.AddField(
            model_name="consoleserverport",
            name="cabletermination_ptr",
            field=models.OneToOneField(
                auto_created=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                to="dcim.cabletermination",
            ),
        ),
        migrations.AddField(
            model_name="powerport",
            name="cabletermination_ptr",
            field=models.OneToOneField(
                auto_created=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                to="dcim.cabletermination",
            ),
        ),
        migrations.AddField(
            model_name="poweroutlet",
            name="cabletermination_ptr",
            field=models.OneToOneField(
                auto_created=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                to="dcim.cabletermination",
            ),
        ),
        migrations.AddField(
            model_name="interface",
            name="cabletermination_ptr",
            field=models.OneToOneField(
                auto_created=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                to="dcim.cabletermination",
            ),
        ),
        migrations.AddField(
            model_name="frontport",
            name="cabletermination_ptr",
            field=models.OneToOneField(
                auto_created=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                to="dcim.cabletermination",
            ),
        ),
        migrations.AddField(
            model_name="rearport",
            name="cabletermination_ptr",
            field=models.OneToOneField(
                auto_created=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                to="dcim.cabletermination",
            ),
        ),
        migrations.AddField(
            model_name="powerfeed",
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
