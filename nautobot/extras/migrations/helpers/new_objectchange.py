from django.contrib.contenttypes.models import ContentType

from nautobot.extras.models.change_logging import ChangeLoggedModel, ObjectChange


def make_funcs_for_model(app_name, model_name):
    def forward(apps, schema_editor):
        Model: ChangeLoggedModel = apps.get_model(app_name, model_name)
        ModelObjectChange = apps.get_model(app_name, f"{model_name}ObjectChange")
        FakeUser = apps.get_model("users", "user")
        FakeContentType = apps.get_model("contenttypes", "contenttype")

        for obj in ObjectChange.objects.filter(changed_object_type=ContentType.objects.get_for_model(Model)):
            data = {
                "time": obj.time,
                "user": FakeUser.objects.get(id=obj.user_id),
                "user_name": obj.user_name,
                "request_id": obj.request_id,
                "action": obj.action,
                "change_context": obj.change_context,
                "change_context_detail": obj.change_context_detail,
                "object_repr": obj.object_repr,
                "object_data": obj.object_data,
                "object_data_v2": obj.object_data_v2,
                "target_model_name": f"{obj._meta.app_label}_{obj._meta.object_name}changelog".lower(),
                "target_uuid": obj.changed_object_id,
                "fktarget": Model.objects.get(id=obj.changed_object_id),
                "changed_object_type": FakeContentType.objects.get(id=obj.changed_object_type_id),
                "changed_object_id": obj.changed_object_id,
            }

            obj.delete()

            ModelObjectChange.objects.create(**data)

    def reverse(apps, schema_editor):
        Model = apps.get_model(app_name, model_name)
        for obj in Model.objects.all():
            obj.some_field = "original"
            obj.save()

    return forward, reverse
