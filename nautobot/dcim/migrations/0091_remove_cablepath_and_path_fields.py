# Generated manually to remove CablePath model and _path fields

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("circuits", "0026_finalize_circuittermination_structure"),
        ("dcim", "0090_alter_path_fields_before_cablepath_removal"),
    ]

    operations = [
        # Remove _path fields from PathEndpoint models before deleting CablePath
        migrations.RemoveField(
            model_name="consoleport",
            name="_path",
        ),
        migrations.RemoveField(
            model_name="consoleserverport",
            name="_path",
        ),
        migrations.RemoveField(
            model_name="interface",
            name="_path",
        ),
        migrations.RemoveField(
            model_name="powerport",
            name="_path",
        ),
        migrations.RemoveField(
            model_name="poweroutlet",
            name="_path",
        ),
        migrations.RemoveField(
            model_name="powerfeed",
            name="_path",
        ),
        # Now delete the CablePath model
        migrations.DeleteModel(
            name="CablePath",
        ),
    ]
