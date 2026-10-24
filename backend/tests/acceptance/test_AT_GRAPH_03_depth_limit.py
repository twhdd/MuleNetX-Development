"""AT-GRAPH-03: depth above the maximum → 400 LIMIT_EXCEEDED (reject, never clamp); same for node/edge caps."""

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("param", "value", "limit"),
    [("depth", 4, 3), ("max_nodes", 501, 500), ("max_edges", 2001, 2000)],
)
def test_AT_GRAPH_03_above_limit_rejected(client, users, param, value, limit) -> None:
    analyst = users("ANALYST")
    resp = client.get(
        "/api/v1/graph/neighborhood", params={"account_id": "x:CA", param: value}, headers=analyst.headers
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "LIMIT_EXCEEDED"
    assert resp.json()["error"]["details"] == {"field": param, "limit": limit}


def test_AT_GRAPH_03_zero_depth_invalid(client, users) -> None:
    analyst = users("ANALYST")
    resp = client.get("/api/v1/graph/neighborhood", params={"account_id": "x:CA", "depth": 0}, headers=analyst.headers)
    assert resp.status_code == 400 and resp.json()["error"]["code"] == "VALIDATION_ERROR"
