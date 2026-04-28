import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("replacements", "0011_specialreplacement_original_teacher"),
    ]

    operations = [
        migrations.CreateModel(
            name="DocxImportTask",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("celery_task_id", models.CharField(blank=True, default="", max_length=255)),
                ("file_name", models.CharField(blank=True, default="", max_length=255)),
                ("date", models.DateField()),
                ("replace_all", models.BooleanField(default=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("running", "Running"),
                            ("success", "Success"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="queued",
                        max_length=16,
                    ),
                ),
                ("parsed_rows", models.PositiveIntegerField(default=0)),
                ("created_count", models.PositiveIntegerField(default=0)),
                ("skipped_same_teacher", models.PositiveIntegerField(default=0)),
                ("unresolved_count", models.PositiveIntegerField(default=0)),
                ("unresolved_preview", models.JSONField(blank=True, default=list)),
                ("error", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "replacements_docx_import_task",
                "ordering": ["-created_at"],
            },
        ),
    ]
