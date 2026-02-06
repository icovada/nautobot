# Generated manually for CircuitTermination CableTermination data population

from django.db import migrations, models


def populate_circuittermination_cabletermination(apps, schema_editor):
    """
    Populate CableTermination table with data from CircuitTermination instances.
    """
    CableTermination = apps.get_model("dcim", "CableTermination")
    CircuitTermination = apps.get_model("circuits", "CircuitTermination")
    ContentType = apps.get_model("contenttypes", "ContentType")
    TaggedItem = apps.get_model("extras", "TaggedItem")

    circuit_ct, _ = ContentType.objects.get_or_create(app_label="circuits", model="circuittermination")
    cable_ct, _ = ContentType.objects.get_or_create(
        app_label="dcim",
        model="cabletermination",
        defaults={"model": "cabletermination"},
    )

    for instance in CircuitTermination.objects.all():
        CableTermination.objects.create(
            id=instance.id,
            created=instance.created,
            last_updated=instance.last_updated,
            _custom_field_data=instance._custom_field_data,
            cable=instance.cable,
            _cable_peer_id=instance._cable_peer_id,
            _cable_peer_type_id=instance._cable_peer_type_id,
            polymorphic_ctype=circuit_ct,
        )

        # Copy tags using TaggedItem through model
        for tagged_item in TaggedItem.objects.filter(content_type=circuit_ct, object_id=instance.id):
            TaggedItem.objects.create(
                tag=tagged_item.tag,
                content_type=cable_ct,
                object_id=instance.id,
            )


def reverse_populate(apps, schema_editor):
    """
    Remove CableTermination records for CircuitTermination instances.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")
    content_type, _ = ContentType.objects.get_or_create(app_label="circuits", model="circuittermination")
    CableTermination = apps.get_model("dcim", "CableTermination")
    CableTermination.objects.filter(polymorphic_ctype=content_type).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("circuits", "0022_circuittermination_cloud_network"),
        ("dcim", "0090_alter_path_fields_before_cablepath_removal"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        # First alter the _path field to remove FK constraint to CablePath
        migrations.AlterField(
            model_name="circuittermination",
            name="_path",
            field=models.UUIDField(null=True, blank=True),
        ),
        # Then run the data migration
        migrations.RunPython(populate_circuittermination_cabletermination, reverse_populate),
    ]
