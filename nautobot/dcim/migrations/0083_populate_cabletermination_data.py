# Generated manually for CableTermination polymorphic model data population

from django.db import migrations


def populate_cabletermination_from_children(apps, schema_editor):
    """
    Populate the CableTermination table with data from all child models.
    Each child record's data (id, cable fields, etc.) is copied to create a corresponding CableTermination parent record.
    """
    CableTermination = apps.get_model("dcim", "CableTermination")
    ContentType = apps.get_model("contenttypes", "ContentType")
    TaggedItem = apps.get_model("extras", "TaggedItem")

    cable_ct, _ = ContentType.objects.get_or_create(
        app_label="dcim",
        model="cabletermination",
        defaults={"model": "cabletermination"},
    )

    # List of child models in dcim app
    child_models = [
        "ConsolePort",
        "ConsoleServerPort",
        "PowerPort",
        "PowerOutlet",
        "Interface",
        "FrontPort",
        "RearPort",
    ]

    for model_name in child_models:
        Model = apps.get_model("dcim", model_name)
        child_ct = ContentType.objects.get(app_label="dcim", model=model_name.lower())

        # Get all instances of this model
        for instance in Model.objects.all():
            # Create a CableTermination record with the same ID and related fields
            CableTermination.objects.create(
                id=instance.id,
                created=instance.created,
                last_updated=instance.last_updated,
                _custom_field_data=instance._custom_field_data,
                cable=instance.cable,
                _cable_peer_id=instance._cable_peer_id,
                _cable_peer_type_id=instance._cable_peer_type_id,
                polymorphic_ctype=child_ct,
            )

            # Copy tags using TaggedItem through model
            for tagged_item in TaggedItem.objects.filter(content_type=child_ct, object_id=instance.id):
                TaggedItem.objects.create(
                    tag=tagged_item.tag,
                    content_type=cable_ct,
                    object_id=instance.id,
                )


def reverse_populate(apps, schema_editor):
    """
    Reverse migration: delete all CableTermination records.
    The child model data remains intact.
    """
    CableTermination = apps.get_model("dcim", "CableTermination")
    CableTermination.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0082_add_cabletermination_table"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(populate_cabletermination_from_children, reverse_populate),
    ]
