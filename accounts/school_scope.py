from __future__ import annotations

from django.db import models

from replacements.request_context import current_school_id_var


def is_project_level_user(user) -> bool:
    return bool(
        getattr(user, "is_authenticated", False)
        and (getattr(user, "is_superuser", False) or getattr(user, "is_project_admin", False))
    )


def get_current_school_id() -> int | None:
    return current_school_id_var.get()


def scope_queryset_for_school(qs, *, school_field: str = "school_id"):
    school_id = get_current_school_id()
    if school_id:
        return qs.filter(**{school_field: school_id})
    return qs


class SchoolScopedQuerySet(models.QuerySet):
    def _with_current_school(self, kwargs: dict):
        school_id = get_current_school_id()
        if (
            school_id
            and school_id > 0
            and "school" not in kwargs
            and "school_id" not in kwargs
            and hasattr(self.model, "school_id")
        ):
            kwargs["school_id"] = school_id
        return kwargs

    def for_current_school(self):
        return scope_queryset_for_school(self)

    def all_schools(self):
        return self.model.all_objects.all()

    def create(self, **kwargs):
        return super().create(**self._with_current_school(kwargs))

    def get_or_create(self, defaults=None, **kwargs):
        kwargs = self._with_current_school(kwargs)
        defaults = dict(defaults or {})
        self._with_current_school(defaults)
        return super().get_or_create(defaults=defaults, **kwargs)

    def update_or_create(self, defaults=None, **kwargs):
        kwargs = self._with_current_school(kwargs)
        defaults = dict(defaults or {})
        self._with_current_school(defaults)
        return super().update_or_create(defaults=defaults, **kwargs)


class SchoolScopedManager(models.Manager):
    def get_queryset(self):
        return SchoolScopedQuerySet(self.model, using=self._db).for_current_school()
