from threading import local
from typing import Any

from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.urls import NoReverseMatch, reverse

from nautobot.core.celery import NautobotKombuJSONEncoder
from nautobot.core.models import BaseModel
from nautobot.core.models.utils import serialize_object, serialize_object_v2
from nautobot.core.utils.data import shallow_compare_dict
from nautobot.core.utils.lookup import get_route_for_model
from nautobot.extras.choices import ObjectChangeActionChoices, ObjectChangeEventContextChoices
from nautobot.extras.constants import CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL, CHANGELOG_MAX_OBJECT_REPR
from nautobot.extras.models.managers import FastInheritanceManager
from nautobot.extras.utils import extras_features

#
# Change logging
#

_thread_local = local()


class ChangeLoggedModel(models.Model):
    """
    An abstract model which adds fields to store the creation and last-updated times for an object. Both fields can be
    null to facilitate adding these fields to existing instances via a database migration.
    """

    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        abstract = True

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # Store the class for later processing
        if not hasattr(cls, '_changelog_setup_done'):
            cls._changelog_setup_done = False

        # Connect signals immediately (they don't need the relationship model)
        cls._connect_signals()

    @classmethod
    def _ensure_changelog_setup(cls):
        """
        Ensure the changelog relationship is set up.
        This is called lazily when needed.
        """
        if cls._changelog_setup_done:
            return

        # Create the relationship model
        cls._create_changelog_relationship()
        cls._changelog_setup_done = True

    @classmethod
    def _create_changelog_relationship(cls):
        """
        Dynamically create a model that links this model to ObjectChange
        """
        # Create the relationship model name
        rel_model_name = f"{cls.__name__}ObjectChange"

        # Check if the model already exists
        try:
            existing_model = apps.get_model(
                cls._meta.app_label, rel_model_name)
            cls._changelog_rel_model = existing_model
            return
        except LookupError:
            pass

        # Get name of object model this changelog refers to
        # eg. this is a DeviceObjectChange, we want normal_device
        target_model_name = f"{cls._meta.app_label}_{cls.__name__}changelog".lower()

        # Create the relationship model
        attrs = {
            '__module__': cls.__module__,
            'Meta': type('Meta', (), {
                'app_label': cls._meta.app_label,
            }),
            'changelog_ptr': models.OneToOneField(
                ObjectChange,
                on_delete=models.CASCADE,
                parent_link=True,
                related_name=target_model_name
            ),
            'changed_object': models.ForeignKey(
                cls,
                on_delete=models.SET_NULL,
                related_name='change_logs',
                null=True
            ),
            'target_uuid': models.UUIDField()
        }

        rel_model = type(rel_model_name, (ObjectChange,), attrs)
        admin.site.register(rel_model)

        # Store reference to the relationship model
        cls._changelog_rel_model = rel_model

    @classmethod
    def _get_changelog_rel_model(cls):
        """Get the changelog relationship model, creating it if necessary"""
        if not hasattr(cls, '_changelog_rel_model'):
            cls._ensure_changelog_setup()
        return cls._changelog_rel_model

    @classmethod
    def _connect_signals(cls):
        """Connect the change tracking signals"""

        @receiver(pre_save, sender=cls, weak=False)
        def pre_save_handler(sender, instance, **kwargs):
            if instance.pk:
                try:
                    _thread_local.old_instance = sender.objects.get(
                        pk=instance.pk)
                except sender.DoesNotExist:
                    _thread_local.old_instance = None
            else:
                _thread_local.old_instance = None

        @receiver(post_save, sender=cls, weak=False)
        def post_save_handler(sender, instance, created, **kwargs):

            target_model_name = f"{cls._meta.app_label}_{cls.__name__}changelog".lower()

            # Get user from thread local if available
            user = getattr(_thread_local, 'user', None)
            old_instance = getattr(_thread_local, 'old_instance', None)

            if created:
                action = 'CREATE'
                old_values = None
                new_values = cls._serialize_instance(instance)
                changed_fields = None
            else:
                action = 'UPDATE'
                old_values = cls._serialize_instance(
                    old_instance) if old_instance else None
                new_values = cls._serialize_instance(instance)
                changed_fields = cls._get_changed_fields(
                    old_instance, instance)

            # Create the ObjectChange entry
            rel_model = cls._get_changelog_rel_model()
            changelog: ObjectChange = rel_model.objects.create(
                action=action,
                user=user,
                old_values=old_values,
                new_values=new_values,
                changed_fields=changed_fields,
                changed_object=instance,
                target_uuid=instance.id,
                target_model_name=target_model_name,
            )

        @receiver(post_delete, sender=cls, weak=False)
        def post_delete_handler(sender, instance, **kwargs):
            user = getattr(_thread_local, 'user', None)

            target_model_name = f"{cls._meta.app_label}_{cls.__name__}changelog".lower()

            # Create the ObjectChange entry for deletion
            rel_model: models.Model | type[_] = cls._get_changelog_rel_model()
            changelog = rel_model.objects.create(
                action='DELETE',
                user=user,
                old_values=cls._serialize_instance(instance),
                new_values=None,
                changed_fields=None,
                target_uuid=instance.id,
                target_model_name=target_model_name,
            )


    @classmethod
    def _serialize_instance(cls, instance):
        """Serialize model instance to JSON-compatible dict"""
        if not instance:
            return None

        data = {}
        for field in instance._meta.fields:
            value = getattr(instance, field.name)

            # Handle different field types
            if field.name == "id":
                continue
            elif isinstance(field, models.DateTimeField) and value:
                data[field.name] = value.isoformat()
            elif isinstance(field, models.UUIDField) and value:
                data[field.name] = str(value)
            elif isinstance(field, models.ForeignKey) and value:
                data[field.name] = str(value.pk)
            elif hasattr(value, 'pk'):
                data[field.name] = value.pk
            else:
                data[field.name] = value

        return data

    @classmethod
    def _get_changed_fields(cls, old_instance, new_instance):
        """Get list of changed fields between two instances"""
        if not old_instance:
            return None

        changed = []
        for field in new_instance._meta.fields:
            old_value = getattr(old_instance, field.name)
            new_value = getattr(new_instance, field.name)

            if old_value != new_value:
                changed.append(field.name)

        return changed if changed else None

    def get_change_logs(self):
        """Get all change logs for this instance"""
        rel_model = self.__class__._get_changelog_rel_model()
        relations = rel_model.objects.filter(**{
            self.__class__.__name__.lower(): self
        }).select_related('changelog')
        return [rel.changelog for rel in relations]

    def to_objectchange(self, action, *, related_object=None, object_data_extra=None, object_data_exclude=None):
        """
        Return a new ObjectChange representing a change made to this object, or None if the object shouldn't be logged.

        This will typically be called automatically by ChangeLoggingMiddleware.
        """
        return ObjectChange(
            changed_object=self,
            object_repr=str(self)[:CHANGELOG_MAX_OBJECT_REPR],
            action=action,
            object_data=serialize_object(self, extra=object_data_extra, exclude=object_data_exclude),
            object_data_v2=serialize_object_v2(self),
            related_object=related_object,
        )

    def get_changelog_url(self):
        """Return the changelog URL for this object."""
        route = get_route_for_model(self, "changelog")

        # Iterate the pk-like fields and try to get a URL, or return None.
        fields = ["pk", "slug"]
        for field in fields:
            if not hasattr(self, field):
                continue

            try:
                return reverse(route, kwargs={field: getattr(self, field)})
            except NoReverseMatch:
                continue

        return None


