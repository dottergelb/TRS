# Production Roadmap

## 1. Runtime

- [x] `gunicorn` + `nginx`
- [x] separate `docker-compose.prod.yml`
- [ ] object storage for media (S3/MinIO)

## 2. Data reliability

- [x] backup/restore scripts for PostgreSQL
- [ ] automated backup scheduling (cron/systemd timer)
- [ ] periodic restore drills

## 3. Code quality

- [x] CI for lint/check/tests
- [x] docker build/config validation in CI
- [ ] e2e tests for calendar/import workflows
- [ ] split `replacements/views.py` into smaller modules

## 4. Observability

- [x] liveness/readiness endpoints
- [x] Sentry integration hooks in settings
- [ ] metrics exporter (Prometheus/OpenTelemetry)

## 5. Security

- [x] production env validator script
- [x] stricter prod settings checks
- [x] rate limit for login + docx import
- [ ] secret scanning in CI

## 6. Background tasks

- [x] Celery worker/beat + Redis in prod stack
- [x] task discovery and baseline task module
- [ ] move heavy business operations to Celery tasks

## 7. Process

- [x] operations runbook
- [x] staging/prod deployment baseline
- [ ] release tags + explicit rollback playbook automation
