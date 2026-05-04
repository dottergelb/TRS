from django.conf import settings
from django.db import models
import uuid
from accounts.school_scope import SchoolScopedManager


class Teacher(models.Model):
    id = models.AutoField(primary_key=True, db_column="teacher_id")
    school = models.ForeignKey("accounts.School", on_delete=models.CASCADE, related_name="teachers", null=True, blank=True)
    full_name = models.CharField(max_length=255)
    specialization = models.CharField("Специализации", max_length=255, blank=True, null=True)
    hours_per_week = models.PositiveIntegerField(default=0)
    objects = SchoolScopedManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "replacements_teacher"
        constraints = [
            models.UniqueConstraint(fields=["school", "full_name"], name="uniq_teacher_school_full_name"),
        ]


class Subject(models.Model):
    id_subject = models.AutoField(primary_key=True)
    school = models.ForeignKey("accounts.School", on_delete=models.CASCADE, related_name="subjects", null=True, blank=True)
    name = models.CharField(max_length=100)
    objects = SchoolScopedManager()
    all_objects = models.Manager()

    def __str__(self):
        return self.name

    class Meta:
        db_table = "replacements_subject"
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="uniq_subject_school_name"),
        ]


class Lesson(models.Model):
    id = models.AutoField(primary_key=True, db_column="lesson_id")
    school = models.ForeignKey("accounts.School", on_delete=models.CASCADE, related_name="lessons", null=True, blank=True)
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        db_column="teacher_id",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        to_field="id_subject",
        db_column="subject_id_subject",
        verbose_name="Предмет",
    )
    lesson_number = models.IntegerField("Номер урока", null=False)
    class_group = models.CharField("Класс", max_length=50, default="-", blank=False)
    classroom = models.CharField("Кабинет", max_length=50, default="---", blank=False)
    start_time = models.TimeField("Начало")
    end_time = models.TimeField("Конец")
    shift = models.IntegerField("Смена")
    day_of_week = models.CharField("День недели", max_length=3)
    is_active = models.BooleanField("Актуальное расписание", default=True, db_index=True)
    objects = SchoolScopedManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["day_of_week", "lesson_number"]


class Replacement(models.Model):
    school = models.ForeignKey("accounts.School", on_delete=models.CASCADE, related_name="replacements", null=True, blank=True)
    original_teacher = models.ForeignKey(
        "Teacher",
        on_delete=models.CASCADE,
        related_name="original_replacements",
        db_column="original_teacher_id",
    )
    replacement_teacher = models.ForeignKey(
        "Teacher",
        on_delete=models.CASCADE,
        related_name="replacement_replacements",
        db_column="replacement_teacher_id",
    )
    lesson = models.ForeignKey("Lesson", on_delete=models.CASCADE)
    date = models.DateField()
    confirmed = models.BooleanField(default=False)
    production_necessity = models.BooleanField(default=False)
    ignore_in_reports = models.BooleanField(default=False, verbose_name="Не учитывать в замещениях")
    replacement_classroom = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Кабинет замещения",
    )
    objects = SchoolScopedManager()
    all_objects = models.Manager()

    class Meta:
        unique_together = ("lesson", "date")
        db_table = "replacements_replacement"


class SpecialReplacement(models.Model):
    """Отдельное замещение, не привязанное к конкретному уроку в расписании."""

    school = models.ForeignKey("accounts.School", on_delete=models.CASCADE, related_name="special_replacements", null=True, blank=True)
    date = models.DateField()
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="special_replacements",
    )
    class_group = models.CharField("Класс", max_length=50)
    subject_name = models.CharField("Предмет", max_length=100)
    lesson_number = models.IntegerField("Номер урока", null=True, blank=True)
    start_time = models.TimeField("Начало", null=True, blank=True)
    end_time = models.TimeField("Конец", null=True, blank=True)
    classroom = models.CharField("Кабинет", max_length=50, null=True, blank=True)
    replacement_teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="special_replacements",
    )
    original_teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="special_original_replacements",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    objects = SchoolScopedManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "replacements_special_replacement"


class ClassSchedule(models.Model):
    school = models.ForeignKey("accounts.School", on_delete=models.CASCADE, related_name="class_schedules", null=True, blank=True)
    class_group = models.CharField("Класс", max_length=10)
    lesson_number = models.IntegerField("Номер урока")
    start_time = models.TimeField("Начало", null=True, blank=True)
    end_time = models.TimeField("Конец", null=True, blank=True)
    shift = models.IntegerField("Смена", choices=[(1, "1 смена"), (2, "2 смена")], default=1)
    objects = SchoolScopedManager()
    all_objects = models.Manager()

    class Meta:
        unique_together = ("class_group", "lesson_number", "shift")
        db_table = "replacements_class_schedule"


class ActivityLog(models.Model):
    school = models.ForeignKey("accounts.School", on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=64, db_index=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    path = models.CharField(max_length=255, blank=True, default="")
    method = models.CharField(max_length=16, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    objects = SchoolScopedManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "replacements_activity_log"
        ordering = ["-created_at"]


class DocxImportTask(models.Model):
    STATUS_QUEUED = "queued"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey("accounts.School", on_delete=models.CASCADE, related_name="docx_import_tasks", null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    celery_task_id = models.CharField(max_length=255, blank=True, default="")
    file_name = models.CharField(max_length=255, blank=True, default="")
    date = models.DateField()
    replace_all = models.BooleanField(default=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True)
    parsed_rows = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    skipped_same_teacher = models.PositiveIntegerField(default=0)
    unresolved_count = models.PositiveIntegerField(default=0)
    unresolved_preview = models.JSONField(default=list, blank=True)
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = SchoolScopedManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "replacements_docx_import_task"
        ordering = ["-created_at"]
