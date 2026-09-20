#!/bin/sh
set -eu

PORT="${PORT:-8000}"

if [ -z "${JWT_SECRET:-}" ]; then
  echo "Missing required environment variable: JWT_SECRET"
  exit 1
fi

if [ -z "${DATABASE_URL:-}" ] && [ -z "${POSTGRES_CONNECTION_STRING:-}" ] && [ -z "${POSTGRES_URL:-}" ]; then
  echo "Missing required database environment variable: set DATABASE_URL or POSTGRES_CONNECTION_STRING"
  exit 1
fi

uv run --no-sync python - <<'PY'
import os

from app.core.config import settings

print(f"Starting {settings.app_env} API on port {os.getenv('PORT', '8000')}")
print("Database configuration loaded")
PY

attempt=1
max_attempts="${MIGRATION_MAX_ATTEMPTS:-30}"

until uv run --no-sync alembic upgrade head; do
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "Database migration failed after $attempt attempts"
    exit 1
  fi
  echo "Database migration failed, retrying in 2 seconds ($attempt/$max_attempts)"
  attempt=$((attempt + 1))
  sleep 2
done

exec uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
