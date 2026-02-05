# Generated manually to remove _path field after CablePath deletion

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("circuits", "0026_finalize_circuittermination_structure"),
        ("dcim", "0091_remove_cablepath_and_path_fields"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="circuittermination",
            name="_path",
        ),
    ]
