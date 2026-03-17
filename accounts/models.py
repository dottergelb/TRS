from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    full_name = models.CharField(max_length=255)

    # Права доступа к разделам системы (назначаются суперпользователем).
    # По умолчанию обычный пользователь не имеет доступа ни к одному разделу.
    can_calendar = models.BooleanField(default=False, verbose_name="Доступ к календарю")
    can_teachers = models.BooleanField(default=False, verbose_name="Доступ к разделу «Учителя»")
    can_editor = models.BooleanField(default=False, verbose_name="Доступ к разделу «Редактор»")
    can_upload = models.BooleanField(default=False, verbose_name="Доступ к разделу «Загрузка»")
    can_logs = models.BooleanField(default=False, verbose_name="Доступ к разделу «Логи»")
    can_calls = models.BooleanField(default=False, verbose_name="Доступ к разделу «Звонки»")
    can_users = models.BooleanField(default=False, verbose_name="Доступ к управлению пользователями")

    def has_calendar_access(self) -> bool:
        """Возвращает True, если пользователь может работать с календарём."""
        return self.is_superuser or self.can_calendar

    def has_teachers_access(self) -> bool:
        """Возвращает True, если пользователь может просматривать учителей."""
        return self.is_superuser or self.can_teachers or self.can_editor

    def has_editor_access(self) -> bool:
        """Возвращает True, если пользователь может редактировать специализации учителей."""
        return self.is_superuser or self.can_editor

    def has_upload_access(self) -> bool:
        """Возвращает True, если пользователь может загружать расписание."""
        return self.is_superuser or self.can_upload

    def has_logs_access(self) -> bool:
        """Возвращает True, если пользователь может просматривать журнал действий."""
        return self.is_superuser or self.is_staff or self.can_logs

    def has_calls_access(self) -> bool:
        """Возвращает True, если пользователь может просматривать/редактировать звонки (расписание)."""
        return self.is_superuser or self.can_calls

    def has_users_access(self) -> bool:
        """Возвращает True, если пользователь может управлять пользователями."""
        return self.is_superuser or self.can_users
