"""AT-FLOW-03: more than 50 paths → at most 50 results, ordered by §16.5; limits rejected; hard timeout → 408."""

import pytest
from fastapi.testclient import TestClient

from mulenetx.main import create_app
from tests.apiutil import UserFactory
from tests.conftest import FAST_ARGON, make_settings
from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration


def _fan(n: int = 60) -> list[tuple[str, str, float, int]]:
    edges = []
    for i in range(n):
        edges.append(("CS", f"CX{i:02d}", float(i + 1), 1))
        edges.append((f"CX{i:02d}", "CT", 1.0, 2))
    return edges


def test_AT_FLOW_03_result_limit_and_order(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, _fan(), key="f3")
    params = {"source_account_id": "f3:CS", "destination_account_id": "f3:CT", "mode": "ALL", "max_results": 50}
    body = client.get("/api/v1/graph/path", params=params, headers=admin.headers).json()
    assert body["paths_found"] == 60 and len(body["paths"]) == 50 and body["truncated"] is True
    totals = [float(p["total_amount"]) for p in body["paths"]]
    assert totals == sorted(totals, reverse=True)
    assert body["paths"][0]["accounts"] == ["f3:CS", "f3:CX59", "f3:CT"]  # 60 + 1 is the largest total
    over = client.get("/api/v1/graph/path", params={**params, "max_results": 51}, headers=admin.headers)
    assert over.status_code == 400 and over.json()["error"]["code"] == "LIMIT_EXCEEDED"
    deep = client.get("/api/v1/graph/path", params={**params, "max_depth": 6}, headers=admin.headers)
    assert deep.status_code == 400 and deep.json()["error"]["details"] == {"field": "max_depth", "limit": 5}
    assert (
        client.get("/api/v1/graph/path", params={**params, "mode": "WEIRD"}, headers=admin.headers).status_code == 400
    )


def test_AT_FLOW_03_hard_timeout(app, client, users, clean_db) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, _fan(), key="f3t")
    slow = create_app(make_settings(postgres_dsn=clean_db, path_query_timeout_seconds=0.000001, **FAST_ARGON))
    with TestClient(slow) as c:
        actor = UserFactory(slow)("ANALYST")
        resp = c.get(
            "/api/v1/graph/path",
            params={"source_account_id": "f3t:CS", "destination_account_id": "f3t:CT", "mode": "ALL"},
            headers=actor.headers,
        )
    assert resp.status_code == 408 and resp.json()["error"]["code"] == "QUERY_TIMEOUT"
    assert "paths" not in resp.json()
