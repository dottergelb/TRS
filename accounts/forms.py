from __future__ import annotations

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import CustomUser


class RegisterForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("username", "full_name", "password1", "password2")
        labels = {
            "username": "Логин",
            "full_name": "ФИО",
            "password1": "Пароль",
            "password2": "Подтверждение пароля",
        }


class LoginForm(AuthenticationForm):
    pass


class UserUpdateForm(forms.ModelForm):
    ROLE_NONE = "none"
    ROLE_ADMIN = "admin"
    ROLE_TEACHER = "teacher"
    ROLE_GUEST = "guest"

    ROLE_CHOICES = (
        (ROLE_NONE, "Без роли"),
        (ROLE_ADMIN, "Администратор"),
        (ROLE_TEACHER, "Учитель"),
        (ROLE_GUEST, "Гость"),
    )

    ACCESS_FIELDS = (
        "can_calendar",
        "can_teachers",
        "can_editor",
        "can_upload",
        "can_logs",
        "can_calls",
        "can_users",
    )

    role = forms.ChoiceField(label="Роль", choices=ROLE_CHOICES, required=True)
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput,
        required=False,
        help_text="Оставьте поле пустым, чтобы не менять пароль",
    )

    class Meta:
        model = CustomUser
        fields = [
            "full_name",
            "role",
            "can_calendar",
            "can_teachers",
            "can_editor",
            "can_upload",
            "can_logs",
            "can_calls",
            "can_users",
        ]
        labels = {
            "full_name": "ФИО",
            "can_calendar": "Календарь",
            "can_teachers": "Учителя",
            "can_editor": "Редактор",
            "can_upload": "Загрузка",
            "can_logs": "Логи",
            "can_calls": "Звонки",
            "can_users": "Пользователи",
        }

    def __init__(self, *args, actor=None, **kwargs):
        self.actor = actor
        super().__init__(*args, **kwargs)

        instance = self.instance
        if getattr(instance, "is_admin", False):
            self.fields["role"].initial = self.ROLE_ADMIN
        elif getattr(instance, "is_teacher", False):
            self.fields["role"].initial = self.ROLE_TEACHER
        elif getattr(instance, "is_guest", False):
            self.fields["role"].initial = self.ROLE_GUEST
        else:
            self.fields["role"].initial = self.ROLE_NONE

        if not (self.actor and getattr(self.actor, "is_superuser", False)):
            choices = [
                (value, label)
                for value, label in self.fields["role"].choices
                if value != self.ROLE_ADMIN
            ]
            self.fields["role"].choices = choices
            if self.fields["role"].initial == self.ROLE_ADMIN:
                self.fields["role"].initial = self.ROLE_NONE

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role") or self.ROLE_NONE
        actor_is_superuser = bool(self.actor and getattr(self.actor, "is_superuser", False))

        if role == self.ROLE_ADMIN and not actor_is_superuser:
            raise forms.ValidationError("Только суперпользователь может назначать роль «Администратор».")

        if role in {self.ROLE_ADMIN, self.ROLE_TEACHER, self.ROLE_GUEST}:
            for field_name in self.ACCESS_FIELDS:
                cleaned_data[field_name] = False

        if role == self.ROLE_ADMIN:
            for field_name in self.ACCESS_FIELDS:
                cleaned_data[field_name] = True

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data.get("role") or self.ROLE_NONE

        user.is_admin = role == self.ROLE_ADMIN
        user.is_teacher = role == self.ROLE_TEACHER
        user.is_guest = role == self.ROLE_GUEST

        if role in {self.ROLE_ADMIN, self.ROLE_TEACHER, self.ROLE_GUEST}:
            for field_name in self.ACCESS_FIELDS:
                setattr(user, field_name, False)

        if role == self.ROLE_ADMIN:
            for field_name in self.ACCESS_FIELDS:
                setattr(user, field_name, True)

        pwd = self.cleaned_data.get("password")
        if pwd:
            user.set_password(pwd)
        if commit:
            user.save()
        return user
