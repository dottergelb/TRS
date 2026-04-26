from __future__ import annotations

from collections import Counter
from functools import lru_cache


SUBJECT_ICON_RULES: list[tuple[tuple[str, ...], str]] = [
    (("матем", "алгебр", "геометр"), "🧮"),
    (("русск", "литерат", "чтени"), "📚"),
    (("англ", "немец", "франц", "иностр"), "🗣️"),
    (("информ", "програм", "робот"), "💻"),
    (("физик",), "⚛️"),
    (("хим",), "🧪"),
    (("биолог",), "🧬"),
    (("истор", "обществ", "право"), "🗿"),
    (("географ",), "🌍"),
    (("физкульт", "спорт", "офп"), "⚽"),
    (("музык",), "🎵"),
    (("изо", "рисован", "черчен", "дизайн"), "🎨"),
    (("труд", "технолог", "столяр"), "🔨"),
]


def _normalize(value: str | None) -> str:
    return (value or "").strip().casefold()


def _icon_for_subject_text(subject_text: str | None) -> str | None:
    text = _normalize(subject_text)
    if not text:
        return None
    for keywords, icon in SUBJECT_ICON_RULES:
        if any(k in text for k in keywords):
            return icon
    return None


@lru_cache(maxsize=2048)
def _icon_for_teacher_full_name(full_name: str) -> str | None:
    try:
        from replacements.models import Lesson, Teacher
    except Exception:
        return None

    teacher = Teacher.objects.filter(full_name__iexact=full_name).only("id", "specialization").first()
    if not teacher:
        return None

    spec_icon = _icon_for_subject_text(getattr(teacher, "specialization", ""))
    if spec_icon:
        return spec_icon

    subjects = (
        Lesson.objects.filter(teacher=teacher, is_active=True)
        .select_related("subject")
        .values_list("subject__name", flat=True)
    )
    counter = Counter([_normalize(name) for name in subjects if name])
    if not counter:
        return None

    top_subject = counter.most_common(1)[0][0]
    return _icon_for_subject_text(top_subject)


def get_icon_for_display_name(display_name: str | None, *, default: str = "👤") -> str:
    name = (display_name or "").strip()
    if not name:
        return default
    teacher_icon = _icon_for_teacher_full_name(name)
    return teacher_icon or default


def get_icon_for_user(user) -> str:
    if not user:
        return "👤"
    if getattr(user, "is_system_account", False):
        return "🔔"
    if getattr(user, "is_superuser", False) or getattr(user, "is_admin", False):
        return "🛡️"
    if getattr(user, "is_guest", False):
        return "👀"
    full_name = str(getattr(user, "full_name", "") or "").strip()
    return get_icon_for_display_name(full_name or getattr(user, "username", ""), default="👤")
