# DIP (TRS - Teacher Replacement System)

Система управления заменами преподавателей: календарь замен, коммуникации, отчеты и админ-потоки.

## Стек технологий

- Python 3.12
- Django
- PostgreSQL
- Redis + Celery
- Docker / Docker Compose
- Nginx (production)

## Структура проекта

- `teacher_replacement/` - конфигурация Django, URL, celery, health-check
- `replacements/` - бизнес-логика замен, расписания, статистика, шаблоны
- `communications/` - чаты, тикеты, уведомления
- `accounts/` - пользователи, роли, доступы
- `deploy/` - инфраструктурные конфиги
- `scripts/` - утилиты обслуживания
- `docs/` - документация

## Установка зависимостей

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Настройка `.env`

1. Создать файл из примера:
```powershell
Copy-Item .env.example .env
```
2. Проверить обязательные переменные:
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`

## Запуск проекта

Локально:

```powershell
python manage.py migrate
python manage.py runserver 127.0.0.1:8001
```

Через Docker:

```powershell
docker compose up -d --build
```

## Работа с PostgreSQL

- Основные параметры берутся из `.env`.
- Бэкап (созданный дамп хранится в `backups/`):
  - `dip_backup_YYYY-MM-DD_HH-MM.sql`
- Восстановление:
```powershell
docker exec -i dip-db-1 psql -U postgres -d teacher_replacement < .\backups\<dump_file>.sql
```

## Миграции

```powershell
python manage.py makemigrations
python manage.py migrate
```

Docker:

```powershell
docker compose exec web python manage.py migrate
```

## Команды разработки

- Тесты: `python manage.py test`
- Проверка compose-конфига: `docker compose config`

## Что не должно попадать в репозиторий

- `.env`, `*.env`
- `venv/`, `env/`, `.venv*/`
- `__pycache__/`, `*.pyc`
- `.idea/`, `.vscode/`
- `node_modules/`
- `logs/`, `*.log`
- `backups/`, `*.sql`
- `*.sqlite3`
- `media/` (локальные пользовательские файлы)
- `staticfiles/` (локальный build/output)

## Деплой / дальнейшая настройка

- Production-конфигурация: `docker-compose.prod.yml`.
- Перед деплоем заполнить `.env.prod` по шаблону `.env.prod.example`.
- Проверить:
  - безопасный `DJANGO_SECRET_KEY`,
  - корректные `DJANGO_ALLOWED_HOSTS`,
  - корректные `DJANGO_CSRF_TRUSTED_ORIGINS`.
