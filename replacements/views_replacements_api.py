from __future__ import annotations

import json
from datetime import datetime
from json import JSONDecodeError

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .api_errors import api_json_errors
from .audit import log_activity
from accounts.school_scope import scope_queryset_for_school
from .models import Lesson, SpecialReplacement, Teacher
from .services.permissions_parsing import (
    _active_lessons,
    _can_calendar_read,
    _deny_guest_write_json,
    _teacher_replacements,
    _use_gsheets_backend,
    as_bool,
    as_int,
)
from .services.replacements_api_service import (
    get_saved_replacements_service,
    get_suggestions_service,
    save_replacements_service,
)
from . import views as legacy_views


teacher_search = legacy_views.teacher_search
teacher_search_all = legacy_views.teacher_search_all


def _gs_store():
    raise RuntimeError("Google Sheets backend is not configured in this build")


def _gs_is_teacher_replacement(row: dict) -> bool:
    return as_int(row.get("replacement_teacher_id")) != as_int(row.get("original_teacher_id"))


@login_required
@require_GET
def teacher_details(request, teacher_id):
    if not _can_calendar_read(request.user):
        return HttpResponse("Forbidden", status=403)

    try:
        teacher = scope_queryset_for_school(Teacher.objects).get(id=teacher_id)
    except Teacher.DoesNotExist:
        return JsonResponse({"error": "Teacher not found"}, status=404)
    return JsonResponse({"name": teacher.full_name})


@login_required
@require_GET
@api_json_errors
def check_replacements_for_date(request):
    if not (request.user.is_superuser or getattr(request.user, "is_guest", False) or getattr(request.user, "can_calendar", False)):
        return HttpResponse("Forbidden", status=403)

    date_raw = (request.GET.get("date") or "").strip()
    if not date_raw:
        return JsonResponse({"error": "Дата не указана"}, status=400)
    try:
        parsed_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "Некорректная дата, ожидается YYYY-MM-DD"}, status=400)
    date_str = parsed_date.strftime("%Y-%m-%d")

    if _use_gsheets_backend():
        exists_regular = any(
            str(r.get("date") or "") == date_str and _gs_is_teacher_replacement(r)
            for r in _gs_store().get_table_dicts("replacements_replacement")
        )
        exists_special = any(
            str(r.get("date") or "") == date_str
            for r in _gs_store().get_table_dicts("replacements_special_replacement")
        )
        return JsonResponse({"exists": bool(exists_regular or exists_special)})

    exists = _teacher_replacements().filter(date=date_str).exists() or scope_queryset_for_school(SpecialReplacement.objects).filter(date=date_str).exists()
    return JsonResponse({"exists": exists})


@login_required
@require_POST
@api_json_errors
def delete_replacements_for_date(request):
    guest_forbidden = _deny_guest_write_json(request)
    if guest_forbidden:
        return guest_forbidden

    try:
        payload = json.loads((request.body or b"{}").decode("utf-8"))
    except (JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Некорректный JSON"}, status=400)

    date_raw = str(payload.get("date") or "").strip()
    if not date_raw:
        return JsonResponse({"error": "Не указана дата"}, status=400)
    try:
        parsed_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "Некорректная дата, ожидается YYYY-MM-DD"}, status=400)
    date_str = parsed_date.strftime("%Y-%m-%d")

    if _use_gsheets_backend():
        store = _gs_store()
        replacements_rows = store.get_table_dicts("replacements_replacement")
        special_rows = store.get_table_dicts("replacements_special_replacement")

        before_repl = len(replacements_rows)
        before_special = len(special_rows)

        kept_repl = [
            r for r in replacements_rows
            if not (str(r.get("date") or "") == date_str and _gs_is_teacher_replacement(r))
        ]
        kept_special = [r for r in special_rows if str(r.get("date") or "") != date_str]

        store.replace_table_dicts("replacements_replacement", kept_repl)
        store.replace_table_dicts("replacements_special_replacement", kept_special)

        deleted_count = (before_repl - len(kept_repl)) + (before_special - len(kept_special))
        return JsonResponse({"status": "success", "deleted_count": deleted_count})

    deleted, _ = _teacher_replacements().filter(date=date_str).delete()
    deleted_special, _ = scope_queryset_for_school(SpecialReplacement.objects).filter(date=date_str).delete()
    return JsonResponse({"status": "success", "deleted_count": deleted + deleted_special})


