from django.contrib import admin
from .models import Teacher, Lesson, ActivityLog


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("full_name",)
    search_fields = ("full_name",)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("teacher", "day_of_week", "lesson_number", "subject", "class_group", "shift", "is_active")
    list_filter = ("day_of_week", "shift", "is_active")
    search_fields = ("teacher__full_name", "class_group", "subject__name")


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "ip_address", "path", "method")
    list_filter = ("action", "created_at")
    search_fields = ("user__username", "user__full_name", "action", "path", "ip_address")
    readonly_fields = ("created_at",)
