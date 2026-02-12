# Migration: Remove module field from subclass tables, update constraints

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("dcim", "0095_populate_cabletermination_module"),
    ]

    operations = [
        # Remove constraints from Interface and FrontPort (the only models that still
        # have them in migration state — the others had theirs removed in 0088).
        migrations.RemoveConstraint(
            model_name="interface",
            name="dcim_interface_device_name_unique",
        ),
        migrations.RemoveConstraint(
            model_name="interface",
            name="dcim_interface_module_name_unique",
        ),
        migrations.RemoveConstraint(
            model_name="frontport",
            name="dcim_frontport_device_name_unique",
        ),
        migrations.RemoveConstraint(
            model_name="frontport",
            name="dcim_frontport_module_name_unique",
        ),
        # Remove module field from subclass tables
        migrations.RemoveField(
            model_name="consoleport",
            name="module",
        ),
        migrations.RemoveField(
            model_name="consoleserverport",
            name="module",
        ),
        migrations.RemoveField(
            model_name="powerport",
            name="module",
        ),
        migrations.RemoveField(
            model_name="poweroutlet",
            name="module",
        ),
        migrations.RemoveField(
            model_name="interface",
            name="module",
        ),
        migrations.RemoveField(
            model_name="frontport",
            name="module",
        ),
        migrations.RemoveField(
            model_name="rearport",
            name="module",
        ),
        migrations.RemoveField(
            model_name="powerfeed",
            name="module",
        ),
    ]
