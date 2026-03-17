import logging
from typing import Any, Dict, Optional

from django.http import HttpRequest

from .models import ActivityLog

logger = logging.getLogger(__name__)


def _get_client_ip(request: HttpRequest) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        # can be comma-separated list
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or ""


def log_activity(request: Optional[HttpRequest], action: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Best-effort audit logger. Never raises."""
    try:
        if details is None:
            details = {}
        user = getattr(request, "user", None) if request is not None else None
        ActivityLog.objects.create(
            user=user if getattr(user, "is_authenticated", False) else None,
            action=str(action)[:64],
            details=details or {},
            ip_address=_get_client_ip(request) if request is not None else None,
            user_agent=str(request.META.get("HTTP_USER_AGENT", "") if request is not None else "")[:2000],
            path=str(request.path if request is not None else "")[:255],
            method=str(request.method if request is not None else "")[:16],
        )
    except Exception:
        logger.exception("Failed to write ActivityLog for action=%s", action)
