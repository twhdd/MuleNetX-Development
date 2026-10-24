"""Per-dataset serialization of pipeline stages with a session-level advisory lock (SRS §7.8)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, text

from mulenetx.jobs.runner import LockBusyError


@contextmanager
def dataset_lock(engine: Engine, key: int) -> Iterator[None]:
    conn = engine.connect()
    try:
        got = conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": key}).scalar()
        conn.commit()
        if not got:
            raise LockBusyError(str(key))
        try:
            yield
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": key})
            conn.commit()
    finally:
        conn.close()
