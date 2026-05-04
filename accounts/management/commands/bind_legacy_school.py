from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import CustomUser, School
from communications.models import (
    ChatMessage,
    NotificationReplacementItem,
    NotificationStatus,
    SystemNotification,
    Ticket,
    TicketMessage,
    TicketParticipant,
)
from replacements.models import (
    ActivityLog,
    ClassSchedule,
    DocxImportTask,
    Lesson,
    Replacement,
    SpecialReplacement,
    Subject,
    Teacher,
)


DEFAULT_SCHOOL_NAME = "МБОУ СОШ №95 им. Героя России Крынина А.Э."


class Command(BaseCommand):
    help = "Bind legacy single-school data to default School row"

    @transaction.atomic
    def handle(self, *args, **options):
        school, created = School.objects.get_or_create(
            name=DEFAULT_SCHOOL_NAME,
            defaults={
                "status": School.STATUS_APPROVED,
                "approved_at": timezone.now(),
            },
        )
        if school.status != School.STATUS_APPROVED:
            school.status = School.STATUS_APPROVED
            school.approved_at = school.approved_at or timezone.now()
            school.save(update_fields=["status", "approved_at"])

        self.stdout.write(
            self.style.SUCCESS(
                f"School: {school.name} (id={school.id}) {'created' if created else 'exists'}"
            )
        )

        models_to_bind = [
            Teacher,
            Subject,
            Lesson,
            Replacement,
            SpecialReplacement,
            ClassSchedule,
            ActivityLog,
            DocxImportTask,
            ChatMessage,
            SystemNotification,
            NotificationReplacementItem,
            NotificationStatus,
            Ticket,
            TicketParticipant,
            TicketMessage,
        ]

        for model in models_to_bind:
            updated = model.all_objects.filter(school__isnull=True).update(school=school)
            self.stdout.write(f"{model.__name__}: bound {updated}")

        users_updated = CustomUser.objects.filter(
            school__isnull=True,
            is_superuser=False,
            is_project_admin=False,
            is_support_system=False,
            is_system_account=False,
        ).update(school=school)
        self.stdout.write(f"CustomUser (school users): bound {users_updated}")

        cleaned = CustomUser.objects.filter(
            school=school
        ).filter(
            Q(is_superuser=True)
            | Q(is_project_admin=True)
            | Q(is_support_system=True)
            | Q(is_system_account=True)
        ).update(school=None)
        self.stdout.write(f"CustomUser (project users): unbound {cleaned}")

        self.stdout.write(self.style.SUCCESS("Done"))
