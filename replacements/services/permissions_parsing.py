from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import BooleanField, Case, Count, F, Q, Value, When
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from ..audit import log_activity
from accounts.school_scope import scope_queryset_for_school
from ..models import ClassSchedule, Lesson, Replacement, SpecialReplacement, Teacher
from ..scheduling import (
    FIRST_SHIFT_GRADES_SECONDARY,
    SECOND_SHIFT_GRADES,
    day_short_from_date,
    extract_grade,
    infer_shift_by_grade,
    overlaps,
)
from ..utils import get_subject_id


logger = logging.getLogger(__name__)


def _use_gsheets_backend() -> bool:
    return False


def _is_guest_user(user) -> bool:
    return bool(getattr(user, "is_guest", False))


def _can_calendar_read(user) -> bool:
    return bool(
        user.is_superuser
        or _is_guest_user(user)
        or getattr(user, "is_teacher", False)
        or getattr(user, "can_calendar", False)
        or getattr(user, "can_calls", False)
    )


def _deny_guest_write_json(request):
    if _is_guest_user(request.user):
        return JsonResponse({"error": "Гостевой доступ: только просмотр"}, status=403)
    return None


def _is_vacancy_teacher_name(full_name: str | None) -> bool:
    n = (full_name or "").strip().lower()
    return ("вакан" in n) or ("vakans" in n)


def _name_matches_term_ci(full_name: str | None, term: str | None) -> bool:
    t = (term or "").strip()
    if not t:
        return True
    return t.casefold() in (full_name or "").casefold()


def as_bool(v) -> bool:
    s = str(v or "").strip().lower()
    return s in {"1", "true", "t", "yes", "y"}


def as_int(v, default=None):
    if v is None:
        return default
    s = str(v).strip()
    if not s:
        return default
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return default


def _active_lessons():
    return scope_queryset_for_school(Lesson.objects.filter(is_active=True))


def _teacher_replacements():
    return scope_queryset_for_school(Replacement.objects.exclude(replacement_teacher_id=F("original_teacher_id")))


def _effective_shift_for_class(class_group: str, stored_shift: int | None = None) -> int | None:
    grade = extract_grade(class_group)
    sh = infer_shift_by_grade(grade)
    return sh if sh in (1, 2) else stored_shift


def _effective_times_for_lesson(class_group: str, lesson_number: int, shift: int | None, fallback_start, fallback_end):
    if not shift or not class_group or not lesson_number:
        return fallback_start, fallback_end

    grade = extract_grade(class_group)
    if grade is None:
        return fallback_start, fallback_end

    rows = scope_queryset_for_school(ClassSchedule.objects.filter(lesson_number=lesson_number, shift=int(shift)))
    cls_norm = (class_group or "").strip().lower()
    for row in rows:
        if (row.class_group or "").strip().lower() == cls_norm:
            return (row.start_time or fallback_start, row.end_time or fallback_end)
    for row in rows:
        if extract_grade(row.class_group) == grade:
            return (row.start_time or fallback_start, row.end_time or fallback_end)
    return fallback_start, fallback_end


__all__ = [
    "json",
    "logger",
    "datetime",
    "timedelta",
    "login_required",
    "require_GET",
    "transaction",
    "HttpResponse",
    "JsonResponse",
    "get_object_or_404",
    "Q",
    "Case",
    "When",
    "Value",
    "BooleanField",
    "Count",
    "Teacher",
    "Lesson",
    "Replacement",
    "SpecialReplacement",
    "ClassSchedule",
    "log_activity",
    "get_subject_id",
    "day_short_from_date",
    "extract_grade",
    "infer_shift_by_grade",
    "overlaps",
    "SECOND_SHIFT_GRADES",
    "FIRST_SHIFT_GRADES_SECONDARY",
    "_use_gsheets_backend",
    "_is_guest_user",
    "_can_calendar_read",
    "_deny_guest_write_json",
    "_is_vacancy_teacher_name",
    "_name_matches_term_ci",
    "as_bool",
    "as_int",
    "_active_lessons",
    "_teacher_replacements",
    "_effective_shift_for_class",
    "_effective_times_for_lesson",
]
