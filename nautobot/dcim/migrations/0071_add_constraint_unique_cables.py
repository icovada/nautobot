from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0070_alter_cable_unique_together"),
    ]

    operations = [
        migrations.RunSQL(
            """
            CREATE UNIQUE INDEX unique_unordered_uuid_cable_pair
            ON dcim_cable (
                LEAST(termination_a_id, termination_b_id),
                GREATEST(termination_a_id, termination_b_id),
                termination_a_type_id,
                termination_b_type_id
            );
            """,
            reverse_sql="DROP INDEX unique_unordered_uuid_cable_pair;",
        ),
    ]
