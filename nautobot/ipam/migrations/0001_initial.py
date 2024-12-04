# Generated by Django 4.2.16 on 2024-12-04 21:32

import django.core.serializers.json
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import nautobot.core.models.fields
import nautobot.extras.models.mixins
import nautobot.ipam.fields
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("dcim", "0064_optimization_initial_part_2"),
    ]

    operations = [
        migrations.CreateModel(
            name="IPAddress",
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
                ("host", nautobot.ipam.fields.VarbinaryIPField(db_index=True)),
                ("mask_length", models.IntegerField(db_index=True)),
                ("type", models.CharField(default="host", max_length=50)),
                ("ip_version", models.IntegerField(db_index=True, editable=False)),
                (
                    "dns_name",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        max_length=255,
                        validators=[
                            django.core.validators.RegexValidator(
                                code="invalid",
                                message="Only alphanumeric characters, hyphens, periods, and underscores are allowed in DNS names",
                                regex="^[0-9A-Za-z._-]+$",
                            )
                        ],
                    ),
                ),
                ("description", models.CharField(blank=True, max_length=255)),               
            ],
            options={
                "verbose_name": "IP address",
                "verbose_name_plural": "IP addresses",
                "ordering": ("ip_version", "host", "mask_length"),
            },
            bases=(
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
        ),
        migrations.CreateModel(
            name="IPAddressToInterface",
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
                ("is_source", models.BooleanField(default=False)),
                ("is_destination", models.BooleanField(default=False)),
                ("is_default", models.BooleanField(default=False)),
                ("is_preferred", models.BooleanField(default=False)),
                ("is_primary", models.BooleanField(default=False)),
                ("is_secondary", models.BooleanField(default=False)),
                ("is_standby", models.BooleanField(default=False)),
            ],
            options={
                "verbose_name": "IP Address Assignment",
                "verbose_name_plural": "IP Address Assignments",
            },
        ),
        migrations.CreateModel(
            name="Namespace",
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
                ("name", models.CharField(db_index=True, max_length=255, unique=True)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("location", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="namespaces",
                    to="dcim.location",
                )), 
            ],
            options={
                "ordering": ("name",),
            },
            bases=(
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
        ),
        migrations.CreateModel(
            name="Prefix",
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
                ("network", nautobot.ipam.fields.VarbinaryIPField(db_index=True)),
                ("broadcast", nautobot.ipam.fields.VarbinaryIPField(db_index=True)),
                ("prefix_length", models.IntegerField(db_index=True)),
                ("type", models.CharField(default="network", max_length=50)),
                ("ip_version", models.IntegerField(db_index=True, editable=False)),
                ("date_allocated", models.DateTimeField(blank=True, null=True)),
                ("description", models.CharField(blank=True, max_length=255)),
            ],
            options={
                "verbose_name_plural": "prefixes",
                "ordering": ("namespace", "ip_version", "network", "prefix_length"),
            },
            bases=(
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
        ),
        migrations.CreateModel(
            name="PrefixLocationAssignment",
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
            ],
            options={
                "ordering": ["prefix", "location"],
            },
        ),
        migrations.CreateModel(
            name="RIR",
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
                ("is_private", models.BooleanField(default=False)),
                ("description", models.CharField(blank=True, max_length=255)),
            ],
            options={
                "verbose_name": "RIR",
                "verbose_name_plural": "RIRs",
                "ordering": ["name"],
            },
            bases=(
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
        ),
        migrations.CreateModel(
            name="RouteTarget",
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
                ("name", models.CharField(max_length=21, unique=True)),
                ("description", models.CharField(blank=True, max_length=255)),
            ],
            options={
                "ordering": ["name"],
            },
            bases=(
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
        ),
        migrations.CreateModel(
            name="Service",
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
                ("name", models.CharField(db_index=True, max_length=255)),
                ("protocol", models.CharField(max_length=50)),
                (
                    "ports",
                    nautobot.core.models.fields.JSONArrayField(
                        base_field=models.PositiveIntegerField(
                            validators=[
                                django.core.validators.MinValueValidator(1),
                                django.core.validators.MaxValueValidator(65535),
                            ]
                        )
                    ),
                ),
                ("description", models.CharField(blank=True, max_length=255)),
            ],
            options={
                "ordering": ("protocol", "ports"),
            },
            bases=(
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
        ),
        migrations.CreateModel(
            name="VLAN",
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
                (
                    "vid",
                    models.PositiveSmallIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(4094),
                        ]
                    ),
                ),
                ("name", models.CharField(db_index=True, max_length=255)),
                ("description", models.CharField(blank=True, max_length=255)),
            ],
            options={
                "verbose_name": "VLAN",
                "verbose_name_plural": "VLANs",
                "ordering": ("vlan_group", "vid"),
            },
            bases=(
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
        ),
        migrations.CreateModel(
            name="VLANGroup",
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
                ("name", models.CharField(db_index=True, max_length=255, unique=True)),
                ("description", models.CharField(blank=True, max_length=255)),
                (
                    "range",
                    nautobot.core.models.fields.PositiveRangeNumberTextField(
                        default="1-4094"
                    ),
                ),
            ],
            options={
                "verbose_name": "VLAN group",
                "verbose_name_plural": "VLAN groups",
                "ordering": ("name",),
            },
            bases=(
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
        ),
        migrations.CreateModel(
            name="VLANLocationAssignment",
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
            ],
            options={
                "ordering": ["vlan", "location"],
            },
        ),
        migrations.CreateModel(
            name="VRF",
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
                ("name", models.CharField(db_index=True, max_length=255)),
                ("rd", models.CharField(blank=True, max_length=21, null=True)),
                ("description", models.CharField(blank=True, max_length=255)),
            ],
            options={
                "verbose_name": "VRF",
                "verbose_name_plural": "VRFs",
                "ordering": ("namespace", "name", "rd"),
            },
            bases=(
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
        ),
        migrations.CreateModel(
            name="VRFPrefixAssignment",
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
                (
                    "prefix",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vrf_assignments",
                        to="ipam.prefix",
                    ),
                ),
                (
                    "vrf",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="ipam.vrf",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="VRFDeviceAssignment",
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
                ("rd", models.CharField(blank=True, max_length=21, null=True)),
                ("name", models.CharField(blank=True, max_length=255)),
                (
                    "device",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vrf_assignments",
                        to="dcim.device",
                    ),
                ),
            ],
        ),
    ]
