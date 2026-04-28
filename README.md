# TRS (Teacher Replacement System)

Django-проект для управления заменами учителей: календарь замен, отдельные замены, кабинеты, статистика, уведомления сотрудникам, чаты/тикеты, импорт/экспорт DOCX.

## Технологии

- Python 3.12, Django
- PostgreSQL
- Redis + Celery (worker/beat)
- Docker / Docker Compose
- Nginx (prod)

## Основные возможности

- Календарь замен с сохранением на дату
- Импорт DOCX в фоне через Celery со статусом задачи
- Экспорт отчетов DOCX
- Статистика по дню/периоду/месяцу
- Оповещения сотрудникам
- Управление учителями/специализациями
- Журнал действий (audit log)

## Локальный запуск (без Docker)

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

## Локальный запуск (Docker, dev)

```powershell
copy .env.example .env
docker compose up -d --build
```

Открыть:

- http://127.0.0.1:8001

Dev compose поднимает:

- `web`
- `db`
- `redis`
- `celery_worker`

## Production stack

Используется `docker-compose.prod.yml`:

- `web` (gunicorn)
- `nginx`
- `db` (PostgreSQL)
- `redis`
- `celery_worker`
- `celery_beat`

Запуск:

```powershell
copy .env.prod.example .env.prod
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

URL по умолчанию:

- http://127.0.0.1:8080

## Переменные окружения (ключевые)

- `DJANGO_ENV` (`dev` / `prod`)
- `DJANGO_DB_ENGINE=postgres`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `CELERY_BROKER_URL` (обычно `redis://redis:6379/0`)
- `CELERY_RESULT_BACKEND` (обычно `redis://redis:6379/1`)
- `MAX_DOCX_UPLOAD_SIZE`

## Миграции

```powershell
python manage.py migrate
```

Для Docker:

```powershell
docker compose exec web python manage.py migrate
```

## Health-check endpoints

- `/health/live/`
- `/health/ready/`

## Бэкапы PostgreSQL

```powershell
sh ./scripts/backup_postgres.sh
sh ./scripts/restore_postgres.sh ./backups/<backup_file>.sql.gz
```

## Тесты

```powershell
python manage.py test
```

## Примечания по доступу извне

Если открываете проект через туннель (например ngrok), добавьте домен туннеля в:

- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`

И перезапустите `web`.

## Структура (кратко)

- `teacher_replacement/` — settings, urls, celery, health
- `replacements/` — ядро логики замен, календарь, статистика, DOCX
- `communications/` — уведомления, чаты, тикеты
- `accounts/` — пользователи и доступы
- `deploy/nginx/` — nginx-конфиг для prod
- `scripts/` — утилиты деплоя/бэкапов/валидации
