from django.conf import settings
from django.db import models
from django.utils.text import get_valid_filename


class ChatMessage(models.Model):
    TYPE_USER = "user"
    TYPE_SYSTEM = "system"
    TYPE_CHOICES = (
        (TYPE_USER, "Пользовательское"),
        (TYPE_SYSTEM, "Системное"),
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_chat_messages",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_chat_messages",
    )
    text = models.TextField()
    attachment = models.FileField(upload_to="chat_attachments/%Y/%m/%d/", null=True, blank=True)
    attachment_name = models.CharField(max_length=255, blank=True, default="")
    attachment_mime = models.CharField(max_length=120, blank=True, default="")
    message_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=TYPE_USER)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    system_notification = models.ForeignKey(
        "SystemNotification",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_messages",
    )

    class Meta:
        db_table = "communications_chat_message"
        ordering = ["created_at"]

    @property
    def safe_attachment_name(self) -> str:
        if self.attachment_name:
            return self.attachment_name
        if self.attachment:
            return get_valid_filename(self.attachment.name.rsplit("/", 1)[-1])
        return ""

    @property
    def is_image_attachment(self) -> bool:
        mime = (self.attachment_mime or "").lower().strip()
        if mime.startswith("image/"):
            return True
        filename = self.safe_attachment_name.lower()
        return filename.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"))


class SystemNotification(models.Model):
    STATUS_CREATED = "created"
    STATUS_READ = "read"
    STATUS_ACKNOWLEDGED = "acknowledged"
    STATUS_QUESTION = "question"
    STATUS_CHOICES = (
        (STATUS_CREATED, "Создано"),
        (STATUS_READ, "Прочитано"),
        (STATUS_ACKNOWLEDGED, "Ознакомлен"),
        (STATUS_QUESTION, "Есть вопросы"),
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="system_notifications",
    )
    sender_system_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_system_notifications",
    )
    created_by_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_system_notifications",
    )
    target_date = models.DateField(db_index=True)
    title = models.CharField(max_length=255, blank=True, default="")
    body = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CREATED, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    acted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "communications_system_notification"
        ordering = ["-created_at"]


class NotificationReplacementItem(models.Model):
    notification = models.ForeignKey(
        SystemNotification,
        on_delete=models.CASCADE,
        related_name="items",
    )
    replacement_id = models.IntegerField(null=True, blank=True)
    replacement_date = models.DateField(db_index=True)
    lesson_number = models.IntegerField(null=True, blank=True)
    class_group = models.CharField(max_length=50, blank=True, default="")
    subject_name = models.CharField(max_length=100, blank=True, default="")
    time_start = models.TimeField(null=True, blank=True)
    time_end = models.TimeField(null=True, blank=True)
    original_teacher_name = models.CharField(max_length=255, blank=True, default="")
    replacement_teacher_name = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "communications_notification_replacement_item"
        ordering = ["lesson_number", "class_group", "id"]


class NotificationStatus(models.Model):
    notification = models.ForeignKey(
        SystemNotification,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    status = models.CharField(max_length=20, choices=SystemNotification.STATUS_CHOICES, db_index=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="changed_notification_statuses",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "communications_notification_status"
        ordering = ["-created_at"]


class Ticket(models.Model):
    STATUS_OPEN = "open"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = (
        (STATUS_OPEN, "Открыт"),
        (STATUS_CLOSED, "Закрыт"),
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tickets_created",
    )
    notification = models.ForeignKey(
        SystemNotification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True)
    is_important = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    reopened_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets_closed",
    )

    class Meta:
        db_table = "communications_ticket"
        ordering = ["-is_important", "created_at"]


class TicketParticipant(models.Model):
    ROLE_AUTHOR = "author"
    ROLE_ADMIN = "admin"
    ROLE_CHOICES = (
        (ROLE_AUTHOR, "Автор"),
        (ROLE_ADMIN, "Администратор"),
    )

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ticket_participations",
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "communications_ticket_participant"
        unique_together = ("ticket", "user")


class TicketMessage(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_messages",
    )
    text = models.TextField()
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "communications_ticket_message"
        ordering = ["created_at"]
