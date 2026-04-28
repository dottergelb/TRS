from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET

from .models import Lesson
from .services.permissions_parsing import (
    _active_lessons,
    _can_calendar_read,
    _effective_shift_for_class,
    _effective_times_for_lesson,
)
from . import views as legacy_views


class_schedule_view = legacy_views.class_schedule_view
clear_schedule = legacy_views.clear_schedule
import_replacements_docx = legacy_views.import_replacements_docx
teacher_lessons_view = legacy_views.teacher_lessons_view
upload = legacy_views.upload
upload_schedule_api = legacy_views.upload_schedule_api
upload_schedule_view = legacy_views.upload_schedule_view


@login_required
@require_GET
def get_lessons(request, teacher_id, day):
    if not _can_calendar_read(request.user):
        return HttpResponse("Forbidden", status=403)
    lessons = _active_lessons().filter(teacher_id=teacher_id, day_of_week=day)
    lesson_data = []
    for lesson in lessons:
        eff_shift = _effective_shift_for_class(lesson.class_group, lesson.shift)
        eff_start, eff_end = _effective_times_for_lesson(
            lesson.class_group,
            lesson.lesson_number,
            eff_shift,
            lesson.start_time,
            lesson.end_time,
        )
        lesson_data.append(
            {
                "id": lesson.id,
                "number": lesson.lesson_number,
                "start": eff_start.strftime("%H:%M") if eff_start else "--:--",
                "end": eff_end.strftime("%H:%M") if eff_end else "--:--",
                "subject": str(lesson.subject),
                "class": lesson.class_group,
                "shift": eff_shift,
            }
        )
    return JsonResponse({"lessons": lesson_data})


@login_required
@require_GET
def get_lessons_by_id(request, lesson_id):
    if not _can_calendar_read(request.user):
        return HttpResponse("Forbidden", status=403)
    try:
        lesson = Lesson.objects.select_related("subject", "teacher").get(id=lesson_id)
    except Lesson.DoesNotExist:
        return JsonResponse({"error": f"Урок с ID {lesson_id} не найден"}, status=404)

    eff_shift = _effective_shift_for_class(lesson.class_group, lesson.shift)
    eff_start, eff_end = _effective_times_for_lesson(
        lesson.class_group,
        lesson.lesson_number,
        eff_shift,
        lesson.start_time,
        lesson.end_time,
    )
    return JsonResponse(
        {
            "id": lesson.id,
            "subject": lesson.subject.name if lesson.subject else "Не указано",
            "teacher": lesson.teacher.full_name if lesson.teacher else "Не указан",
            "number": lesson.lesson_number,
            "class": lesson.class_group,
            "room": lesson.classroom,
            "start": eff_start.strftime("%H:%M") if eff_start else "--:--",
            "end": eff_end.strftime("%H:%M") if eff_end else "--:--",
            "shift": eff_shift,
            "day_of_week": lesson.day_of_week,
        }
    )


__all__ = [
    "class_schedule_view",
    "clear_schedule",
    "get_lessons",
    "get_lessons_by_id",
    "import_replacements_docx",
    "teacher_lessons_view",
    "upload",
    "upload_schedule_api",
    "upload_schedule_view",
]
