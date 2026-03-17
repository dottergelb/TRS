from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django import forms
from .models import CustomUser

class RegisterForm(UserCreationForm):
    """Регистрация пользователя (по умолчанию Django User)."""
    pass

class LoginForm(AuthenticationForm):
    """Форма логина (username + password)."""
    pass


class UserUpdateForm(forms.ModelForm):
    """
    Форма обновления пользователя. Позволяет администратору изменить
    ФИО, права доступа и пароль. Пароль не является частью полей модели,
    чтобы избежать перезаписи хэшированного пароля необработанным значением.
    Если поле «Пароль» оставить пустым, текущий пароль останется без изменений.
    """

    # Поле ввода нового пароля. Оно не связано напрямую с полем модели
    # `password`, поэтому значения не присваиваются автоматически при сохранении.
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput,
        required=False,
        help_text="Оставьте поле пустым, чтобы не менять пароль"
    )

    class Meta:
        model = CustomUser
        # Исключаем поле password из Meta.fields, чтобы избежать его перезаписи
        # сырым значением. Все флажки доступа и ФИО обновятся напрямую.
        fields = [
            'full_name',
            'can_calendar',
            'can_teachers',
            'can_editor',
            'can_upload',
            'can_logs',
            'can_calls',
            'can_users',
        ]
        labels = {
            'full_name': 'ФИО',
            'can_calendar': 'Календарь',
            'can_teachers': 'Учителя',
            'can_editor': 'Редактор',
            'can_upload': 'Загрузка',
            'can_logs': 'Логи',
            'can_calls': 'Звонки',
            'can_users': 'Пользователи',
        }

    def save(self, commit=True):
        # Сохраняем модель без коммита, чтобы можно было изменить пароль позже
        user = super().save(commit=False)
        pwd = self.cleaned_data.get('password')
        # Если введён новый пароль — хэшируем его
        if pwd:
            user.set_password(pwd)
        if commit:
            user.save()
        return user
