from __future__ import annotations

from contextvars import ContextVar


request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
current_school_id_var: ContextVar[int | None] = ContextVar("current_school_id", default=None)
