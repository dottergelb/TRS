from __future__ import annotations

from datetime import datetime
import mimetypes

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .forms import ChatMessageForm, NotificationQuestionForm, TicketMessageForm
from accounts.icon_service import get_icon_for_user
from .models import (
    ChatMessage,
    NotificationStatus,
    SystemNotification,
    Ticket,
    TicketMessage,
    TicketParticipant,
)
from .services import (
    build_notification_preview,
    ensure_system_user,
    is_admin_user,
    mark_notification_read,
    send_notifications_for_date,
)


User = get_user_model()


def _is_teacher_user(user) -> bool:
    return bool(getattr(user, "is_teacher", False))


def _is_guest_user(user) -> bool:
    return bool(getattr(user, "is_guest", False))


def _forbidden():
    return HttpResponse("Forbidden", status=403)


def _can_use_chat_with(user) -> bool:
    return not bool(
        getattr(user, "is_guest", False)
        or _is_vacancy_user(user)
        or str(getattr(user, "username", "")).strip().lower() == "admin"
    )


def _display_name(user) -> str:
    return str(getattr(user, "full_name", "") or getattr(user, "username", ""))


def _is_vacancy_user(user) -> bool:
    value = f"{getattr(user, 'full_name', '')} {getattr(user, 'username', '')}".strip().lower()
    return ("вакан" in value) or ("vakans" in value) or ("vacanc" in value)


def _build_chats_state(me, selected_user, thread_limit: int | None = None):
    default_thread_limit = int(getattr(settings, "CHAT_THREAD_LIMIT", 200))
    if thread_limit is None:
        thread_limit = default_thread_limit
    thread_limit = max(1, min(int(thread_limit), 500))

    users = (
        User.objects.filter(
            is_active=True,
            is_guest=False,
        )
        .exclude(id=me.id)
        .exclude(is_system_account=True)
        .exclude(username__iexact="admin")
        .exclude(full_name__icontains="вакан")
        .exclude(full_name__icontains="vakans")
        .exclude(full_name__icontains="vacanc")
        .exclude(username__icontains="вакан")
        .exclude(username__icontains="vakans")
        .exclude(username__icontains="vacanc")
        .order_by("full_name", "username")
    )

    messages_qs = ChatMessage.objects.filter(Q(sender=me) | Q(recipient=me)).select_related("sender", "recipient")
    dialogs_map = {}
    for m in messages_qs.order_by("created_at"):
        counterpart = m.recipient if m.sender_id == me.id else m.sender
        if not _can_use_chat_with(counterpart):
            continue
        item = dialogs_map.setdefault(
            counterpart.id,
            {"user": counterpart, "last_message": m, "unread_count": 0},
        )
        item["last_message"] = m
        if m.recipient_id == me.id and m.read_at is None:
            item["unread_count"] += 1
    dialogs = sorted(dialogs_map.values(), key=lambda x: x["last_message"].created_at, reverse=True)

    thread = []
    if selected_user is not None:
        if not _can_use_chat_with(selected_user):
            return None
        thread = list(
            ChatMessage.objects.filter(
                Q(sender=me, recipient=selected_user) | Q(sender=selected_user, recipient=me)
            )
            .select_related("sender", "recipient", "system_notification")
            .prefetch_related("system_notification__tickets")
            .order_by("-created_at")[:thread_limit]
        )
        thread.reverse()
        unread_qs = ChatMessage.objects.filter(sender=selected_user, recipient=me, read_at__isnull=True)
        unread_notification_ids = []
        if selected_user.is_system_account:
            unread_notification_ids = list(
                unread_qs.exclude(system_notification_id=None)
                .values_list("system_notification_id", flat=True)
                .distinct()
            )
        unread_qs.update(read_at=timezone.now())
        if unread_notification_ids:
            notifications = SystemNotification.objects.filter(id__in=unread_notification_ids, recipient=me)
            for notification in notifications:
                mark_notification_read(notification, me)

    return {
        "users": users,
        "dialogs": dialogs,
        "thread": thread,
        "unread_total": ChatMessage.objects.filter(recipient=me, read_at__isnull=True).count(),
    }


