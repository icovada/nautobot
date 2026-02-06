# Generated manually to link CircuitTermination cabletermination_ptr field

from django.db import migrations


def link_ptr_field(apps, schema_editor):
    """
    Populate cabletermination_ptr field to link CircuitTermination to CableTermination.
    """
    CableTermination = apps.get_model("dcim", "CableTermination")
    CircuitTermination = apps.get_model("circuits", "CircuitTermination")

    for instance in CircuitTermination.objects.all():
        parent = CableTermination.objects.get(id=instance.id)
        instance.cabletermination_ptr = parent
        instance.save(update_fields=["cabletermination_ptr"])


def reverse_link(apps, schema_editor):
    """
    Clear cabletermination_ptr field.
    """
    CircuitTermination = apps.get_model("circuits", "CircuitTermination")
    CircuitTermination.objects.all().update(cabletermination_ptr=None)


class Migration(migrations.Migration):
    dependencies = [
        ("circuits", "0024_add_circuittermination_ptr"),
    ]

    operations = [
        migrations.RunPython(link_ptr_field, reverse_link),
    ]
