from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET

from .models import Teacher
from .views import (
    _can_calendar_read,
    check_replacements_for_date,
    delete_replacements_for_date,
    get_saved_replacements,
    get_suggestions,
    reassign_teacher_lessons,
    save_replacements,
    teacher_search,
    teacher_search_all,
)


@login_required
@require_GET
def teacher_details(request, teacher_id):
    if not _can_calendar_read(request.user):
        return HttpResponse("Forbidden", status=403)

    try:
        teacher = Teacher.objects.get(id=teacher_id)
        return JsonResponse({"name": teacher.full_name})
    except Teacher.DoesNotExist:
        return JsonResponse({"error": "Teacher not found"}, status=404)


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
]
