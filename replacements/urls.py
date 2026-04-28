from django.urls import path
from django.views.generic import TemplateView

from . import views
from . import views_cabinets
from . import views_calendar
from . import views_replacements_api
from . import views_reports
from . import views_schedule


app_name = "replacements"

urlpatterns = [
    path("", TemplateView.as_view(template_name="main_menu.html"), name="main-menu"),
    path("stats/", views_calendar.statistics_view, name="statistics"),
    path("calendar/", views_calendar.calendar_view, name="calendar"),
    path("logs/", views.activity_logs_view, name="activity_logs"),
    path("api/lessons/<int:lesson_id>/teacher/", views_replacements_api.update_lesson_teacher, name="lesson-teacher"),
    path("api/lessons/<int:teacher_id>/<str:day>/", views_schedule.get_lessons, name="get_lessons"),
    path("lessons/<int:teacher_id>/<str:day>/", views_schedule.teacher_lessons_view, name="teacher_lessons"),
    path("export/", views_reports.export_to_docx, name="export"),
    path("api/save/", views_replacements_api.save_replacements, name="save"),
    path("api/suggestions/", views_replacements_api.get_suggestions, name="suggestions"),
    path("api/teachers/", views_replacements_api.teacher_search, name="teachers"),
    path("api/teachers-all/", views_replacements_api.teacher_search_all, name="teachers_all"),
    path("api/my-replacements/", views_calendar.my_replacements_for_day_api, name="my_replacements_for_day"),
    path("api/my-replacement-dates/", views_calendar.my_replacement_dates_for_month_api, name="my_replacement_dates_for_month"),
    path("api/vacancy-teachers/", views_calendar.vacancy_teachers_for_date, name="vacancy_teachers"),
    path("api/reassign-teacher-lessons/", views_replacements_api.reassign_teacher_lessons, name="reassign_teacher_lessons"),
    path("api/teacher-conflicts/", views_calendar.teacher_conflicts_api, name="teacher_conflicts"),
    path("api/replacements/", views_replacements_api.get_saved_replacements, name="get_replacements"),
    path("specializations/", views.teachers_overview_view, name="teachers_overview"),
    path("specializations/editor/", views.specializations_view, name="specializations_editor"),
    path("api/update-specialization/", views.update_specialization, name="update_specialization"),
    path("api/teachers/add/", views.add_teacher_api, name="add_teacher"),
    path("api/teachers/<int:teacher_id>/delete/", views.delete_teacher_api, name="delete_teacher"),
    path("api/lessons/<int:lesson_id>/", views_schedule.get_lessons_by_id, name="lesson-by-id"),
    path("api/teachers/<int:teacher_id>/", views_replacements_api.teacher_details, name="teacher-details"),
    path("api/special-options/", views.special_replacement_options, name="special_options"),
    path("api/special-lessons/", views.special_replacement_lessons, name="special_lessons"),
    path("api/special-time/", views.special_replacement_time, name="special_time"),
    path("api/check-replacements/", views_replacements_api.check_replacements_for_date, name="check_replacements"),
    path("api/delete-replacements/", views_replacements_api.delete_replacements_for_date, name="delete_replacements"),
    path("api/replacement-dates/", views_calendar.replacement_dates_for_month, name="replacement_dates"),
    path("api/teacher-hours/<int:teacher_id>/", views_calendar.teacher_hours, name="teacher_hours"),
    path("api/replacement-report/", views_reports.replacement_summary_report, name="replacement_report"),
    path("api/replacement-report-extra/", views_reports.replacement_daily_summary_docx, name="replacement_report_extra"),
    path("api/replacement-report-extra-teacher/", views_reports.replacement_teacher_summary_docx, name="replacement_report_extra_teacher"),
    path("api/import-docx/", views_schedule.import_replacements_docx, name="import_replacements_docx"),
    path("api/import-docx/status/<uuid:job_id>/", views.import_replacements_docx_status, name="import_replacements_docx_status"),
    path("api/stats/", views_calendar.replacement_statistics_api, name="statistics_api"),
    path("api/backend-health/", views_calendar.backend_health_api, name="backend_health"),
    path("schedule/", views_schedule.class_schedule_view, name="class_schedule"),
    path("upload/", views_schedule.upload, name="upload"),
    path("upload/schedule/", views_schedule.upload_schedule_view, name="upload_schedule"),
    path("api/upload-schedule/", views_schedule.upload_schedule_api, name="upload_schedule_api"),
    path("cabinets/", views_cabinets.cabinet_replacement_view, name="cabinets"),
    path("api/cabinet-lessons/", views_cabinets.cabinet_lessons, name="cabinet_lessons"),
    path("api/save-cabinet-replacements/", views_cabinets.save_cabinet_replacements, name="save_cabinet_replacements"),
    path("api/export-cabinet-docx/", views_cabinets.export_cabinet_docx, name="export_cabinet_docx"),
    path("api/available-rooms/", views_cabinets.available_rooms, name="available_rooms"),
    path("api/room-conflicts/", views_cabinets.room_conflicts_api, name="room_conflicts"),
]
