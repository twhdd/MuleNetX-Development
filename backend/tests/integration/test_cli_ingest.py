"""`mulenetx ingest --path` follows the same contract as POST /api/v1/ingestion (SRS §19.2 note)."""

import json

import pytest
from sqlalchemy import create_engine, text

from mulenetx import cli
from mulenetx.core.config import get_settings
from tests.conftest import BASE_ENV
from tests.ingestutil import fixture_csv

pytestmark = pytest.mark.integration


def test_cli_ingest_registers_and_enqueues(monkeypatch: pytest.MonkeyPatch, clean_db: str, tmp_path, capsys) -> None:
    for key, value in BASE_ENV.items():
        if isinstance(value, str):
            monkeypatch.setenv(key.upper(), value)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:8080")
    monkeypatch.setenv("POSTGRES_DSN", clean_db)
    monkeypatch.setenv("STAGING_DIR", str(tmp_path / "staging"))
    get_settings.cache_clear()
    try:
        code = cli.main(
            ["ingest", "--path", str(fixture_csv("abc_chain")), "--name", "cli set", "--dataset-version", "v1"]
        )
        assert code == 0
        out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        engine = create_engine(clean_db)
        with engine.connect() as conn:
            job = conn.execute(text("SELECT kind, payload FROM jobs")).one()
        engine.dispose()
        assert job.kind == "INGEST" and job.payload["ingestion_run_id"] == out["ingestion_run_id"]
        assert job.payload["staged_path"].startswith(str(tmp_path / "staging"))
        assert (
            cli.main(
                ["ingest", "--path", str(fixture_csv("abc_chain")), "--name", "cli set", "--dataset-version", "v1"]
            )
            == 1
        )  # DATASET_ALREADY_REGISTERED
    finally:
        get_settings.cache_clear()
