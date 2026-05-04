from django.contrib.auth.models import AbstractUser
from django.db import models


class School(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Ожидает рассмотрения"),
        (STATUS_APPROVED, "Одобрена"),
        (STATUS_REJECTED, "Отклонена"),
    )

    name = models.CharField(max_length=255, unique=True)
    city = models.CharField(max_length=120, blank=True, default="")
    street = models.CharField(max_length=180, blank=True, default="")
    house = models.CharField(max_length=32, blank=True, default="")
    contact_phone = models.CharField(max_length=64, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    contact_person = models.CharField(max_length=255, blank=True, default="")
    comment = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_school"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class CustomUser(AbstractUser):
    full_name = models.CharField(max_length=255)
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    is_system_account = models.BooleanField(
        default=False,
        verbose_name="Системный аккаунт (служебный)",
        db_index=True,
    )
    is_support_system = models.BooleanField(
        default=False,
        verbose_name="Система поддержки (служебный)",
        db_index=True,
    )
    is_project_admin = models.BooleanField(
        default=False,
        verbose_name="Роль «Администратор проекта»",
        db_index=True,
    )
    is_admin = models.BooleanField(
        default=False,
        verbose_name="Роль «Администратор школы»",
    )
    is_guest = models.BooleanField(
        default=False,
        verbose_name="Статус «Гость» (только просмотр)",
    )
    is_teacher = models.BooleanField(
        default=False,
        verbose_name="Роль «Учитель» (только свои данные)",
    )

    can_calendar = models.BooleanField(default=False, verbose_name="Доступ к календарю")
    can_teachers = models.BooleanField(default=False, verbose_name="Доступ к разделу «Учителя»")
    can_editor = models.BooleanField(default=False, verbose_name="Доступ к разделу «Редактор»")
    can_upload = models.BooleanField(default=False, verbose_name="Доступ к разделу «Загрузка»")
    can_logs = models.BooleanField(default=False, verbose_name="Доступ к разделу «Логи»")
    can_calls = models.BooleanField(default=False, verbose_name="Доступ к разделу «Звонки»")
    can_users = models.BooleanField(default=False, verbose_name="Доступ к управлению пользователями")

    def save(self, *args, **kwargs):
        access_fields = (
            "can_calendar",
            "can_teachers",
            "can_editor",
            "can_upload",
            "can_logs",
            "can_calls",
            "can_users",
        )
        if self.is_admin:
            self.is_guest = False
            self.is_teacher = False
            for field in access_fields:
                setattr(self, field, True)
        elif self.is_teacher:
            self.is_admin = False
            self.is_guest = False
            for field in access_fields:
                setattr(self, field, False)
        elif self.is_guest:
            self.is_admin = False
            self.is_teacher = False
            for field in access_fields:
                setattr(self, field, False)
        super().save(*args, **kwargs)

    def has_calendar_access(self) -> bool:
        return self.is_superuser or self.is_project_admin or self.is_admin or self.can_calendar or self.is_teacher

    def has_teachers_access(self) -> bool:
        return self.is_superuser or self.is_project_admin or self.is_admin or self.can_teachers or self.can_editor

    def has_editor_access(self) -> bool:
        return self.is_superuser or self.is_project_admin or self.is_admin or self.can_editor

    def has_upload_access(self) -> bool:
        return self.is_superuser or self.is_project_admin or self.is_admin or self.can_upload

    def has_logs_access(self) -> bool:
        return self.is_superuser or self.is_project_admin or self.is_admin or self.is_staff or self.can_logs or self.is_teacher

    def has_calls_access(self) -> bool:
        return self.is_superuser or self.is_project_admin or self.is_admin or self.can_calls

    def has_users_access(self) -> bool:
        return self.is_superuser or self.is_project_admin or self.is_admin or self.can_users

    def has_write_access(self) -> bool:
        return not self.is_guest and not self.is_teacher
