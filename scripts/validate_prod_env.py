from __future__ import annotations

import os
import sys


REQUIRED_KEYS = [
    "DJANGO_SECRET_KEY",
    "DJANGO_ALLOWED_HOSTS",
    "POSTGRES_PASSWORD",
]


def main() -> int:
    errors: list[str] = []

    for key in REQUIRED_KEYS:
        value = (os.getenv(key, "") or "").strip()
        if not value:
            errors.append(f"{key} is required")

    secret = (os.getenv("DJANGO_SECRET_KEY", "") or "").strip()
    if secret in {"change-me", "unsafe-dev-key-change-me"}:
        errors.append("DJANGO_SECRET_KEY uses insecure default value")

    if errors:
        print("Production env validation failed:")
        for err in errors:
            print(f" - {err}")
        return 1

    print("Production env validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
