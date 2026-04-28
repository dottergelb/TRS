#!/bin/sh
set -eu

exec celery -A teacher_replacement worker \
  --loglevel="${CELERY_LOG_LEVEL:-INFO}" \
  --concurrency="${CELERY_CONCURRENCY:-2}"
