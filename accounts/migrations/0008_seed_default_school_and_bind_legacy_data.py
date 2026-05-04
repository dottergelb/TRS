from django.db import migrations
from django.utils import timezone


SCHOOL_NAME = "МБОУ СОШ №95 им. Героя России Крынина А.Э."


def forwards(apps, schema_editor):
    School = apps.get_model("accounts", "School")
    User = apps.get_model("accounts", "CustomUser")

    school, created = School.objects.get_or_create(
        name=SCHOOL_NAME,
        defaults={
            "status": "approved",
            "approved_at": timezone.now(),
        },
    )
    if not created and school.status != "approved":
        school.status = "approved"
        school.approved_at = school.approved_at or timezone.now()
        school.save(update_fields=["status", "approved_at"])

    # School-level users get legacy school; global/system users stay project-level.
    User.objects.filter(
        school__isnull=True,
        is_superuser=False,
        is_system_account=False,
        is_support_system=False,
    ).update(school=school)

    # Project admins from existing top-level admins (except school admins) can be set manually later.
    # We do not auto-convert is_admin to is_project_admin to avoid role drift.

    model_names = [
        ("replacements", "Teacher"),
        ("replacements", "Subject"),
        ("replacements", "Lesson"),
        ("replacements", "Replacement"),
        ("replacements", "SpecialReplacement"),
        ("replacements", "ClassSchedule"),
        ("replacements", "ActivityLog"),
        ("replacements", "DocxImportTask"),
        ("communications", "ChatMessage"),
        ("communications", "SystemNotification"),
        ("communications", "NotificationReplacementItem"),
        ("communications", "NotificationStatus"),
        ("communications", "Ticket"),
        ("communications", "TicketParticipant"),
        ("communications", "TicketMessage"),
    ]
    for app_label, model_name in model_names:
        Model = apps.get_model(app_label, model_name)
        Model.objects.filter(school__isnull=True).update(school=school)


def backwards(apps, schema_editor):
    # Safe rollback: clear school bindings from seeded school only.
    School = apps.get_model("accounts", "School")
    try:
        school = School.objects.get(name=SCHOOL_NAME)
    except School.DoesNotExist:
        return

    User = apps.get_model("accounts", "CustomUser")
    User.objects.filter(school=school).update(school=None)

    model_names = [
        ("replacements", "Teacher"),
        ("replacements", "Subject"),
        ("replacements", "Lesson"),
        ("replacements", "Replacement"),
        ("replacements", "SpecialReplacement"),
        ("replacements", "ClassSchedule"),
        ("replacements", "ActivityLog"),
        ("replacements", "DocxImportTask"),
        ("communications", "ChatMessage"),
        ("communications", "SystemNotification"),
        ("communications", "NotificationReplacementItem"),
        ("communications", "NotificationStatus"),
        ("communications", "Ticket"),
        ("communications", "TicketParticipant"),
        ("communications", "TicketMessage"),
    ]
    for app_label, model_name in model_names:
        Model = apps.get_model(app_label, model_name)
        Model.objects.filter(school=school).update(school=None)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_school_customuser_is_project_admin_and_more"),
        ("replacements", "0013_activitylog_school_classschedule_school_and_more"),
        ("communications", "0003_chatmessage_school_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
