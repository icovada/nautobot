# Generated by Django 4.2.16 on 2024-12-04 21:32

import django.core.serializers.json
from django.db import migrations, models
import django.db.models.deletion
import nautobot.core.models.fields
import nautobot.core.models.tree_queries
import nautobot.extras.models.mixins
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("extras", "0117_optimization_initial_part_1"),
    ]

    operations = [
        migrations.CreateModel(
            name="TenantGroup",
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
                ("name", models.CharField(max_length=255, unique=True)),
                ("description", models.CharField(blank=True, max_length=255)),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="children",
                        to="tenancy.tenantgroup",
                    ),
                ),
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
                ("objects", nautobot.core.models.tree_queries.TreeManager()),
            ],
        ),
        migrations.CreateModel(
            name="Tenant",
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
                ("name", models.CharField(max_length=255, unique=True)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("comments", models.TextField(blank=True)),
                (
                    "tags",
                    nautobot.core.models.fields.TagsField(
                        through="extras.TaggedItem", to="extras.Tag"
                    ),
                ),
                (
                    "tenant_group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="tenants",
                        to="tenancy.tenantgroup",
                    ),
                ),
            ],
            options={
                "ordering": ["tenant_group", "name"],
            },
            bases=(
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
        ),
    ]
