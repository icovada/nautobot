# Generated manually to link cabletermination_ptr fields

from django.db import migrations


def link_ptr_fields(apps, schema_editor):
    """
    Populate cabletermination_ptr fields to link each child instance to its parent CableTermination.
    Since we copied the same IDs, each child's ptr should point to the CableTermination with matching ID.
    """
    CableTermination = apps.get_model("dcim", "CableTermination")

    child_models = [
        "ConsolePort",
        "ConsoleServerPort",
        "PowerPort",
        "PowerOutlet",
        "Interface",
        "FrontPort",
        "RearPort",
        "PowerFeed",
    ]

    for model_name in child_models:
        Model = apps.get_model("dcim", model_name)

        for instance in Model.objects.all():
            # Link to the CableTermination with the same ID
            parent = CableTermination.objects.get(id=instance.id)
            instance.cabletermination_ptr = parent
            instance.save(update_fields=["cabletermination_ptr"])


def reverse_link(apps, schema_editor):
    """
    Clear cabletermination_ptr fields.
    """
    child_models = [
        "ConsolePort",
        "ConsoleServerPort",
        "PowerPort",
        "PowerOutlet",
        "Interface",
        "FrontPort",
        "RearPort",
        "PowerFeed",
    ]

    for model_name in child_models:
        Model = apps.get_model("dcim", model_name)
        Model.objects.all().update(cabletermination_ptr=None)


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0085_add_cabletermination_ptr_fields"),
    ]

    operations = [
        migrations.RunPython(link_ptr_fields, reverse_link),
    ]
