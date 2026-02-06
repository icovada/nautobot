# Generated manually for CableTermination polymorphic model

import uuid

import django.contrib.contenttypes.models
import django.core.serializers.json
import django.db.models.deletion
from django.db import migrations, models

import nautobot.core.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("dcim", "0081_alter_device_device_redundancy_group_priority_and_more"),
    ]

    operations = [
        # Create the CableTermination table
        migrations.CreateModel(
            name="CableTermination",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                (
                    "_custom_field_data",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        encoder=django.core.serializers.json.DjangoJSONEncoder,
                    ),
                ),
                ("_cable_peer_id", models.UUIDField(blank=True, null=True)),
                (
                    "_cable_peer_type",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="contenttypes.contenttype",
                    ),
                ),
                (
                    "cable",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="dcim.cable",
                    ),
                ),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_%(app_label)s.%(class)s_set+",
                        to="contenttypes.contenttype",
                    ),
                ),
                (
                    "tags",
                    nautobot.core.models.fields.TagsField(through="extras.TaggedItem", to="extras.Tag"),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=(models.Model,),
        ),
    ]
