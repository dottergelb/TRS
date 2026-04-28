#!/bin/sh
set -eu

if [ $# -lt 1 ]; then
  echo "Usage: $0 <backup.sql.gz>"
  exit 1
fi

BACKUP_FILE="$1"
ENV_FILE="${ENV_FILE:-.env.prod}"
if [ ! -f "${BACKUP_FILE}" ]; then
  echo "Backup file not found: ${BACKUP_FILE}"
  exit 1
fi

gzip -dc "${BACKUP_FILE}" | docker compose --env-file "${ENV_FILE}" -f docker-compose.prod.yml exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

echo "Restore completed from: ${BACKUP_FILE}"
