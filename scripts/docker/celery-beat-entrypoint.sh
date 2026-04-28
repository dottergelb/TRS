#!/bin/sh
set -eu

exec celery -A teacher_replacement beat \
  --loglevel="${CELERY_LOG_LEVEL:-INFO}"
