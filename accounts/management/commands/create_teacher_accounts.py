from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from replacements.models import Teacher


TRANSLIT_MAP = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "j",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "c",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def transliterate_ru_to_latin(value: str) -> str:
    parts: list[str] = []
    for ch in (value or ""):
        low = ch.lower()
        if low in TRANSLIT_MAP:
            t = TRANSLIT_MAP[low]
            if ch.isupper() and t:
                t = t[0].upper() + t[1:]
            parts.append(t)
        else:
            parts.append(ch)
    return "".join(parts)


def build_base_username(full_name: str) -> str:
    latin = transliterate_ru_to_latin(full_name)
    cleaned = re.sub(r"[^A-Za-z0-9]+", "", latin or "")
    if not cleaned:
        return "teacher"
    return cleaned[:140]


def make_unique_username(base: str, existing: set[str]) -> str:
    username = base
    idx = 1
    while username in existing:
        suffix = str(idx)
        username = f"{base[: max(1, 150 - len(suffix))]}{suffix}"
        idx += 1
    existing.add(username)
    return username


class Command(BaseCommand):
    help = "Creates teacher user accounts and exports CSV with full_name + username only."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            dest="output",
            default="",
            help="Output CSV path (default: ./created_teacher_accounts_<timestamp>.csv)",
        )
        parser.add_argument(
            "--with-suffix",
            action="store_true",
            dest="with_suffix",
            help="If base username exists, append numeric suffix instead of skipping.",
        )

    def handle(self, *args, **options):
        output_arg: str = options.get("output") or ""
        with_suffix: bool = bool(options.get("with_suffix"))

        User = get_user_model()
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(output_arg) if output_arg else Path.cwd() / f"created_teacher_accounts_{now}.csv"

        existing_usernames = set(User.objects.values_list("username", flat=True))
        existing_full_names = set(
            User.objects.exclude(full_name__isnull=True).exclude(full_name__exact="").values_list("full_name", flat=True)
        )

        created_rows: list[tuple[str, str]] = []
        skipped = 0

        for teacher in Teacher.objects.all().order_by("full_name"):
            full_name = (teacher.full_name or "").strip()
            if not full_name:
                skipped += 1
                continue

            if full_name in existing_full_names:
                skipped += 1
                continue

            base_username = build_base_username(full_name)
            if base_username in existing_usernames and not with_suffix:
                skipped += 1
                continue

            username = make_unique_username(base_username, existing_usernames) if with_suffix else base_username

            user = User(
                username=username,
                full_name=full_name,
                is_active=True,
                is_admin=False,
                is_teacher=True,
                is_guest=False,
                can_calendar=False,
                can_teachers=False,
                can_editor=False,
                can_upload=False,
                can_logs=False,
                can_calls=False,
                can_users=False,
            )
            user.set_unusable_password()
            user.save()

            existing_full_names.add(full_name)
            created_rows.append((full_name, username))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["full_name", "username"])
            writer.writerows(created_rows)

        self.stdout.write(self.style.SUCCESS(f"Created users: {len(created_rows)}"))
        self.stdout.write(f"Skipped: {skipped}")
        self.stdout.write("Passwords are not exported or stored in plain text.")
        self.stdout.write(f"CSV: {output_path}")
