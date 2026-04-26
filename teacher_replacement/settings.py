from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    dotenv_path = Path(__file__).resolve().parent.parent / ".env"
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()


APP_ENV = str(os.getenv("DJANGO_ENV", "dev")).strip().lower()

if APP_ENV in {"prod", "production"}:
    from .settings_prod import *  # noqa: F401,F403
else:
    from .settings_dev import *  # noqa: F401,F403
