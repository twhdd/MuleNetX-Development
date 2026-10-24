"""Alembic environment. Migrations run as the owner role (SRS §6.5(3))."""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import create_engine, pool

config = context.config


def _dsn() -> str:
    explicit = config.attributes.get("dsn")
    if isinstance(explicit, str):
        return explicit
    dsn = os.environ.get("POSTGRES_OWNER_DSN") or os.environ.get("POSTGRES_DSN")
    if not dsn:
        raise RuntimeError("POSTGRES_OWNER_DSN (or POSTGRES_DSN) is required to run migrations")
    return dsn


def run_migrations_online() -> None:
    engine = create_engine(_dsn(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("offline migrations are not supported")
run_migrations_online()
