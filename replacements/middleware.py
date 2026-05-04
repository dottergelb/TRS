from __future__ import annotations

import uuid

from .request_context import current_school_id_var, request_id_var


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_var.set(request_id)
        request.request_id = request_id
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = request_id
            return response
        finally:
            request_id_var.reset(token)


class SchoolContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        school_id = None
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            if getattr(user, "is_superuser", False) or getattr(user, "is_project_admin", False):
                school_id = request.session.get("active_school_id")
                if not school_id:
                    # Project-level users must explicitly select a school to access school data.
                    school_id = -1
            elif getattr(user, "is_support_system", False):
                # Support users are project-level operators but not superusers.
                # They are filtered by explicit participant checks in communications views.
                school_id = None
            else:
                school_id = getattr(user, "school_id", None)
                if not school_id:
                    # Any authenticated school-level user without school binding
                    # must not see global data by mistake.
                    school_id = -1
        request.current_school_id = school_id
        token = current_school_id_var.set(school_id)
        try:
            return self.get_response(request)
        finally:
            current_school_id_var.reset(token)
