# Generated by Django 4.2.16 on 2024-12-04 21:32

from django.db import migrations, models
import django.db.models.deletion
import nautobot.core.models.fields
import nautobot.extras.models.statuses


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("cloud", "0001_initial"),
        ("circuits", "0001_initial"),
        ("dcim", "0001_initial"),
        ("tenancy", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("extras", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="providernetwork",
            name="tags",
            field=nautobot.core.models.fields.TagsField(
                through="extras.TaggedItem", to="extras.Tag"
            ),
        ),
        migrations.AddField(
            model_name="provider",
            name="tags",
            field=nautobot.core.models.fields.TagsField(
                through="extras.TaggedItem", to="extras.Tag"
            ),
        ),
        migrations.AddField(
            model_name="circuittermination",
            name="_cable_peer_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="contenttypes.contenttype",
            ),
        ),
        migrations.AddField(
            model_name="circuittermination",
            name="_path",
            field=nautobot.core.models.fields.ForeignKeyWithAutoRelatedName(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="dcim.cablepath",
            ),
        ),
        migrations.AddField(
            model_name="circuittermination",
            name="cable",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="dcim.cable",
            ),
        ),
        migrations.AddField(
            model_name="circuittermination",
            name="circuit",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="circuit_terminations",
                to="circuits.circuit",
            ),
        ),
        migrations.AddField(
            model_name="circuittermination",
            name="cloud_network",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="circuit_terminations",
                to="cloud.cloudnetwork",
            ),
        ),
        migrations.AddField(
            model_name="circuittermination",
            name="location",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="circuit_terminations",
                to="dcim.location",
            ),
        ),
        migrations.AddField(
            model_name="circuittermination",
            name="provider_network",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="circuit_terminations",
                to="circuits.providernetwork",
            ),
        ),
        migrations.AddField(
            model_name="circuittermination",
            name="tags",
            field=nautobot.core.models.fields.TagsField(
                through="extras.TaggedItem", to="extras.Tag"
            ),
        ),
        migrations.AddField(
            model_name="circuit",
            name="circuit_termination_a",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="circuits.circuittermination",
            ),
        ),
        migrations.AddField(
            model_name="circuit",
            name="circuit_termination_z",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="circuits.circuittermination",
            ),
        ),
        migrations.AddField(
            model_name="circuit",
            name="circuit_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="circuits",
                to="circuits.circuittype",
            ),
        ),
        migrations.AddField(
            model_name="circuit",
            name="provider",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="circuits",
                to="circuits.provider",
            ),
        ),
        migrations.AddField(
            model_name="circuit",
            name="status",
            field=nautobot.extras.models.statuses.StatusField(
                on_delete=django.db.models.deletion.PROTECT, to="extras.status"
            ),
        ),
        migrations.AddField(
            model_name="circuit",
            name="tags",
            field=nautobot.core.models.fields.TagsField(
                through="extras.TaggedItem", to="extras.Tag"
            ),
        ),
        migrations.AddField(
            model_name="circuit",
            name="tenant",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="circuits",
                to="tenancy.tenant",
            ),
        ),
        migrations.AddConstraint(
            model_name="providernetwork",
            constraint=models.UniqueConstraint(
                fields=("provider", "name"),
                name="circuits_providernetwork_provider_name",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="providernetwork",
            unique_together={("provider", "name")},
        ),
        migrations.AlterUniqueTogether(
            name="circuittermination",
            unique_together={("circuit", "term_side")},
        ),
        migrations.AlterUniqueTogether(
            name="circuit",
            unique_together={("provider", "cid")},
        ),
    ]
