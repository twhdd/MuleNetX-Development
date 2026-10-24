"""Configuration fails fast on missing or default secrets (SRS §23.1, SR-15)."""

import pytest
from pydantic import ValidationError

from mulenetx.core.config import Settings
from tests.conftest import BASE_ENV, make_settings


def test_valid_settings() -> None:
    s = make_settings()
    assert s.max_page_size == 100
    assert s.job_timeout_seconds("TRAIN") == 7200


def test_missing_postgres_dsn_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("POSTGRES_DSN",):
        monkeypatch.delenv(key, raising=False)
    values = {k: v for k, v in BASE_ENV.items() if k != "postgres_dsn"}
    with pytest.raises(ValidationError):
        Settings(**values)


def test_default_neo4j_password_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(neo4j_password="neo4j")


def test_empty_db_password_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(postgres_dsn="postgresql+psycopg://mulenetx_app@h:5432/db")


def test_wildcard_cors_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(cors_allowed_origins=["*"])
