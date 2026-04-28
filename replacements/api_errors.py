from __future__ import annotations

from functools import wraps
import logging

from django.db import DatabaseError
from django.http import JsonResponse


logger = logging.getLogger(__name__)


def api_json_errors(fn):
    @wraps(fn)
    def _wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (ValueError, TypeError) as exc:
            return JsonResponse({"error": str(exc) or "Некорректные данные запроса"}, status=400)
        except DatabaseError:
            logger.exception("Database error in replacement API: %s", fn.__name__)
            return JsonResponse({"error": "Ошибка доступа к данным"}, status=500)
        except Exception:
            logger.exception("Unhandled error in replacement API: %s", fn.__name__)
            return JsonResponse({"error": "Внутренняя ошибка сервера"}, status=500)

    return _wrapped
