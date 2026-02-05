# Generated manually to populate CableEnd from existing Cable data

from django.db import migrations


def populate_cableend_from_cables(apps, schema_editor):
    """
    Create CableEnd objects at position 0 for all existing cables that use the legacy termination fields.
    """
    Cable = apps.get_model("dcim", "Cable")
    CableEnd = apps.get_model("dcim", "CableEnd")
    CableTermination = apps.get_model("dcim", "CableTermination")

    for cable in Cable.objects.all():
        # Create CableEnd for termination A if it exists
        if cable.termination_a_id:
            # Get the CableTermination instance for this termination
            # The termination_a_id matches the CableTermination id since we migrated them
            try:
                cable_termination_a = CableTermination.objects.get(id=cable.termination_a_id)
                CableEnd.objects.create(
                    cable=cable,
                    cable_termination=cable_termination_a,
                    cable_side="a",
                    position=0,
                )
            except CableTermination.DoesNotExist:
                # Skip if the termination doesn't exist in CableTermination table
                # This might happen if it's not a cable termination type
                pass

        # Create CableEnd for termination B if it exists
        if cable.termination_b_id:
            try:
                cable_termination_b = CableTermination.objects.get(id=cable.termination_b_id)
                CableEnd.objects.create(
                    cable=cable,
                    cable_termination=cable_termination_b,
                    cable_side="b",
                    position=0,
                )
            except CableTermination.DoesNotExist:
                # Skip if the termination doesn't exist in CableTermination table
                pass


def reverse_populate(apps, schema_editor):
    """
    Remove all CableEnd objects.
    """
    CableEnd = apps.get_model("dcim", "CableEnd")
    CableEnd.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0088_add_cableend_model"),
    ]

    operations = [
        migrations.RunPython(populate_cableend_from_cables, reverse_populate),
    ]
