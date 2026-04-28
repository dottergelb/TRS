from __future__ import annotations

from . import views as legacy_views


export_to_docx = legacy_views.export_to_docx
replacement_daily_summary_docx = legacy_views.replacement_daily_summary_docx
replacement_summary_report = legacy_views.replacement_summary_report
replacement_teacher_summary_docx = legacy_views.replacement_teacher_summary_docx

__all__ = [
    "export_to_docx",
    "replacement_daily_summary_docx",
    "replacement_summary_report",
    "replacement_teacher_summary_docx",
]
