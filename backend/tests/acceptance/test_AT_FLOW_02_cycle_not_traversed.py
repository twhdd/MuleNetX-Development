"""AT-FLOW-02: with an A→B→A cycle, paths never repeat an account."""

import pytest

from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration


def test_AT_FLOW_02_cycle_not_traversed(app, client, users) -> None:
    admin = users("ADMIN")
    edges = [("CA", "CB", 1.0, 1), ("CB", "CA", 1.0, 2), ("CB", "CC", 1.0, 3), ("CC", "CA", 1.0, 4)]
    seed_and_activate(app, client, admin, edges, key="f2")
    for mode in ("ALL", "SHORTEST"):
        body = client.get(
            "/api/v1/graph/path",
            params={"source_account_id": "f2:CA", "destination_account_id": "f2:CC", "mode": mode},
            headers=admin.headers,
        ).json()
        assert [p["accounts"] for p in body["paths"]] == [["f2:CA", "f2:CB", "f2:CC"]]
        assert all(len(set(p["accounts"])) == len(p["accounts"]) for p in body["paths"])
    same = client.get(
        "/api/v1/graph/path",
        params={"source_account_id": "f2:CA", "destination_account_id": "f2:CA"},
        headers=admin.headers,
    )
    assert same.status_code == 400 and same.json()["error"]["code"] == "INVALID_PATH_REQUEST"
