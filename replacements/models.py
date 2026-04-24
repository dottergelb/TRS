from django.db import models
from django.conf import settings


class Teacher(models.Model):
    id = models.AutoField(primary_key=True, db_column='teacher_id')
    full_name = models.CharField(max_length=255, unique=True)
    specialization = models.CharField("Специализации", max_length=255, blank=True, null=True)
    hours_per_week = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'replacements_teacher'


class Subject(models.Model):
    id_subject = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'replacements_subject'


class Lesson(models.Model):
    id = models.AutoField(primary_key=True, db_column='lesson_id')
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        db_column='teacher_id',
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        to_field='id_subject',
        db_column='subject_id_subject',
        verbose_name="Предмет"
    )
    lesson_number = models.IntegerField("Номер урока", null=False)
    class_group = models.CharField("Класс", max_length=50, default='-', blank=False)
    classroom = models.CharField("Кабинет", max_length=50, default='---', blank=False)
    start_time = models.TimeField("Начало")
    end_time = models.TimeField("Конец")
    shift = models.IntegerField("Смена")
    day_of_week = models.CharField("День недели", max_length=3)
    is_active = models.BooleanField("Актуальное расписание", default=True, db_index=True)

    class Meta:
        ordering = ['day_of_week', 'lesson_number']


class Replacement(models.Model):
    original_teacher = models.ForeignKey(
        'Teacher',
        on_delete=models.CASCADE,
        related_name='original_replacements',
        db_column='original_teacher_id'
    )
    replacement_teacher = models.ForeignKey(
        'Teacher',
        on_delete=models.CASCADE,
        related_name='replacement_replacements',
        db_column='replacement_teacher_id'
    )
    lesson = models.ForeignKey('Lesson', on_delete=models.CASCADE)
    date = models.DateField()
    confirmed = models.BooleanField(default=False)
                                                                                            
    production_necessity = models.BooleanField(default=False)
                                                         
    ignore_in_reports = models.BooleanField(default=False, verbose_name="Не учитывать в замещениях")

                                                                                                   
                                                                                       
    replacement_classroom = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Кабинет замещения"
    )

    class Meta:
        unique_together = ('lesson', 'date')
        db_table = 'replacements_replacement'


class SpecialReplacement(models.Model):
    """Отдельное замещение, не привязанное к конкретному уроку в расписании."""
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

    class Meta:
        db_table = "replacements_special_replacement"


class ClassSchedule(models.Model):
    class_group = models.CharField("Класс", max_length=10)
    lesson_number = models.IntegerField("Номер урока")
    start_time = models.TimeField("Начало", null=True, blank=True)
    end_time = models.TimeField("Конец", null=True, blank=True)
    shift = models.IntegerField("Смена", choices=[(1, "1 смена"), (2, "2 смена")], default=1)

    class Meta:
        unique_together = ("class_group", "lesson_number", "shift")
        db_table = 'replacements_class_schedule'


class ActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=64, db_index=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    path = models.CharField(max_length=255, blank=True, default="")
    method = models.CharField(max_length=16, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "replacements_activity_log"
        ordering = ["-created_at"]
