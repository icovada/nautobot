from __future__ import annotations

from typing import Any, TypeVar

from django.contrib.contenttypes.models import ContentType
from django.db import models
from model_utils.managers import (
    InheritanceManager,
    InheritanceManagerMixin,
    InheritanceQuerySet,
    InheritanceQuerySetMixin,
)

from nautobot.core.models.querysets import RestrictedQuerySet

ModelT = TypeVar("ModelT", bound=models.Model, covariant=True)


class FastInheritanceQuerySetMixin(InheritanceQuerySetMixin, models.QuerySet):
    def select_subclasses(self, *subclasses: str | type[models.Model]) -> InheritanceQuerySet:
        if not subclasses:
            selected_subclasses = {
                f"_{ContentType.objects.get_for_id(x['changed_object_type']).app_label}_{ContentType.objects.get_for_id(x['changed_object_type']).model}changelog".lower()
                for x in self.values("changed_object_type").distinct("changed_object_type").order_by("changed_object_type")
            }
            try:
                # During the migration there will be a moment when the target_model_name column is empty and
                # the above code will return { None }. We don't want that.
                selected_subclasses.remove(None)
            except KeyError:
                pass
        else:
            selected_subclasses = subclasses

        try:
            return super().select_subclasses(*selected_subclasses)
        except ValueError:
            return self


class FastInheritanceQuerySet(FastInheritanceQuerySetMixin, InheritanceQuerySet, RestrictedQuerySet):
    def _fetch_all(self):
        if self._result_cache is None:
            self._result_cache = list(self._iterable_class(self))

    def get(self, *args: Any, **kwargs: Any) -> FastInheritanceQuerySet:
        # Bit of an ugly hack: Views call QuerySets, not Models, so we have to call select_subclasses from here
        # Unfortunately this will JOIN against ALL possible tables nullifying the Fast part of this QuerySet
        # TODO: make Fast again

        return self.select_subclasses()._superget(*args, **kwargs)

    def _superget(self, *args: Any, **kwargs: Any) -> FastInheritanceQuerySet:
        return super().get(*args, **kwargs)

class FastInheritanceManagerMixin(InheritanceManagerMixin):
    _queryset_class = FastInheritanceQuerySet


class FastInheritanceManager(FastInheritanceManagerMixin, InheritanceManager):
    @classmethod
    def _find_subclass(cls, obj):
        return getattr(obj, f"_{obj.changed_object_type.app_label}_{obj.changed_object_type.model}changelog")

    def all(self) -> InheritanceQuerySet:
        return super().all().select_subclasses()

    def filter(self, *args: Any, **kwargs: Any) -> InheritanceQuerySet:
        return super().filter(*args, **kwargs).select_subclasses()

    def restrict(self, *args: Any, **kwargs: Any) -> InheritanceQuerySet:
        return super().restrict(*args, **kwargs).select_subclasses()

    def exclude(self, *args: Any, **kwargs: Any) -> InheritanceQuerySet:
        return super().exclude(*args, **kwargs).select_subclasses()

    def get(self, *args: Any, **kwargs: Any) -> Any:
        return self._find_subclass(super().get(*args, **kwargs))

    def first(self, *args: Any, **kwargs: Any) -> Any:
        return self._find_subclass(super().first(*args, **kwargs))

    def last(self, *args: Any, **kwargs: Any) -> Any:
        return self._find_subclass(super().last(*args, **kwargs))

    def values(self, *args: Any, **kwargs: Any) -> Any:
        return self.select_subclasses().values(*args, **kwargs)

    def select_related(self, *fields: Any) -> InheritanceQuerySet:
        if "changed_object" in fields:
            fields = []
            # Cycle through all model fields
            for field in self.model._meta.get_fields():
                # Skip non-relation fields
                if not field.is_relation:
                    continue

                # If this is a relation field and it has a related model
                if issubclass(field.related_model, self.model):
                    fields.append(field.name)

        return super().select_related(*fields)
