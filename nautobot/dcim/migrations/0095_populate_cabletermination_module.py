# Data migration: Copy module_id from subclass tables to dcim_cabletermination

from django.db import migrations


def copy_module_to_cabletermination(apps, schema_editor):
    """Copy module_id from each subclass table to the CableTermination base table."""
    subclass_tables = [
        "dcim_consoleport",
        "dcim_consoleserverport",
        "dcim_powerport",
        "dcim_poweroutlet",
        "dcim_interface",
        "dcim_frontport",
        "dcim_rearport",
        "dcim_powerfeed",
    ]
    with schema_editor.connection.cursor() as cursor:
        for table in subclass_tables:
            cursor.execute(
                f"""
                UPDATE dcim_cabletermination
                SET module_id = sub.module_id
                FROM {table} sub
                WHERE dcim_cabletermination.id = sub.cabletermination_ptr_id
                  AND sub.module_id IS NOT NULL
                """
            )


def copy_module_from_cabletermination(apps, schema_editor):
    """Reverse: Copy module_id from CableTermination back to subclass tables."""
    subclass_tables = [
        "dcim_consoleport",
        "dcim_consoleserverport",
        "dcim_powerport",
        "dcim_poweroutlet",
        "dcim_interface",
        "dcim_frontport",
        "dcim_rearport",
        "dcim_powerfeed",
    ]
    with schema_editor.connection.cursor() as cursor:
        for table in subclass_tables:
            cursor.execute(
                f"""
                UPDATE {table}
                SET module_id = ct.module_id
                FROM dcim_cabletermination ct
                WHERE {table}.cabletermination_ptr_id = ct.id
                  AND ct.module_id IS NOT NULL
                """
            )


class Migration(migrations.Migration):

    dependencies = [
        ("dcim", "0094_move_module_to_cabletermination"),
    ]

    operations = [
        migrations.RunPython(
            copy_module_to_cabletermination,
            copy_module_from_cabletermination,
        ),
    ]
