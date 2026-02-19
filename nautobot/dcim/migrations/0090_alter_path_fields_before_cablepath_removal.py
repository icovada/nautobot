# Generated manually to prepare _path fields for CablePath removal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0089_populate_cableend_from_cables"),
    ]

    operations = [
        # Make _path fields nullable and remove FK constraint to prepare for CablePath deletion
        migrations.AlterField(
            model_name="consoleport",
            name="_path",
            field=models.UUIDField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="consoleserverport",
            name="_path",
            field=models.UUIDField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="interface",
            name="_path",
            field=models.UUIDField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="powerport",
            name="_path",
            field=models.UUIDField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="poweroutlet",
            name="_path",
            field=models.UUIDField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="powerfeed",
            name="_path",
            field=models.UUIDField(null=True, blank=True),
        ),
    ]
