# Generated manually for PowerFeed CableTermination data population

from django.db import migrations


def populate_powerfeed_cabletermination(apps, schema_editor):
    """
    Populate CableTermination table with data from PowerFeed instances.
    """
    CableTermination = apps.get_model("dcim", "CableTermination")
    PowerFeed = apps.get_model("dcim", "PowerFeed")
    ContentType = apps.get_model("contenttypes", "ContentType")
    TaggedItem = apps.get_model("extras", "TaggedItem")

    powerfeed_ct, _ = ContentType.objects.get_or_create(app_label="dcim", model="powerfeed")
    cable_ct, _ = ContentType.objects.get_or_create(
        app_label="dcim",
        model="cabletermination",
        defaults={"model": "cabletermination"},
    )

    for instance in PowerFeed.objects.all():
        CableTermination.objects.create(
            id=instance.id,
            created=instance.created,
            last_updated=instance.last_updated,
            _custom_field_data=instance._custom_field_data,
            cable=instance.cable,
            _cable_peer_id=instance._cable_peer_id,
            _cable_peer_type_id=instance._cable_peer_type_id,
            polymorphic_ctype=powerfeed_ct,
        )

        # Copy tags using TaggedItem through model
        for tagged_item in TaggedItem.objects.filter(content_type=powerfeed_ct, object_id=instance.id):
            TaggedItem.objects.create(
                tag=tagged_item.tag,
                content_type=cable_ct,
                object_id=instance.id,
            )


def reverse_populate(apps, schema_editor):
    """
    Remove CableTermination records for PowerFeed instances.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")
    content_type, _ = ContentType.objects.get_or_create(app_label="dcim", model="powerfeed")
    CableTermination = apps.get_model("dcim", "CableTermination")
    CableTermination.objects.filter(polymorphic_ctype=content_type).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0083_populate_cabletermination_data"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(populate_powerfeed_cabletermination, reverse_populate),
    ]
