"""Helpers for grade/shift/time rules used in auto-replacement selection.

The project stores class names as strings (e.g. "1А", "10Б", "4", etc.).
For most rules we only need the numeric grade (1..11).
"""

from __future__ import annotations

import re
from datetime import date, time
from typing import Optional


DAY_MAP = {0: "пн", 1: "вт", 2: "ср", 3: "чт", 4: "пт", 5: "сб", 6: "вс"}


def day_short_from_date(d: date) -> str:
    """Return short weekday in Russian (пн/вт/...)."""
    return DAY_MAP[d.weekday()]


def extract_grade(class_group: str) -> Optional[int]:
    """Extract grade number from class label.

    Examples:
        "1А" -> 1
        "10Б" -> 10
        " 4 " -> 4
        "-" -> None
    """
    if not class_group:
        return None
    m = re.search(r"(\d{1,2})", str(class_group))
    if not m:
        return None
    try:
        g = int(m.group(1))
    except ValueError:
        return None
    if 1 <= g <= 11:
        return g
    return None


def overlaps(a_start: time, a_end: time, b_start: time, b_end: time) -> bool:
    """True if [a_start, a_end) intersects [b_start, b_end)."""
    return a_start < b_end and a_end > b_start


# --- Shift rules (school-specific) ---
# Primary school (1–4) is treated as 1st shift.
# For 5–11 the school uses a fixed mapping by grade:
#   6/7/8  -> 2nd shift
#   5/9/10/11 -> 1st shift
# If a grade is unknown (or outside 1..11), caller should fall back to time-based inference.
SECOND_SHIFT_GRADES = {6, 7, 8}
FIRST_SHIFT_GRADES_SECONDARY = {5, 9, 10, 11}


def infer_shift_by_grade(grade: Optional[int]) -> Optional[int]:
    """Infer shift (1/2) from grade according to school rules.

    Returns:
        1 or 2 if grade is recognized,
        None if grade is unknown.
    """
    if grade is None:
        return None
    if 1 <= grade <= 4:
        return 1
    if grade in SECOND_SHIFT_GRADES:
        return 2
    if grade in FIRST_SHIFT_GRADES_SECONDARY:
        return 1
    return None