def _notification_state(notification, ticket):
    if notification.status == SystemNotification.STATUS_ACKNOWLEDGED:
        return "ack"
    if notification.status == SystemNotification.STATUS_QUESTION:
        if ticket and ticket.status == Ticket.STATUS_CLOSED:
            return "question_closed"
        return "question_open"
    return "pending"


def _ticket_visible_for_user(ticket: Ticket, user) -> bool:
    if is_admin_user(user):
        return True
    if ticket.author_id == user.id:
        return True
    return TicketParticipant.objects.filter(ticket=ticket, user=user).exists()


@login_required
def cabinet_view(request):
    user = request.user
    chat_unread = 0
    if not _is_guest_user(user):
        chat_unread = ChatMessage.objects.filter(recipient=user, read_at__isnull=True).count()
    context = {
        "is_admin": is_admin_user(user),
        "is_teacher": _is_teacher_user(user),
        "notifications_unread": SystemNotification.objects.filter(
            recipient=user,
            status=SystemNotification.STATUS_CREATED,
        ).count(),
        "chat_unread": chat_unread,
    }
    if is_admin_user(user):
        context["open_tickets"] = Ticket.objects.filter(status=Ticket.STATUS_OPEN).count()
    else:
        context["open_tickets"] = Ticket.objects.filter(author=user, status=Ticket.STATUS_OPEN).count()
    return render(request, "comm_cabinet.html", context)


@login_required
def chats_view(request, user_id: int | None = None):
    me = request.user
    if _is_guest_user(me):
        return _forbidden()

    system_user = ensure_system_user()

    selected_user = None
    form = ChatMessageForm(request.POST or None, request.FILES or None)
    if user_id:
        selected_user = get_object_or_404(User, id=user_id, is_active=True)
        if not _can_use_chat_with(selected_user):
            return _forbidden()

        if request.method == "POST":
            if selected_user.is_system_account:
                messages.error(request, "Нельзя отвечать системному аккаунту.")
                return redirect("communications:chats_with", user_id=selected_user.id)
            if form.is_valid():
                attachment = form.cleaned_data.get("attachment")
                attachment_name = ""
                attachment_mime = ""
                if attachment:
                    attachment_name = (getattr(attachment, "name", "") or "").strip()
                    attachment_mime = (getattr(attachment, "content_type", "") or "").strip()
                    if not attachment_mime:
                        attachment_mime = mimetypes.guess_type(attachment_name)[0] or ""
                ChatMessage.objects.create(
                    sender=me,
                    recipient=selected_user,
                    text=form.cleaned_data["text"],
                    attachment=attachment,
                    attachment_name=attachment_name[:255],
                    attachment_mime=attachment_mime[:120],
                    message_type=ChatMessage.TYPE_USER,
                )
                return redirect("communications:chats_with", user_id=selected_user.id)

    state = _build_chats_state(me, selected_user)
    if state is None:
        return _forbidden()

    return render(
        request,
        "comm_chats.html",
        {
            "dialogs": state["dialogs"],
            "users": state["users"],
            "selected_user": selected_user,
            "thread": state["thread"],
            "unread_total": state["unread_total"],
            "form": form,
            "system_user_id": system_user.id,
            "is_admin": is_admin_user(me),
            "question_form": NotificationQuestionForm(),
        },
    )


