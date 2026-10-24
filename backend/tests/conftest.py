"""Shared test configuration."""

from __future__ import annotations

from typing import Any

import pytest

from mulenetx.core.config import Settings

BASE_ENV: dict[str, Any] = {
    "postgres_dsn": "postgresql+psycopg://mulenetx_app:test-app-secret@127.0.0.1:55432/mulenetx",
    "postgres_owner_dsn": "postgresql+psycopg://mulenetx_owner:test-owner-secret@127.0.0.1:55432/mulenetx",
    "neo4j_uri": "bolt://127.0.0.1:57687",
    "neo4j_user": "neo4j",
    "neo4j_password": "test-neo4j-secret",
    "cors_allowed_origins": ["http://localhost:8080"],
    "artifact_dir": "/tmp/mulenetx-test/artifacts",
    "staging_dir": "/tmp/mulenetx-test/staging",
    "ollama_url": "http://127.0.0.1:59999",
}


def make_settings(**overrides: Any) -> Settings:
    values = {**BASE_ENV, **overrides}
    return Settings(**values)


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture(scope="session")
def migrated_db() -> str:
    """The main test database, migrated to head once per session. Returns the app DSN."""
    from tests import dbutil

    dbutil.upgrade(dbutil.owner_dsn())
    return dbutil.app_dsn()


@pytest.fixture
def clean_db(migrated_db: str) -> str:
    from tests import dbutil

    dbutil.truncate_all()
    return migrated_db


FAST_ARGON = {"argon2_memory_kib": 8192, "argon2_time_cost": 1, "argon2_parallelism": 1}


@pytest.fixture(scope="session")
def neo4j_schema() -> None:
    from mulenetx.graph.neo4j_client import Neo4jClient

    client = Neo4jClient(BASE_ENV["neo4j_uri"], BASE_ENV["neo4j_user"], BASE_ENV["neo4j_password"])
    client.create_schema()
    client.close()


@pytest.fixture
def clean_graph(neo4j_schema: None) -> None:
    from mulenetx.graph.neo4j_client import Neo4jClient

    client = Neo4jClient(BASE_ENV["neo4j_uri"], BASE_ENV["neo4j_user"], BASE_ENV["neo4j_password"])
    while client.run("MATCH (n) WITH n LIMIT 10000 DETACH DELETE n RETURN count(*) AS n")[0]["n"]:
        pass
    client.close()


@pytest.fixture
def app(clean_db: str, clean_graph: None) -> Any:
    from mulenetx.main import create_app

    return create_app(make_settings(postgres_dsn=clean_db, **FAST_ARGON))


@pytest.fixture
def client(app: Any) -> Any:
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


@pytest.fixture
def users(app: Any) -> Any:
    """Factory: users(role) -> Actor with a logged-in bearer token."""
    from tests.apiutil import UserFactory

    return UserFactory(app)


@pytest.fixture(autouse=True, scope="session")
def _clean_test_staging() -> Any:
    """Staged uploads of queued INGEST jobs are never consumed in tests; remove them before and after."""
    import shutil

    shutil.rmtree(BASE_ENV["staging_dir"], ignore_errors=True)
    yield
    shutil.rmtree(BASE_ENV["staging_dir"], ignore_errors=True)
