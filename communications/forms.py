from django import forms
from django.conf import settings


class ChatMessageForm(forms.Form):
    text = forms.CharField(
        label="Сообщение",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Введите сообщение"}),
        max_length=4000,
        required=False,
    )
    attachment = forms.FileField(label="Файл", required=False)

    ALLOWED_ATTACHMENT_EXTENSIONS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".bmp",
        ".svg",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".txt",
        ".rtf",
        ".zip",
        ".rar",
        ".7z",
    }

    def clean_attachment(self):
        attachment = self.cleaned_data.get("attachment")
        if not attachment:
            return attachment
        max_size = int(getattr(settings, "MAX_CHAT_ATTACHMENT_SIZE", 5 * 1024 * 1024))
        if attachment.size > max_size:
            raise forms.ValidationError(f"Файл слишком большой (максимум {max_size // (1024 * 1024)} МБ).")
        filename = (attachment.name or "").lower()
        if "." not in filename:
            raise forms.ValidationError("У файла должно быть расширение.")
        ext = "." + filename.rsplit(".", 1)[-1]
        if ext not in self.ALLOWED_ATTACHMENT_EXTENSIONS:
            raise forms.ValidationError("Недопустимый тип файла.")
        return attachment

    def clean(self):
        cleaned_data = super().clean()
        text = (cleaned_data.get("text") or "").strip()
        attachment = cleaned_data.get("attachment")
        if not text and not attachment:
            raise forms.ValidationError("Введите сообщение или выберите файл.")
        cleaned_data["text"] = text
        return cleaned_data


class TicketMessageForm(forms.Form):
    text = forms.CharField(
        label="Ответ",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Введите сообщение"}),
        max_length=4000,
        required=False,
    )
    attachment = forms.FileField(label="Файл", required=False)

    ALLOWED_ATTACHMENT_EXTENSIONS = ChatMessageForm.ALLOWED_ATTACHMENT_EXTENSIONS

    def clean_attachment(self):
        attachment = self.cleaned_data.get("attachment")
        if not attachment:
            return attachment
        max_size = int(getattr(settings, "MAX_CHAT_ATTACHMENT_SIZE", 5 * 1024 * 1024))
        if attachment.size > max_size:
            raise forms.ValidationError(f"Файл слишком большой (максимум {max_size // (1024 * 1024)} МБ).")
        filename = (attachment.name or "").lower()
        if "." not in filename:
            raise forms.ValidationError("У файла должно быть расширение.")
        ext = "." + filename.rsplit(".", 1)[-1]
        if ext not in self.ALLOWED_ATTACHMENT_EXTENSIONS:
            raise forms.ValidationError("Недопустимый тип файла.")
        return attachment

    def clean(self):
        cleaned_data = super().clean()
        text = (cleaned_data.get("text") or "").strip()
        attachment = cleaned_data.get("attachment")
        if not text and not attachment:
            raise forms.ValidationError("Введите сообщение или выберите файл.")
        cleaned_data["text"] = text
        return cleaned_data


class NotificationQuestionForm(forms.Form):
    subject = forms.CharField(
        label="Проблема",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Проблема"}),
    )
    text = forms.CharField(
        label="Опишите проблему",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Опишите проблему"}),
        max_length=4000,
        required=False,
    )


class SupportTicketCreateForm(forms.Form):
    subject = forms.CharField(
        label="Тема",
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "Кратко опишите проблему"}),
    )
    text = forms.CharField(
        label="Описание",
        max_length=4000,
        widget=forms.Textarea(attrs={"rows": 6, "placeholder": "Подробности проблемы"}),
    )
