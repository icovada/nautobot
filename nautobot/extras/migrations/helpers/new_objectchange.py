from django.contrib.contenttypes.models import ContentType
from django.db import connection

from nautobot.extras.models.change_logging import ChangeLoggedModel, ObjectChange


def make_funcs_for_model(app_name, model_name):
    def forward(apps, schema_editor):
        Model: ChangeLoggedModel = apps.get_model(app_name, model_name)
        ModelObjectChange = apps.get_model(app_name, f"{model_name}ObjectChange")

        for obj in ObjectChange.objects.filter(changed_object_type=ContentType.objects.get_for_model(Model)):
            if obj.changed_object is None:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"INSERT INTO {ModelObjectChange._meta.db_table} (changelog_ptr_id, target_uuid) VALUES (%s, %s)",
                        [obj.pk, obj.changed_object_id],
                    )
            else:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"INSERT INTO {ModelObjectChange._meta.db_table} (changelog_ptr_id, target_uuid, fktarget_id) VALUES (%s, %s, %s)",
                        [obj.pk, obj.changed_object_id, obj.changed_object_id],
                    )


    def reverse(apps, schema_editor):
        ...

    return forward, reverse
