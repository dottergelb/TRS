from __future__ import annotations

from .views import (
    backend_health_api,
    calendar_view,
    my_replacement_dates_for_month_api,
    my_replacements_for_day_api,
    replacement_dates_for_month,
    replacement_statistics_api,
    statistics_view,
    teacher_conflicts_api,
    teacher_hours,
    vacancy_teachers_for_date,
)

__all__ = [
    "backend_health_api",
    "calendar_view",
    "my_replacement_dates_for_month_api",
    "my_replacements_for_day_api",
    "replacement_dates_for_month",
    "replacement_statistics_api",
    "statistics_view",
    "teacher_conflicts_api",
    "teacher_hours",
    "vacancy_teachers_for_date",
]