@login_required
@require_GET
def chats_state_api(request):
    me = request.user
    if _is_guest_user(me):
        return _forbidden()

    system_user = ensure_system_user()
    selected_user = None
    thread_limit_raw = (request.GET.get("thread_limit") or "").strip()
    thread_limit = None
    if thread_limit_raw:
        try:
            thread_limit = int(thread_limit_raw)
        except ValueError:
            return JsonResponse({"error": "invalid thread_limit"}, status=400)

    user_id_raw = (request.GET.get("user_id") or "").strip()
    if user_id_raw:
        try:
            selected_user_id = int(user_id_raw)
        except ValueError:
            return JsonResponse({"error": "invalid user_id"}, status=400)
        selected_user = get_object_or_404(User, id=selected_user_id, is_active=True)
        if not _can_use_chat_with(selected_user):
            return _forbidden()

    state = _build_chats_state(me, selected_user, thread_limit=thread_limit)
    if state is None:
        return _forbidden()

    dialogs_payload = []
    for item in state["dialogs"]:
        last_msg = item["last_message"]
        last_message_text = (last_msg.text or "").strip()
        if not last_message_text and last_msg.attachment:
            last_message_text = f"📎 {last_msg.safe_attachment_name or 'Файл'}"
        dialogs_payload.append(
            {
                "user_id": item["user"].id,
                "display_name": _display_name(item["user"]),
                "icon": get_icon_for_user(item["user"]),
                "unread_count": item["unread_count"],
                "last_message_text": last_message_text,
                "last_message_at": timezone.localtime(last_msg.created_at).strftime("%d.%m.%Y %H:%M"),
            }
        )

    users_payload = [
        {
            "id": user.id,
            "display_name": _display_name(user),
            "icon": get_icon_for_user(user),
        }
        for user in state["users"]
    ]

    notif_ids = [msg.system_notification_id for msg in state["thread"] if msg.system_notification_id]
    tickets_map = {}
    if notif_ids:
        tickets = (
            Ticket.objects.filter(notification_id__in=notif_ids)
            .order_by("notification_id", "-created_at")
            .only("id", "notification_id", "status")
        )
        for ticket in tickets:
            if ticket.notification_id not in tickets_map:
                tickets_map[ticket.notification_id] = ticket

    thread_payload = []
    for msg in state["thread"]:
        payload_item = {
            "id": msg.id,
            "sender_id": msg.sender_id,
            "sender_name": _display_name(msg.sender),
            "text": msg.text,
            "attachment_url": msg.attachment.url if msg.attachment else "",
            "attachment_name": msg.safe_attachment_name,
            "attachment_is_image": msg.is_image_attachment if msg.attachment else False,
            "message_type": msg.message_type,
            "is_mine": msg.sender_id == me.id,
            "created_at": timezone.localtime(msg.created_at).strftime("%d.%m.%Y %H:%M"),
        }
        notification = msg.system_notification
        if notification:
            ticket = tickets_map.get(notification.id)
            payload_item.update(
                {
                    "notification_id": notification.id,
                    "notification_status": notification.status,
                    "notification_state": _notification_state(notification, ticket),
                    "notification_ack_url": reverse("communications:notification_ack", args=[notification.id]),
                    "notification_question_url": reverse("communications:notification_question", args=[notification.id]),
                    "notification_can_act": (not is_admin_user(me))
                    and notification.status in {SystemNotification.STATUS_CREATED, SystemNotification.STATUS_READ},
                    "notification_ticket_url": (
                        reverse("communications:ticket_detail", args=[ticket.id])
                        if ticket and notification.status == SystemNotification.STATUS_QUESTION
                        else ""
                    ),
                }
            )
        thread_payload.append(payload_item)

    return JsonResponse(
        {
            "dialogs": dialogs_payload,
            "users": users_payload,
            "unread_total": state["unread_total"],
            "selected_user": (
                {
                    "id": selected_user.id,
                    "display_name": _display_name(selected_user),
                    "icon": get_icon_for_user(selected_user),
                    "is_system_account": bool(selected_user.is_system_account),
                }
                if selected_user
                else None
            ),
            "thread": thread_payload,
            "system_user_id": system_user.id,
        }
    )


