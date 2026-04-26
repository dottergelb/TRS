from __future__ import annotations

from collections import defaultdict
from datetime import date

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from replacements.models import Replacement, SpecialReplacement

from .models import (
    ChatMessage,
    NotificationReplacementItem,
    NotificationStatus,
    SystemNotification,
)


User = get_user_model()


def is_admin_user(user) -> bool:
    return bool(getattr(user, "is_authenticated", False) and (user.is_superuser or getattr(user, "is_admin", False)))


def ensure_system_user():
    username = "system_notify"
    user = User.objects.filter(is_system_account=True).first()
    if user:
        return user

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "full_name": "Система оповещения",
            "is_active": True,
            "is_staff": False,
            "is_system_account": True,
            "is_admin": False,
            "is_teacher": False,
            "is_guest": False,
            "can_calendar": False,
            "can_teachers": False,
            "can_editor": False,
            "can_upload": False,
            "can_logs": False,
            "can_calls": False,
            "can_users": False,
        },
    )
    changed = False
    if not user.is_system_account:
        user.is_system_account = True
        changed = True
    if (user.full_name or "").strip() != "Система оповещения":
        user.full_name = "Система оповещения"
        changed = True
    if created or changed:
        user.set_unusable_password()
        user.save()
    return user


def _lesson_time_and_subject(replacement: Replacement):
    lesson = replacement.lesson
    if not lesson:
        return None, None, ""
    return lesson.start_time, lesson.end_time, (lesson.subject.name if lesson.subject else "")


def _replacement_rows_for_date(target_date: date):
    rows = []

    repl_qs = (
        Replacement.objects.filter(date=target_date)
        .exclude(replacement_teacher_id=None)
        .exclude(original_teacher_id=None)
        .exclude(replacement_teacher_id=F("original_teacher_id"))
        .select_related("lesson__subject", "original_teacher", "replacement_teacher")
        .order_by("lesson__lesson_number", "lesson__class_group", "id")
    )
    for r in repl_qs:
        st, en, subj = _lesson_time_and_subject(r)
        rows.append(
            {
                "teacher_name": r.replacement_teacher.full_name if r.replacement_teacher else "",
                "teacher_id": r.replacement_teacher_id,
                "replacement_id": r.id,
                "date": r.date,
                "lesson_number": (r.lesson.lesson_number if r.lesson else None),
                "class_group": (r.lesson.class_group if r.lesson else ""),
                "subject_name": subj,
                "time_start": st,
                "time_end": en,
                "original_teacher_name": (r.original_teacher.full_name if r.original_teacher else ""),
                "replacement_teacher_name": (r.replacement_teacher.full_name if r.replacement_teacher else ""),
            }
        )

    special_qs = (
        SpecialReplacement.objects.filter(date=target_date)
        .exclude(replacement_teacher_id=None)
        .select_related("original_teacher", "replacement_teacher")
        .order_by("lesson_number", "class_group", "id")
    )
    for s in special_qs:
        rows.append(
            {
                "teacher_name": s.replacement_teacher.full_name if s.replacement_teacher else "",
                "teacher_id": s.replacement_teacher_id,
                "replacement_id": None,
                "date": s.date,
                "lesson_number": s.lesson_number,
                "class_group": s.class_group or "",
                "subject_name": s.subject_name or "",
                "time_start": s.start_time,
                "time_end": s.end_time,
                "original_teacher_name": (s.original_teacher.full_name if s.original_teacher else ""),
                "replacement_teacher_name": (s.replacement_teacher.full_name if s.replacement_teacher else ""),
            }
        )

    return rows


def build_notification_preview(target_date: date):
    rows = _replacement_rows_for_date(target_date)
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["teacher_id"], row["teacher_name"])].append(row)

    preview = []
    for (teacher_id, teacher_name), items in sorted(grouped.items(), key=lambda x: (x[0][1].casefold(), x[0][0] or 0)):
        user = User.objects.filter(full_name__iexact=(teacher_name or "").strip(), is_active=True).first()
        preview.append(
            {
                "teacher_id": teacher_id,
                "teacher_name": teacher_name,
                "user_id": user.id if user else None,
                "username": user.username if user else "",
                "items_count": len(items),
                "items": items,
            }
        )
    return preview


def _render_notification_body(target_date: date, teacher_name: str, items: list[dict]) -> str:
    lines = [
        "Здравствуйте!",
        "",
        f"Вам назначены замены на {target_date.strftime('%d.%m.%Y')}:",
        "",
    ]
    for i, row in enumerate(items, start=1):
        start = row.get("time_start")
        end = row.get("time_end")
        lesson_number = row.get("lesson_number")
        class_group = row.get("class_group") or "—"
        if start and end:
            t_part = f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')}"
        else:
            t_part = "время не указано"
        lesson_part = f"{lesson_number} урок" if lesson_number is not None else "отдельный урок"
        lines.append(f"{i}. {t_part} — {lesson_part} — {class_group}")
    lines.extend(["", "Пожалуйста, подтвердите ознакомление или задайте вопрос."])
    return "\n".join(lines)


@transaction.atomic
def send_notifications_for_date(*, target_date: date, admin_user):
    system_user = ensure_system_user()
    preview = build_notification_preview(target_date)

    created_notifications = 0
    skipped_without_user = 0
    recipients = 0
    for group in preview:
        recipient_id = group.get("user_id")
        if not recipient_id:
            skipped_without_user += 1
            continue

        recipient = User.objects.get(id=recipient_id)
        items = group["items"]
        body = _render_notification_body(target_date, group.get("teacher_name") or "", items)

        notification = SystemNotification.objects.create(
            recipient=recipient,
            sender_system_user=system_user,
            created_by_admin=admin_user,
            target_date=target_date,
            title=f"Замещения на {target_date.strftime('%d.%m.%Y')}",
            body=body,
            status=SystemNotification.STATUS_CREATED,
        )
        NotificationStatus.objects.create(
            notification=notification,
            status=SystemNotification.STATUS_CREATED,
            changed_by=admin_user,
        )

        NotificationReplacementItem.objects.bulk_create(
            [
                NotificationReplacementItem(
                    notification=notification,
                    replacement_id=row.get("replacement_id"),
                    replacement_date=row.get("date"),
                    lesson_number=row.get("lesson_number"),
                    class_group=row.get("class_group") or "",
                    subject_name=row.get("subject_name") or "",
                    time_start=row.get("time_start"),
                    time_end=row.get("time_end"),
                    original_teacher_name=row.get("original_teacher_name") or "",
                    replacement_teacher_name=row.get("replacement_teacher_name") or "",
                )
                for row in items
            ]
        )

        ChatMessage.objects.create(
            sender=system_user,
            recipient=recipient,
            text=body,
            message_type=ChatMessage.TYPE_SYSTEM,
            system_notification=notification,
        )
        created_notifications += 1
        recipients += 1

    return {
        "created_notifications": created_notifications,
        "skipped_without_user": skipped_without_user,
        "recipients": recipients,
        "preview_total": len(preview),
    }


def mark_notification_read(notification, user):
    if notification.status == SystemNotification.STATUS_CREATED:
        now = timezone.now()
        notification.status = SystemNotification.STATUS_READ
        notification.read_at = now
        notification.save(update_fields=["status", "read_at"])
        NotificationStatus.objects.create(
            notification=notification,
            status=SystemNotification.STATUS_READ,
            changed_by=user,
        )
