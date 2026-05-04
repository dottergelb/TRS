from __future__ import annotations

import logging
import base64
from datetime import datetime

from celery import shared_task

from .models import DocxImportTask, ActivityLog
from .request_context import current_school_id_var

logger = logging.getLogger(__name__)


@shared_task
def celery_heartbeat() -> str:
    now = datetime.utcnow().isoformat()
    logger.info("Celery heartbeat at %sZ", now)
    return now


@shared_task
def noop_background_task(payload: dict | None = None) -> dict:
    logger.info("No-op background task executed")
    return {"status": "ok", "payload": payload or {}}


@shared_task(bind=True)
def import_replacements_docx_task(
    self,
    *,
    job_id: str,
    file_bytes_b64: str,
    date_str: str,
    replace_all: bool,
    actor_user_id: int | None = None,
) -> dict:
    from datetime import datetime as dt
    from . import views as replacements_views

    try:
        job = DocxImportTask.objects.get(id=job_id)
    except DocxImportTask.DoesNotExist:
        logger.warning("DOCX import job %s not found", job_id)
        return {"status": "error", "error": "job_not_found"}

    job.status = DocxImportTask.STATUS_RUNNING
    job.error = ""
    job.save(update_fields=["status", "error", "updated_at"])

    try:
        file_bytes = base64.b64decode(file_bytes_b64.encode("ascii"))
        target_date = dt.strptime(date_str, "%Y-%m-%d").date()
        scope_school_id = job.school_id or (job.created_by.school_id if job.created_by_id and job.created_by else None)
        school_token = current_school_id_var.set(scope_school_id if scope_school_id else None)
        try:
            result = replacements_views._run_docx_import_core(
                file_bytes=file_bytes,
                target_date=target_date,
                replace_all=replace_all,
            )
        finally:
            current_school_id_var.reset(school_token)

        job.status = DocxImportTask.STATUS_SUCCESS
        job.parsed_rows = int(result.get("parsed_rows") or 0)
        job.created_count = int(result.get("created") or 0)
        job.skipped_same_teacher = int(result.get("skipped_same_teacher") or 0)
        job.unresolved_count = int(result.get("unresolved_count") or 0)
        job.unresolved_preview = result.get("unresolved") or []
        job.error = ""
        job.save(
            update_fields=[
                "status",
                "parsed_rows",
                "created_count",
                "skipped_same_teacher",
                "unresolved_count",
                "unresolved_preview",
                "error",
                "updated_at",
            ]
        )

        ActivityLog.objects.create(
            user_id=actor_user_id,
            action="replacements_import_docx",
            details={
                "job_id": str(job.id),
                "date": result.get("date"),
                "file_name": job.file_name,
                "parsed_rows": job.parsed_rows,
                "created": job.created_count,
                "unresolved": job.unresolved_count,
                "replace_all": bool(job.replace_all),
            },
        )
        return {"status": "success", "job_id": str(job.id), **result}
    except replacements_views.DocxImportProcessingError as exc:
        job.status = DocxImportTask.STATUS_FAILED
        job.error = exc.message
        job.unresolved_preview = exc.unresolved[:30]
        job.unresolved_count = len(exc.unresolved)
        job.save(
            update_fields=[
                "status",
                "error",
                "unresolved_preview",
                "unresolved_count",
                "updated_at",
            ]
        )
        return {"status": "failed", "job_id": str(job.id), "error": exc.message}
    except Exception as exc:
        logger.exception("DOCX import job %s failed", job_id)
        job.status = DocxImportTask.STATUS_FAILED
        job.error = str(exc) or "Внутренняя ошибка импорта"
        job.save(update_fields=["status", "error", "updated_at"])
        raise
