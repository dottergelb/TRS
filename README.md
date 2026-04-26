# DIP (Teacher Replacement System)

## Quick start

1. Create virtual environment and install deps:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\activate
pip install -r requirements.txt
```

2. Create `.env` from `.env.example`.

3. Run migrations and start app:

```powershell
python manage.py migrate
python manage.py runserver
```

## Settings profiles

- `DJANGO_ENV=dev` -> `teacher_replacement/settings_dev.py`
- `DJANGO_ENV=prod` -> `teacher_replacement/settings_prod.py`

Shared base settings are in `teacher_replacement/settings_base.py`.

## Security defaults

- No plaintext password export for teacher accounts.
- Logout and user deletion are POST-only + CSRF.
- Calendar/replacement API endpoints require auth and role-based access.
- Upload limits are controlled by env vars:
  - `MAX_CHAT_ATTACHMENT_SIZE`
  - `CHAT_THREAD_LIMIT`
  - `MAX_DOCX_UPLOAD_SIZE`
  - `MAX_SCHEDULE_UPLOAD_SIZE`
- Do not commit generated exports/logs with credentials or personal data.

## Tests

```powershell
python manage.py test
```

## Logging

- Request id is added by `replacements.middleware.RequestIdMiddleware`.
- Response includes `X-Request-ID`.
- Log formatter includes `rid=<request_id>`.
