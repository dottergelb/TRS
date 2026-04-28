#!/bin/sh
set -eu

OUT_DIR="${1:-./backups}"
TS="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="${OUT_DIR}/postgres_${TS}.sql.gz"
ENV_FILE="${ENV_FILE:-.env.prod}"

mkdir -p "${OUT_DIR}"

docker compose --env-file "${ENV_FILE}" -f docker-compose.prod.yml exec -T db sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | gzip -9 > "${OUT_FILE}"

echo "Backup created: ${OUT_FILE}"