@login_required
@require_POST
def chats_read_all_api(request):
    me = request.user
    if _is_guest_user(me):
        return _forbidden()
    updated = ChatMessage.objects.filter(recipient=me, read_at__isnull=True).update(read_at=timezone.now())
    unread_total = ChatMessage.objects.filter(recipient=me, read_at__isnull=True).count()
    return JsonResponse({"ok": True, "updated": updated, "unread_total": unread_total})


@login_required
def notifications_view(request):
    user = request.user
    if is_admin_user(user):
        notifications = (
            SystemNotification.objects.select_related("recipient", "created_by_admin")
            .prefetch_related("items")
            .order_by("-created_at")
        )
        return render(request, "comm_notifications_admin.html", {"notifications": notifications})
    system_user = ensure_system_user()
    return redirect("communications:chats_with", user_id=system_user.id)


@login_required
@require_POST
def notification_acknowledge_view(request, notification_id: int):
    n = get_object_or_404(SystemNotification, id=notification_id)
    if n.recipient_id != request.user.id and not is_admin_user(request.user):
        return _forbidden()
    n.status = SystemNotification.STATUS_ACKNOWLEDGED
    n.acted_at = timezone.now()
    if n.read_at is None:
        n.read_at = n.acted_at
    n.save(update_fields=["status", "acted_at", "read_at"])
    NotificationStatus.objects.create(notification=n, status=SystemNotification.STATUS_ACKNOWLEDGED, changed_by=request.user)
    if is_admin_user(request.user):
        return redirect("communications:notifications")
    system_user = ensure_system_user()
    return redirect("communications:chats_with", user_id=system_user.id)


@login_required
@require_POST
def notification_question_view(request, notification_id: int):
    n = get_object_or_404(SystemNotification, id=notification_id)
    if n.recipient_id != request.user.id and not is_admin_user(request.user):
        return _forbidden()

    form = NotificationQuestionForm(request.POST)
    subject = f"Вопрос по уведомлению от {n.target_date.strftime('%d.%m.%Y')}"
    text = "Есть вопросы по назначенным заменам."
    if form.is_valid():
        if form.cleaned_data.get("subject"):
            subject = form.cleaned_data["subject"].strip()
        if form.cleaned_data.get("text"):
            text = form.cleaned_data["text"].strip()

    ticket = Ticket.objects.create(
        author=n.recipient,
        notification=n,
        subject=subject,
        status=Ticket.STATUS_OPEN,
    )
    TicketParticipant.objects.get_or_create(ticket=ticket, user=n.recipient, defaults={"role": TicketParticipant.ROLE_AUTHOR})
    for admin in User.objects.filter(Q(is_superuser=True) | Q(is_admin=True), is_active=True):
        TicketParticipant.objects.get_or_create(ticket=ticket, user=admin, defaults={"role": TicketParticipant.ROLE_ADMIN})
    TicketMessage.objects.create(ticket=ticket, author=n.recipient, text=text)

    n.status = SystemNotification.STATUS_QUESTION
    n.acted_at = timezone.now()
    if n.read_at is None:
        n.read_at = n.acted_at
    n.save(update_fields=["status", "acted_at", "read_at"])
    NotificationStatus.objects.create(notification=n, status=SystemNotification.STATUS_QUESTION, changed_by=request.user)
    return redirect("communications:ticket_detail", ticket_id=ticket.id)


@login_required
def tickets_view(request):
    user = request.user
    qs = Ticket.objects.select_related("author", "notification").prefetch_related("participants")

    show_archive = request.GET.get("archive") == "1"
    if show_archive:
        qs = qs.filter(status=Ticket.STATUS_CLOSED)
    else:
        qs = qs.filter(status=Ticket.STATUS_OPEN)

    if not is_admin_user(user):
        qs = qs.filter(author=user)

    qs = qs.order_by("-is_important", "-created_at")
    return render(request, "comm_tickets.html", {"tickets": qs, "archive": show_archive, "is_admin": is_admin_user(user)})


