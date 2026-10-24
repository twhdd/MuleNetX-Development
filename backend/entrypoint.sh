#!/usr/bin/env bash
# Entrypoints: backend | worker | migrate | cli <args>. SRS §26.2: backend and worker refuse to start on
# a schema version mismatch.
set -euo pipefail
mode="${1:-backend}"
shift || true
case "$mode" in
  migrate)
    POSTGRES_DSN="${POSTGRES_OWNER_DSN:?POSTGRES_OWNER_DSN is required for migrate}" alembic upgrade head
    python -m mulenetx.cli migrate-neo4j
    ;;
  backend)
    python -m mulenetx.cli check-schema
    exec uvicorn mulenetx.main:app --host 0.0.0.0 --port 8000 --no-access-log "$@"
    ;;
  worker)
    python -m mulenetx.cli check-schema
    exec python -m mulenetx.worker "$@"
    ;;
  cli)
    exec python -m mulenetx.cli "$@"
    ;;
  *)
    exec "$mode" "$@"
    ;;
esac
