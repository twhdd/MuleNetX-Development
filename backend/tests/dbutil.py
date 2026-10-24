"""Test database helpers (test services from docker-compose.test.yml, OQ-02)."""

from __future__ import annotations

from pathlib import Path

import psycopg
from alembic import command
from alembic.config import Config

HOST = "127.0.0.1:55432"
SUPER_DSN = f"postgresql://postgres:test-superuser-secret@{HOST}/postgres"
OWNER_PW = "test-owner-secret"
APP_PW = "test-app-secret"
BACKEND = Path(__file__).resolve().parents[1]

DB_SETUP_SQL = [
    "ALTER SCHEMA public OWNER TO mulenetx_owner",
    "REVOKE ALL ON SCHEMA public FROM PUBLIC",
    "GRANT USAGE ON SCHEMA public TO mulenetx_app",
    "ALTER DEFAULT PRIVILEGES FOR ROLE mulenetx_owner IN SCHEMA public "
    "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO mulenetx_app",
    "ALTER DEFAULT PRIVILEGES FOR ROLE mulenetx_owner IN SCHEMA public "
    "GRANT USAGE, SELECT ON SEQUENCES TO mulenetx_app",
]


def owner_dsn(db: str = "mulenetx", driver: bool = True) -> str:
    scheme = "postgresql+psycopg" if driver else "postgresql"
    return f"{scheme}://mulenetx_owner:{OWNER_PW}@{HOST}/{db}"


def app_dsn(db: str = "mulenetx", driver: bool = True) -> str:
    scheme = "postgresql+psycopg" if driver else "postgresql"
    return f"{scheme}://mulenetx_app:{APP_PW}@{HOST}/{db}"


def create_fresh_database(name: str) -> None:
    """Drop and recreate a database with the same role setup as docker/postgres/init.sh."""
    with psycopg.connect(SUPER_DSN, autocommit=True) as conn:
        conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
            (name,),
        )
        conn.execute(f'DROP DATABASE IF EXISTS "{name}"')
        conn.execute(f'CREATE DATABASE "{name}" OWNER mulenetx_owner')
        conn.execute(f'GRANT CONNECT ON DATABASE "{name}" TO mulenetx_app')
    with psycopg.connect(SUPER_DSN.rsplit("/", 1)[0] + f"/{name}", autocommit=True) as conn:
        for stmt in DB_SETUP_SQL:
            conn.execute(stmt)


def alembic_config(dsn: str) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.attributes["dsn"] = dsn
    return cfg


def upgrade(dsn: str, revision: str = "head") -> None:
    command.upgrade(alembic_config(dsn), revision)


def downgrade(dsn: str, revision: str = "base") -> None:
    command.downgrade(alembic_config(dsn), revision)


def truncate_all(db: str = "mulenetx") -> None:
    """Remove every row (owner role) and restore the active_context singleton."""
    with psycopg.connect(owner_dsn(db, driver=False), autocommit=True) as conn:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
            ).fetchall()
        ]
        if tables:
            conn.execute("TRUNCATE " + ", ".join(f'"{t}"' for t in tables) + " RESTART IDENTITY CASCADE")
        conn.execute("INSERT INTO active_context (singleton, updated_at) VALUES (TRUE, now())")
        for (name,) in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'staging'").fetchall():
            conn.execute(f'DROP TABLE IF EXISTS staging."{name}"')
