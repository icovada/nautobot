# Generated by Django 4.2.13 on 2024-06-21 19:02

import uuid

import django.core.serializers.json
from django.db import migrations, models
import django.db.models.deletion

import nautobot.core.models.fields
import nautobot.extras.models.metadata
import nautobot.extras.models.mixins
import nautobot.extras.utils


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("extras", "0108_alter_configcontext_cluster_groups_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="MetadataType",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                (
                    "_custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder),
                ),
                ("name", models.CharField(max_length=255, unique=True)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("data_type", models.CharField(max_length=50)),
                (
                    "content_types",
                    models.ManyToManyField(
                        limit_choices_to=nautobot.extras.utils.FeatureQuery("metadata"),
                        related_name="metadata_types",
                        to="contenttypes.contenttype",
                    ),
                ),
                ("tags", nautobot.core.models.fields.TagsField(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={
                "ordering": ["name"],
            },
            bases=(
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
            managers=[
                ("objects", nautobot.extras.models.metadata.MetadataTypeManager()),
            ],
        ),
        migrations.CreateModel(
            name="ObjectMetadata",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                (
                    "scoped_fields",
                    nautobot.core.models.fields.JSONArrayField(base_field=models.CharField(max_length=255)),
                ),
                ("value", models.JSONField(blank=True, null=True)),
                ("assigned_object_id", models.UUIDField(db_index=True)),
                (
                    "assigned_object_type",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="contenttypes.contenttype",
                    ),
                ),
                (
                    "contact",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="object_metadatas",
                        to="extras.contact",
                    ),
                ),
                (
                    "metadata_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="object_metadatas",
                        to="extras.metadatatype",
                    ),
                ),
                (
                    "team",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="object_metadatas",
                        to="extras.team",
                    ),
                ),
            ],
            options={
                "ordering": ["metadata_type"],
                "indexes": [
                    models.Index(fields=["assigned_object_type", "assigned_object_id"], name="assigned_object"),
                    models.Index(
                        fields=["assigned_object_type", "assigned_object_id", "contact"], name="assigned_object_contact"
                    ),
                    models.Index(
                        fields=["assigned_object_type", "assigned_object_id", "team"], name="assigned_object_team"
                    ),
                ],
                "unique_together": {("metadata_type", "assigned_object_type", "assigned_object_id", "scoped_fields")},
            },
        ),
        migrations.CreateModel(
            name="MetadataChoice",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("value", models.CharField(max_length=255)),
                ("weight", models.PositiveSmallIntegerField(default=100)),
                (
                    "metadata_type",
                    models.ForeignKey(
                        limit_choices_to=models.Q(("data_type__in", ["select", "multi-select"])),
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="choices",
                        to="extras.metadatatype",
                    ),
                ),
            ],
            options={
                "ordering": ["metadata_type", "weight", "value"],
                "unique_together": {("metadata_type", "value")},
            },
        ),
    ]
