"""Administrator bootstrap (SRS §22.1, §6.7): reads the environment, refuses if an ADMIN exists, stores
no plaintext password."""

import pytest
from sqlalchemy import create_engine, text

from mulenetx import cli
from mulenetx.core.config import get_settings
from tests.conftest import BASE_ENV

pytestmark = pytest.mark.integration


def _env(monkeypatch: pytest.MonkeyPatch, dsn: str, password: str) -> None:
    for key, value in BASE_ENV.items():
        if isinstance(value, str):
            monkeypatch.setenv(key.upper(), value)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:8080")
    monkeypatch.setenv("POSTGRES_DSN", dsn)
    monkeypatch.setenv("MULENETX_BOOTSTRAP_ADMIN_USERNAME", "root.admin")
    monkeypatch.setenv("MULENETX_BOOTSTRAP_ADMIN_PASSWORD", password)
    monkeypatch.setenv("ARGON2_MEMORY_KIB", "8192")
    get_settings.cache_clear()


def test_bootstrap_admin_once(monkeypatch: pytest.MonkeyPatch, clean_db: str) -> None:
    secret = "bootstrap-secret-value"
    _env(monkeypatch, clean_db, secret)
    try:
        assert cli.main(["bootstrap-admin"]) == 0
        assert cli.main(["bootstrap-admin"]) == 1  # an ADMIN exists now
        engine = create_engine(clean_db)
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT role, password_hash FROM users WHERE username='root.admin'")).all()
        engine.dispose()
        assert len(rows) == 1 and rows[0].role == "ADMIN"
        assert rows[0].password_hash.startswith("$argon2id$") and secret not in rows[0].password_hash
    finally:
        get_settings.cache_clear()