@extras_features("graphql")
class ObjectChange(BaseModel):
    """
    Record a change to an object and the user account associated with that change. A change record may optionally
    indicate an object related to the one being changed. For example, a change to an interface may also indicate the
    parent device. This will ensure changes made to component models appear in the parent model's changelog.
    """

    time = models.DateTimeField(auto_now_add=True, editable=False, db_index=True)
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="object_changes",
        blank=True,
        null=True,
    )
    user_name = models.CharField(max_length=150, editable=False, db_index=True)
    request_id = models.UUIDField(editable=False, db_index=True)
    action = models.CharField(max_length=50, choices=ObjectChangeActionChoices)
    changed_object_type = models.ForeignKey(to=ContentType, on_delete=models.SET_NULL, null=True, related_name="+")
    change_context = models.CharField(
        max_length=50,
        choices=ObjectChangeEventContextChoices,
        editable=False,
        db_index=True,
    )
    change_context_detail = models.CharField(max_length=CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL, blank=True, editable=False)
    related_object_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
    )
    # todoindex:
    related_object_id = models.UUIDField(blank=True, null=True)
    related_object = GenericForeignKey(ct_field="related_object_type", fk_field="related_object_id")
    object_repr = models.CharField(max_length=CHANGELOG_MAX_OBJECT_REPR, editable=False)
    object_data = models.JSONField(encoder=DjangoJSONEncoder, editable=False)
    object_data_v2 = models.JSONField(encoder=NautobotKombuJSONEncoder, editable=False, null=True, blank=True)
    target_model_name = models.CharField(max_length=30, blank=True, null=True)
    objects = FastInheritanceManager()

    documentation_static_path = "docs/user-guide/platform-functionality/change-logging.html"
    natural_key_field_names = ["pk"]

    class Meta:
        ordering = ["-time"]
        get_latest_by = "time"
        # [request_id, changed_object_type, changed_object_id] is not sufficient to uniquely identify an ObjectChange,
        # as a single bulk-create or bulk-edit REST API request may modify the same object multiple times, such as in
        # the case of creating CircuitTerminations for both ends of a single Circuit in a single request.
        unique_together = [
            ["time", "request_id", "changed_object_type"],
        ]
        indexes = [
            models.Index(
                name="extras_objectchange_triple_idx",
                fields=["request_id", "changed_object_type_id"],
            ),
            models.Index(
                name="related_object_idx",
                fields=["related_object_type", "related_object_id"],
            ),
            models.Index(
                name="user_changed_object_typex",
                fields=["user", "changed_object_type"],
            ),
        ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.upgraded_to_subclass = False
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"{self.changed_object_type} {self.object_repr} {self.get_action_display().lower()} by {self.user_name}"

    def save(self, *args, **kwargs):
        # Record the user's name and the object's representation as static strings
        if not self.user_name:
            if self.user:
                self.user_name = self.user.username
            else:
                self.user_name = "Undefined"

        if not self.object_repr:
            self.object_repr = str(self.changed_object)[:CHANGELOG_MAX_OBJECT_REPR]

        return super().save(*args, **kwargs)

    def get_action_class(self):
        return ObjectChangeActionChoices.CSS_CLASSES.get(self.action)

    def get_next_change(self, user=None, only=None):
        """Return next change for this changed object, optionally restricting by user view permission"""
        related_changes = self.get_related_changes(user=user)
        if only:
            related_changes = related_changes.only(*only)
        return related_changes.filter(time__gt=self.time).order_by("time").first()

    def get_prev_change(self, user=None, only=None):
        """Return previous change for this changed object, optionally restricting by user view permission"""
        related_changes = self.get_related_changes(user=user)
        if only:
            related_changes = related_changes.only(*only)
        return related_changes.filter(time__lt=self.time).order_by("-time").first()

    def get_related_changes(self, user=None, permission="view"):
        """Return queryset of all ObjectChanges for this changed object, excluding this ObjectChange"""
        related_changes = ObjectChange.objects.filter(
            changed_object_type=self.changed_object_type,
            changed_object_id=self.changed_object_id,
        ).exclude(pk=self.pk)
        if user is not None:
            return related_changes.restrict(user, permission)
        return related_changes

    def get_snapshots(self, pre_object_data=None, pre_object_data_v2=None):
        """
        Return a dictionary with the changed object's serialized data before and after this change
        occurred and a key with a shallow diff of those dictionaries.

        Returns:
        {
            "prechange": dict(),
            "postchange": dict(),
            "differences": {
                "removed": dict(),
                "added": dict(),
            }
        }
        """
        prechange = None
        postchange = None
        prior_change = None

        # Populate the prechange field, create actions do not need to have a prechange field
        if self.action != ObjectChangeActionChoices.ACTION_CREATE:
            prior_change = self.get_prev_change(only=["object_data_v2", "object_data"])
            # Deal with the cases where we are trying to capture an object deletion/update and there is no prior change record.
            # This can happen when the object is first created and the changelog for that object creation action is deleted.
            if prior_change is not None:
                prechange = prior_change.object_data_v2 or prior_change.object_data
            elif self.action == ObjectChangeActionChoices.ACTION_DELETE:
                prechange = self.object_data_v2 or self.object_data
            else:
                prechange = pre_object_data_v2 or pre_object_data

        # Populate the postchange field, delete actions do not need to have a postchange field
        if self.action != ObjectChangeActionChoices.ACTION_DELETE:
            postchange = self.object_data_v2
            if postchange is None:
                postchange = self.object_data

        if prechange and postchange:
            if self.object_data_v2 is None or (prior_change and prior_change.object_data_v2 is None):
                prechange = prior_change.object_data
                postchange = self.object_data
            diff_added = shallow_compare_dict(prechange, postchange, exclude=["last_updated"])
            diff_removed = {x: prechange.get(x) for x in diff_added}
        elif prechange and not postchange:
            diff_added, diff_removed = None, prechange
        else:
            diff_added, diff_removed = postchange, None

        return {
            "prechange": prechange,
            "postchange": postchange,
            "differences": {"removed": diff_removed, "added": diff_added},
        }
