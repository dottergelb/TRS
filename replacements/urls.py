from django.urls import path
from django.views.generic import TemplateView
from . import views


app_name = 'replacements'

urlpatterns = [
    path('', TemplateView.as_view(template_name="main_menu.html"), name='main-menu'),
    path('stats/', views.statistics_view, name='statistics'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('logs/', views.activity_logs_view, name='activity_logs'),
    path('api/lessons/<int:lesson_id>/teacher/', views.update_lesson_teacher, name='lesson-teacher'),
    path('api/lessons/<int:teacher_id>/<str:day>/', views.get_lessons, name='get_lessons'),
    path('lessons/<int:teacher_id>/<str:day>/', views.teacher_lessons_view, name='teacher_lessons'),
    path('export/', views.export_to_docx, name='export'),
    path('api/save/', views.save_replacements, name='save'),
    path('api/suggestions/', views.get_suggestions, name='suggestions'),
    path('api/teachers/', views.teacher_search, name='teachers'),
    path('api/teachers-all/', views.teacher_search_all, name='teachers_all'),
    path('api/vacancy-teachers/', views.vacancy_teachers_for_date, name='vacancy_teachers'),
    path('api/reassign-teacher-lessons/', views.reassign_teacher_lessons, name='reassign_teacher_lessons'),
    path('api/teacher-conflicts/', views.teacher_conflicts_api, name='teacher_conflicts'),
    path('api/replacements/', views.get_saved_replacements, name='get_replacements'),
    # "Специализация" теперь разделена на две страницы:
    # 1) /specializations/            -> "Учителя" (обзор)
    # 2) /specializations/editor/     -> "Редактор" (таблица флажков)
    path('specializations/', views.teachers_overview_view, name='teachers_overview'),
    path('specializations/editor/', views.specializations_view, name='specializations_editor'),
    path('api/update-specialization/', views.update_specialization, name='update_specialization'),
    # Teacher management (used on the "Редактор" page)
    path('api/teachers/add/', views.add_teacher_api, name='add_teacher'),
    path('api/teachers/<int:teacher_id>/delete/', views.delete_teacher_api, name='delete_teacher'),
    path('api/lessons/<int:lesson_id>/', views.get_lessons_by_id, name='lesson-by-id'),
    path('api/teachers/<int:teacher_id>/', views.teacher_details, name='teacher-details'),
    path('api/special-options/', views.special_replacement_options, name='special_options'),
    path('api/special-lessons/', views.special_replacement_lessons, name='special_lessons'),
    path('api/special-time/', views.special_replacement_time, name='special_time'),
    path('api/check-replacements/', views.check_replacements_for_date, name='check_replacements'),
    path('api/delete-replacements/', views.delete_replacements_for_date, name='delete_replacements'),
    # Dates with existing replacements (for highlighting in the date picker)
    path('api/replacement-dates/', views.replacement_dates_for_month, name='replacement_dates'),
    path('api/teacher-hours/<int:teacher_id>/', views.teacher_hours, name='teacher_hours'),
    path('api/replacement-report/', views.replacement_summary_report, name='replacement_report'),
    path('api/replacement-report-extra/', views.replacement_daily_summary_docx, name='replacement_report_extra'),
    path('api/replacement-report-extra-teacher/', views.replacement_teacher_summary_docx, name='replacement_report_extra_teacher'),
    path('api/import-docx/', views.import_replacements_docx, name='import_replacements_docx'),
    path('api/stats/', views.replacement_statistics_api, name='statistics_api'),
    path('api/backend-health/', views.backend_health_api, name='backend_health'),
    path('schedule/', views.class_schedule_view, name='class_schedule'),
    path("upload/", views.upload, name="upload"),
    path("api/upload-schedule/", views.upload_schedule_api, name="upload_schedule_api"),

    # ----- Cabinet replacement routes -----
    # Страница для замены кабинетов и связанные API
    path('cabinets/', views.cabinet_replacement_view, name='cabinets'),
    path('api/cabinet-lessons/', views.cabinet_lessons, name='cabinet_lessons'),
    path('api/save-cabinet-replacements/', views.save_cabinet_replacements, name='save_cabinet_replacements'),
    path('api/export-cabinet-docx/', views.export_cabinet_docx, name='export_cabinet_docx'),

    # Кабинеты
    path('api/available-rooms/', views.available_rooms, name='available_rooms'),
    path('api/room-conflicts/', views.room_conflicts_api, name='room_conflicts'),





]
