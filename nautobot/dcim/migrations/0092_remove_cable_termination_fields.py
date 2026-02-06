# Generated manually to remove legacy termination_a/b fields from Cable
# These fields are replaced by the CableEnd junction table model

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0091_remove_cablepath_and_path_fields"),
    ]

    operations = [
        # First, remove constraints that reference the fields we're about to drop
        migrations.AlterModelOptions(
            name="cable",
            options={"ordering": ["pk"]},
        ),
        migrations.AlterUniqueTogether(
            name="cable",
            unique_together=set(),
        ),
        # Now safe to remove the legacy Cable termination fields
        migrations.RemoveField(
            model_name="cable",
            name="termination_a_type",
        ),
        migrations.RemoveField(
            model_name="cable",
            name="termination_a_id",
        ),
        migrations.RemoveField(
            model_name="cable",
            name="termination_b_type",
        ),
        migrations.RemoveField(
            model_name="cable",
            name="termination_b_id",
        ),
        # Remove the device cache fields
        migrations.RemoveField(
            model_name="cable",
            name="_termination_a_device",
        ),
        migrations.RemoveField(
            model_name="cable",
            name="_termination_b_device",
        ),
        # CableEnd constraints
        migrations.AlterUniqueTogether(
            name="cableend",
            unique_together={("cable_termination",)},
        ),
        # Remove legacy CableTermination fields
        migrations.RemoveField(
            model_name="cabletermination",
            name="_cable_peer_id",
        ),
        migrations.RemoveField(
            model_name="cabletermination",
            name="_cable_peer_type",
        ),
        migrations.RemoveField(
            model_name="cabletermination",
            name="cable",
        ),
    ]
