from __future__ import annotations

from . import views as legacy_views


backend_health_api = legacy_views.backend_health_api
calendar_view = legacy_views.calendar_view
my_replacement_dates_for_month_api = legacy_views.my_replacement_dates_for_month_api
my_replacements_for_day_api = legacy_views.my_replacements_for_day_api
replacement_dates_for_month = legacy_views.replacement_dates_for_month
replacement_statistics_api = legacy_views.replacement_statistics_api
statistics_view = legacy_views.statistics_view
teacher_conflicts_api = legacy_views.teacher_conflicts_api
teacher_hours = legacy_views.teacher_hours
vacancy_teachers_for_date = legacy_views.vacancy_teachers_for_date

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
