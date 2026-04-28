# Operations Runbook

## Environments

- `dev`: `docker-compose.yml`
- `staging/prod`: `docker-compose.prod.yml` with separate `.env` and data volumes

## Deploy

1. Pull latest code.
2. Update `.env` (secrets, hosts, ports).
3. Build and run:
   - `docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build`
4. Verify:
   - `/health/live/`
   - `/health/ready/`

## Rollback

1. Stop current stack:
   - `docker compose --env-file .env.prod -f docker-compose.prod.yml down`
2. Start previous image/tag stack.
3. If data-level rollback required:
   - restore DB from backup via `scripts/restore_postgres.sh`.

## Database backup policy (recommended)

- Full backup every night.
- Keep daily backups 14 days.
- Keep weekly backups 8 weeks.
- Test restore at least once per month.

## Incident quick triage

1. Check container status:
   - `docker compose -f docker-compose.prod.yml ps`
2. Check logs:
   - `docker compose --env-file .env.prod -f docker-compose.prod.yml logs web --tail 200`
   - `docker compose --env-file .env.prod -f docker-compose.prod.yml logs nginx --tail 200`
   - `docker compose --env-file .env.prod -f docker-compose.prod.yml logs celery_worker --tail 200`
3. Check health endpoints.
4. If unavailable > 5 min, rollback.
