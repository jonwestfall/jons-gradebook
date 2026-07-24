#!/usr/bin/env sh
set -e

mkdir -p /data/storage /data/backups
chown -R gradebook:gradebook /data

attempt=1
max_attempts=30

while [ $attempt -le $max_attempts ]; do
  echo "Running migrations (attempt ${attempt}/${max_attempts})..."
  if gosu gradebook alembic upgrade head; then
    break
  fi

  if [ $attempt -eq $max_attempts ]; then
    echo "Migration failed after ${max_attempts} attempts"
    exit 1
  fi

  attempt=$((attempt + 1))
  sleep 2
done

exec gosu gradebook uvicorn app.main:app --host 0.0.0.0 --port 8000
