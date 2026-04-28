from __future__ import annotations

from datetime import datetime

from .permissions_parsing import as_bool, as_int


def _gs_store():
    raise RuntimeError("Google Sheets backend is not configured in this build")


def _gs_parse_time(value):
    if value is None:
        return None
    if hasattr(value, "hour") and hasattr(value, "minute"):
        return value
    raw = str(value).strip()
    if not raw:
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    return None


def _gs_time_str(value) -> str:
    t = _gs_parse_time(value)
    return t.strftime("%H:%M") if t else ""


def _gs_next_id(rows: list[dict], key: str) -> int:
    current = [as_int(r.get(key)) for r in rows]
    current = [x for x in current if x is not None]
    return (max(current) + 1) if current else 1


def _gs_is_teacher_replacement(row: dict) -> bool:
    return as_int(row.get("replacement_teacher_id")) != as_int(row.get("original_teacher_id"))


def _gs_teacher_map() -> dict[int, str]:
    rows = _gs_store().get_table_dicts("replacements_teacher")
    return {as_int(r.get("teacher_id")): str(r.get("full_name") or "") for r in rows if as_int(r.get("teacher_id")) is not None}


def _gs_subject_map() -> dict[int, str]:
    rows = _gs_store().get_table_dicts("replacements_subject")
    return {as_int(r.get("id_subject")): str(r.get("name") or "") for r in rows if as_int(r.get("id_subject")) is not None}


def _gs_subject_id_by_name(name: str) -> int | None:
    target = (name or "").strip().casefold()
    if not target:
        return None
    for sid, sname in _gs_subject_map().items():
        if (sname or "").strip().casefold() == target:
            return sid
    return None


def _gs_lesson_map() -> dict[int, dict]:
    rows = _gs_store().get_table_dicts("replacements_lesson")
    return {as_int(r.get("lesson_id")): r for r in rows if as_int(r.get("lesson_id")) is not None}


def _gs_active_lessons_rows() -> list[dict]:
    return [r for r in _gs_store().get_table_dicts("replacements_lesson") if as_bool(r.get("is_active"))]


def _gs_shift_boundary(selected_date):
    schedule_rows = _gs_store().get_table_dicts("replacements_class_schedule")
    shift1_max_end = None
    shift2_min_start = None
    for row in schedule_rows:
        sh = as_int(row.get("shift"))
        st = _gs_parse_time(row.get("start_time"))
        en = _gs_parse_time(row.get("end_time"))
        if sh == 1 and en:
            shift1_max_end = en if shift1_max_end is None or en > shift1_max_end else shift1_max_end
        if sh == 2 and st:
            shift2_min_start = st if shift2_min_start is None or st < shift2_min_start else shift2_min_start

    boundary = shift2_min_start
    if shift1_max_end and shift2_min_start:
        dt1 = datetime.combine(selected_date, shift1_max_end)
        dt2 = datetime.combine(selected_date, shift2_min_start)
        boundary = (dt1 + (dt2 - dt1) / 2).time() if dt2 > dt1 else shift2_min_start
    return shift1_max_end, shift2_min_start, boundary


__all__ = [
    "_gs_store",
    "_gs_parse_time",
    "_gs_time_str",
    "_gs_next_id",
    "_gs_is_teacher_replacement",
    "_gs_teacher_map",
    "_gs_subject_map",
    "_gs_subject_id_by_name",
    "_gs_lesson_map",
    "_gs_active_lessons_rows",
    "_gs_shift_boundary",
]