@login_required
@require_POST
@api_json_errors
def update_lesson_teacher(request, lesson_id):
    guest_forbidden = _deny_guest_write_json(request)
    if guest_forbidden:
        return guest_forbidden

    if not (request.user.is_superuser or getattr(request.user, "can_upload", False)):
        return HttpResponse("Forbidden", status=403)

    try:
        data = json.loads((request.body or b"{}").decode("utf-8"))
    except (JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Некорректный JSON"}, status=400)

    teacher_id_raw = data.get("teacher_id")
    apply_all_subjects = bool(data.get("apply_all_subjects"))
    if teacher_id_raw in (None, ""):
        return JsonResponse({"error": "teacher_id обязателен"}, status=400)
    try:
        teacher_id = int(teacher_id_raw)
    except (TypeError, ValueError):
        return JsonResponse({"error": "teacher_id должен быть числом"}, status=400)

    if _use_gsheets_backend():
        teacher_rows = _gs_store().get_table_dicts("replacements_teacher")
        teacher = next((t for t in teacher_rows if as_int(t.get("teacher_id")) == teacher_id), None)
        if not teacher:
            return JsonResponse({"error": "Учитель не найден"}, status=404)
        lessons_rows = _gs_store().get_table_dicts("replacements_lesson")
        lesson = next((l for l in lessons_rows if as_int(l.get("lesson_id")) == int(lesson_id)), None)
        if not lesson:
            return JsonResponse({"error": "Урок не найден"}, status=404)

        if apply_all_subjects:
            target_indices = [
                i for i, l in enumerate(lessons_rows)
                if as_bool(l.get("is_active"))
                and str(l.get("class_group") or "") == str(lesson.get("class_group") or "")
                and as_int(l.get("subject_id_subject")) == as_int(lesson.get("subject_id_subject"))
                and as_int(l.get("teacher_id")) == as_int(lesson.get("teacher_id"))
            ]
            mode = "class_same_subject_same_teacher"
        else:
            target_indices = [i for i, l in enumerate(lessons_rows) if as_int(l.get("lesson_id")) == as_int(lesson.get("lesson_id"))]
            mode = "single_lesson"

        affected_count = len(target_indices)
        old_teacher_ids = sorted(
            {as_int(lessons_rows[i].get("teacher_id")) for i in target_indices if as_int(lessons_rows[i].get("teacher_id")) is not None}
        )
        updated_count = 0
        for i in target_indices:
            if as_int(lessons_rows[i].get("teacher_id")) != teacher_id:
                lessons_rows[i]["teacher_id"] = teacher_id
                updated_count += 1

        _gs_store().replace_table_dicts("replacements_lesson", lessons_rows)
        log_activity(
            request,
            "lesson_teacher_update",
            {
                "lesson_id": lesson_id,
                "from_teacher_ids": old_teacher_ids,
                "to_teacher_id": teacher_id,
                "class_group": str(lesson.get("class_group") or ""),
                "subject_id": as_int(lesson.get("subject_id_subject")),
                "mode": mode,
                "updated_count": updated_count,
                "affected_count": affected_count,
                "backend": "gsheets",
            },
        )
        return JsonResponse(
            {
                "status": "success",
                "teacher_name": str(teacher.get("full_name") or ""),
                "mode": mode,
                "updated_count": updated_count,
                "affected_count": affected_count,
            }
        )

    lesson = scope_queryset_for_school(Lesson.objects).filter(id=lesson_id).first()
    if lesson is None:
        return JsonResponse({"error": "Урок не найден"}, status=404)
    teacher = scope_queryset_for_school(Teacher.objects).filter(id=teacher_id).first()
    if teacher is None:
        return JsonResponse({"error": "Учитель не найден"}, status=404)

    with transaction.atomic():
        if apply_all_subjects:
            target_qs = _active_lessons().filter(
                class_group=lesson.class_group,
                subject_id=lesson.subject_id,
                teacher_id=lesson.teacher_id,
            )
            mode = "class_same_subject_same_teacher"
        else:
            target_qs = scope_queryset_for_school(Lesson.objects).filter(id=lesson.id)
            mode = "single_lesson"

        affected_count = target_qs.count()
        old_teacher_ids = sorted(set(target_qs.values_list("teacher_id", flat=True)))
        updated_count = target_qs.exclude(teacher_id=teacher.id).update(teacher=teacher)

    log_activity(
        request,
        "lesson_teacher_update",
        {
            "lesson_id": lesson_id,
            "from_teacher_ids": old_teacher_ids,
            "to_teacher_id": teacher.id,
            "class_group": lesson.class_group,
            "subject_id": lesson.subject_id,
            "mode": mode,
            "updated_count": updated_count,
            "affected_count": affected_count,
        },
    )
    return JsonResponse(
        {
            "status": "success",
            "teacher_name": teacher.full_name,
            "mode": mode,
            "updated_count": updated_count,
            "affected_count": affected_count,
        }
    )


@login_required
@require_POST
@api_json_errors
def reassign_teacher_lessons(request):
    guest_forbidden = _deny_guest_write_json(request)
    if guest_forbidden:
        return guest_forbidden

    if not (request.user.is_superuser or getattr(request.user, "can_upload", False)):
        return HttpResponse("Forbidden", status=403)

    try:
        data = json.loads((request.body or b"{}").decode("utf-8"))
    except (JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Некорректный JSON"}, status=400)

    from_teacher_id_raw = data.get("from_teacher_id")
    to_teacher_id_raw = data.get("to_teacher_id")
    active_only = bool(data.get("active_only", True))

    if from_teacher_id_raw in (None, "") or to_teacher_id_raw in (None, ""):
        return JsonResponse({"error": "from_teacher_id и to_teacher_id обязательны"}, status=400)

    try:
        from_teacher_id = int(from_teacher_id_raw)
        to_teacher_id = int(to_teacher_id_raw)
    except (TypeError, ValueError):
        return JsonResponse({"error": "ID учителей должны быть числами"}, status=400)

    if from_teacher_id == to_teacher_id:
        return JsonResponse({"error": "Выберите двух разных учителей"}, status=400)

    if _use_gsheets_backend():
        teacher_rows = _gs_store().get_table_dicts("replacements_teacher")
        from_teacher = next((t for t in teacher_rows if as_int(t.get("teacher_id")) == from_teacher_id), None)
        to_teacher = next((t for t in teacher_rows if as_int(t.get("teacher_id")) == to_teacher_id), None)
        if not from_teacher or not to_teacher:
            return JsonResponse({"error": "Учитель не найден"}, status=404)

        lessons_rows = _gs_store().get_table_dicts("replacements_lesson")
        target_indices = [
            i for i, l in enumerate(lessons_rows)
            if as_int(l.get("teacher_id")) == from_teacher_id and (not active_only or as_bool(l.get("is_active")))
        ]
        affected_count = len(target_indices)
        updated_count = 0
        for i in target_indices:
            lessons_rows[i]["teacher_id"] = to_teacher_id
            updated_count += 1
        _gs_store().replace_table_dicts("replacements_lesson", lessons_rows)

        log_activity(
            request,
            "lesson_teacher_reassign_bulk",
            {
                "from_teacher_id": from_teacher_id,
                "to_teacher_id": to_teacher_id,
                "from_teacher_name": str(from_teacher.get("full_name") or ""),
                "to_teacher_name": str(to_teacher.get("full_name") or ""),
                "active_only": active_only,
                "affected_count": affected_count,
                "updated_count": updated_count,
                "backend": "gsheets",
            },
        )
        return JsonResponse(
            {
                "status": "success",
                "from_teacher_name": str(from_teacher.get("full_name") or ""),
                "to_teacher_name": str(to_teacher.get("full_name") or ""),
                "active_only": active_only,
                "affected_count": affected_count,
                "updated_count": updated_count,
            }
        )

    from_teacher = scope_queryset_for_school(Teacher.objects).filter(id=from_teacher_id).first()
    to_teacher = scope_queryset_for_school(Teacher.objects).filter(id=to_teacher_id).first()
    if not from_teacher or not to_teacher:
        return JsonResponse({"error": "Учитель не найден"}, status=404)

    with transaction.atomic():
        lessons_qs = scope_queryset_for_school(Lesson.objects).filter(teacher_id=from_teacher_id)
        if active_only:
            lessons_qs = lessons_qs.filter(is_active=True)
        affected_count = lessons_qs.count()
        updated_count = lessons_qs.update(teacher_id=to_teacher_id)

    log_activity(
        request,
        "lesson_teacher_reassign_bulk",
        {
            "from_teacher_id": from_teacher_id,
            "to_teacher_id": to_teacher_id,
            "from_teacher_name": from_teacher.full_name,
            "to_teacher_name": to_teacher.full_name,
            "active_only": active_only,
            "affected_count": affected_count,
            "updated_count": updated_count,
        },
    )
    return JsonResponse(
        {
            "status": "success",
            "from_teacher_name": from_teacher.full_name,
            "to_teacher_name": to_teacher.full_name,
            "active_only": active_only,
            "affected_count": affected_count,
            "updated_count": updated_count,
        }
    )


@login_required
@require_POST
@api_json_errors
def save_replacements(request):
    return save_replacements_service(request)


@login_required
@require_GET
@api_json_errors
def get_suggestions(request):
    return get_suggestions_service(request)


@login_required
@require_GET
@api_json_errors
def get_saved_replacements(request):
    return get_saved_replacements_service(request)


__all__ = [
    "check_replacements_for_date",
    "delete_replacements_for_date",
    "get_saved_replacements",
    "get_suggestions",
    "reassign_teacher_lessons",
    "save_replacements",
    "teacher_details",
    "teacher_search",
    "teacher_search_all",
    "update_lesson_teacher",
]
