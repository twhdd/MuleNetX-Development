"""SQLAlchemy engine construction (psycopg 3)."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine


def make_engine(dsn: str, *, pool_size: int = 10) -> Engine:
    return create_engine(
        dsn,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=10,
        connect_args={"connect_timeout": 3},
    )
