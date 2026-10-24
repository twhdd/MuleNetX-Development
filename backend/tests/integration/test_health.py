"""Liveness and readiness (SRS §26.3)."""

import pytest
from fastapi.testclient import TestClient

from mulenetx.main import create_app
from tests import dbutil
from tests.conftest import make_settings

pytestmark = pytest.mark.integration


def test_health_has_no_dependency_checks() -> None:
    app = create_app(make_settings(postgres_dsn="postgresql+psycopg://x:unreachable-pw@127.0.0.1:1/none"))
    resp = TestClient(app).get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "UP"}


def test_ready_200_with_matching_schema(clean_db: str) -> None:
    app = create_app(make_settings(postgres_dsn=clean_db))
    resp = TestClient(app).get("/ready")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["components"]["postgres"] == "UP"
    assert body["components"]["neo4j"] == "UP"
    assert body["components"]["ollama"] == "DOWN"
    assert body["components"]["worker"] == "IDLE"
    assert body["components"]["active_context"] == "IDLE"


def test_ready_503_on_schema_mismatch() -> None:
    dbutil.create_fresh_database("mulenetx_empty")
    app = create_app(make_settings(postgres_dsn=dbutil.app_dsn("mulenetx_empty")))
    resp = TestClient(app).get("/ready")
    assert resp.status_code == 503
    assert resp.json()["components"]["postgres"] in ("DOWN", "DEGRADED")


def test_ready_503_when_postgres_down() -> None:
    app = create_app(make_settings(postgres_dsn="postgresql+psycopg://x:unreachable-pw@127.0.0.1:1/none"))
    resp = TestClient(app).get("/ready")
    assert resp.status_code == 503
    assert resp.json()["components"]["postgres"] == "DOWN"


def test_ready_200_with_neo4j_down(clean_db: str) -> None:
    app = create_app(make_settings(postgres_dsn=clean_db, neo4j_uri="bolt://127.0.0.1:1"))
    resp = TestClient(app).get("/ready")
    assert resp.status_code == 200
    assert resp.json()["components"]["neo4j"] == "DOWN"
