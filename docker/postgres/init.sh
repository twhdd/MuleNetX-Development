#!/usr/bin/env bash
# Creates the two database roles of SRS §6.5 (owner for migrations, app for backend/worker).
# Runs once from docker-entrypoint-initdb.d as the postgres superuser.
set -euo pipefail
: "${MULENETX_OWNER_PASSWORD:?MULENETX_OWNER_PASSWORD is required}"
: "${MULENETX_APP_PASSWORD:?MULENETX_APP_PASSWORD is required}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v owner_pw="$MULENETX_OWNER_PASSWORD" -v app_pw="$MULENETX_APP_PASSWORD" <<'SQL'
CREATE ROLE mulenetx_owner LOGIN PASSWORD :'owner_pw';
CREATE ROLE mulenetx_app LOGIN PASSWORD :'app_pw';
SELECT format('ALTER DATABASE %I OWNER TO mulenetx_owner', current_database()) \gexec
ALTER SCHEMA public OWNER TO mulenetx_owner;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO mulenetx_app;
SELECT format('GRANT CONNECT ON DATABASE %I TO mulenetx_app', current_database()) \gexec
-- New tables created by the owner are readable and writable by the app role; migration 0006
-- revokes UPDATE/DELETE on the append-only tables (SRS §6.5(1)).
ALTER DEFAULT PRIVILEGES FOR ROLE mulenetx_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO mulenetx_app;
ALTER DEFAULT PRIVILEGES FOR ROLE mulenetx_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO mulenetx_app;
SQL
