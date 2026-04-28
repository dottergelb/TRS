from __future__ import annotations

from . import views as legacy_views


available_rooms = legacy_views.available_rooms
cabinet_lessons = legacy_views.cabinet_lessons
cabinet_replacement_view = legacy_views.cabinet_replacement_view
export_cabinet_docx = legacy_views.export_cabinet_docx
room_conflicts_api = legacy_views.room_conflicts_api
save_cabinet_replacements = legacy_views.save_cabinet_replacements

__all__ = [
    "available_rooms",
    "cabinet_lessons",
    "cabinet_replacement_view",
    "export_cabinet_docx",
    "room_conflicts_api",
    "save_cabinet_replacements",
]
