from __future__ import annotations

from typing import Any, TypeVar

from django.db import models
from model_utils.managers import (
    InheritanceManager,
    InheritanceManagerMixin,
    InheritanceQuerySet,
    InheritanceQuerySetMixin,
)

ModelT = TypeVar("ModelT", bound=models.Model, covariant=True)


class FastInheritanceQuerySetMixin(InheritanceQuerySetMixin, models.QuerySet):
    def select_subclasses(self, *subclasses: str | type[models.Model]) -> InheritanceQuerySet:
        if not subclasses:
            selected_subclasses = {
                x["target_model_name"]
                for x in self.values("target_model_name").distinct("target_model_name").order_by("target_model_name")
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


class FastInheritanceQuerySet(FastInheritanceQuerySetMixin, InheritanceQuerySet): ...


class FastInheritanceManagerMixin(InheritanceManagerMixin):
    _queryset_class = FastInheritanceQuerySet


class FastInheritanceManager(FastInheritanceManagerMixin, InheritanceManager):
    @classmethod
    def _find_subclass(cls, obj):
        return getattr(obj, obj.target_model_name)

    def all(self) -> InheritanceQuerySet:
        return super().all().select_subclasses()

    def filter(self, *args: Any, **kwargs: Any) -> InheritanceQuerySet:
        return super().filter(*args, **kwargs).select_subclasses()

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
        if "fktarget" in fields:
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
