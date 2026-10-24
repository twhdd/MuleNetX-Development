"""AT-GRAPH-02: with Neo4j unavailable, the neighborhood returns 503 GRAPH_UNAVAILABLE; no fabricated graph."""

import pytest
from fastapi.testclient import TestClient

from mulenetx.main import create_app
from tests.apiutil import UserFactory
from tests.conftest import FAST_ARGON, make_settings
from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration


def test_AT_GRAPH_02_neo4j_unavailable(app, client, users, clean_db) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, [("CA", "CB", 1.0, 1)], key="g2")
    down = create_app(make_settings(postgres_dsn=clean_db, neo4j_uri="bolt://127.0.0.1:1", **FAST_ARGON))
    with TestClient(down) as c:
        actor = UserFactory(down)("ANALYST")
        resp = c.get("/api/v1/graph/neighborhood", params={"account_id": "g2:CA"}, headers=actor.headers)
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "GRAPH_UNAVAILABLE"
        assert "nodes" not in resp.json()
        # relational features still work
        assert c.get("/api/v1/accounts/g2:CA", headers=actor.headers).status_code == 200
