"""Schema version check: the database's Alembic revision must equal the code's head (SRS §26.2)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, text

ALEMBIC_DIR = Path(__file__).resolve().parents[2] / "alembic"


@lru_cache(maxsize=1)
def code_head() -> str:
    cfg = Config()
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    head = ScriptDirectory.from_config(cfg).get_current_head()
    if head is None:
        raise RuntimeError("no alembic head")
    return head


def database_revision(engine: Engine) -> str | None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version")).first()
    return None if row is None else str(row[0])


def schema_matches(engine: Engine) -> bool:
    try:
        return database_revision(engine) == code_head()
    except Exception:  # noqa: BLE001 - any failure (missing table, connection) means "does not match"
        return False