@login_required
def ticket_detail_view(request, ticket_id: int):
    ticket = get_object_or_404(Ticket.objects.select_related("author", "notification"), id=ticket_id)
    if not _ticket_visible_for_user(ticket, request.user):
        return _forbidden()

    can_write = ticket.status == Ticket.STATUS_OPEN and (is_admin_user(request.user) or ticket.author_id == request.user.id)
    form = TicketMessageForm(request.POST or None)
    if request.method == "POST":
        if not can_write:
            return _forbidden()
        if form.is_valid():
            TicketMessage.objects.create(ticket=ticket, author=request.user, text=form.cleaned_data["text"].strip())
            return redirect("communications:ticket_detail", ticket_id=ticket.id)

    msgs = ticket.messages.select_related("author").all()
    return render(
        request,
        "comm_ticket_detail.html",
        {"ticket": ticket, "messages_list": msgs, "form": form, "can_write": can_write, "is_admin": is_admin_user(request.user)},
    )


@login_required
@require_POST
def ticket_toggle_important_view(request, ticket_id: int):
    if not is_admin_user(request.user):
        return _forbidden()
    ticket = get_object_or_404(Ticket, id=ticket_id)
    ticket.is_important = not ticket.is_important
    ticket.save(update_fields=["is_important"])
    return redirect("communications:ticket_detail", ticket_id=ticket.id)


@login_required
@require_POST
def ticket_close_view(request, ticket_id: int):
    if not is_admin_user(request.user):
        return _forbidden()
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if ticket.status != Ticket.STATUS_CLOSED:
        ticket.status = Ticket.STATUS_CLOSED
        ticket.closed_at = timezone.now()
        ticket.closed_by = request.user
        ticket.save(update_fields=["status", "closed_at", "closed_by"])
    return redirect("communications:ticket_detail", ticket_id=ticket.id)


@login_required
@require_POST
def ticket_reopen_view(request, ticket_id: int):
    if not is_admin_user(request.user):
        return _forbidden()
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if ticket.status != Ticket.STATUS_OPEN:
        ticket.status = Ticket.STATUS_OPEN
        ticket.reopened_at = timezone.now()
        ticket.save(update_fields=["status", "reopened_at"])
    return redirect("communications:ticket_detail", ticket_id=ticket.id)


@login_required
@require_GET
def notifications_preview_api(request):
    if not is_admin_user(request.user):
        return _forbidden()
    date_raw = (request.GET.get("date") or "").strip()
    try:
        target_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
    except Exception:
        return JsonResponse({"error": "Некорректная дата, ожидается YYYY-MM-DD"}, status=400)
    preview = build_notification_preview(target_date)
    return JsonResponse(
        {
            "date": target_date.strftime("%Y-%m-%d"),
            "teachers": preview,
            "teachers_count": len(preview),
            "teachers_with_user": len([p for p in preview if p.get("user_id")]),
        }
    )


@login_required
@require_POST
def notifications_send_api(request):
    if not is_admin_user(request.user):
        return _forbidden()
    try:
        import json

        payload = json.loads(request.body or "{}")
    except Exception:
        payload = {}
    date_raw = (payload.get("date") or "").strip()
    try:
        target_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
    except Exception:
        return JsonResponse({"error": "Некорректная дата, ожидается YYYY-MM-DD"}, status=400)
    result = send_notifications_for_date(target_date=target_date, admin_user=request.user)
    return JsonResponse({"ok": True, **result})


@login_required
@require_GET
def unread_counts_api(request):
    user = request.user
    unread_messages = 0
    if not _is_guest_user(user):
        unread_messages = ChatMessage.objects.filter(recipient=user, read_at__isnull=True).count()
    unread_notifications = SystemNotification.objects.filter(
        recipient=user,
        status=SystemNotification.STATUS_CREATED,
    ).count()
    return JsonResponse(
        {
            "messages": unread_messages,
            "notifications": unread_notifications,
        }
    )
