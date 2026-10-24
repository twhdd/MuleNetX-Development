"""AT-FLOW-01: parallel A→B transactions form one topology hop; all evidence IDs are retained in order."""

import pytest

from mulenetx.core import ids
from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration


def test_AT_FLOW_01_parallel_transactions(app, client, users) -> None:
    admin = users("ADMIN")
    edges = [("CA", "CB", 10.0, 3), ("CA", "CB", 20.0, 1), ("CA", "CB", 30.0, 2), ("CB", "CC", 5.0, 4)]
    seed_and_activate(app, client, admin, edges, key="f1")
    body = client.get(
        "/api/v1/graph/path",
        params={"source_account_id": "f1:CA", "destination_account_id": "f1:CC"},
        headers=admin.headers,
    ).json()
    assert body["paths_found"] == 1
    [path] = body["paths"]
    assert path["accounts"] == ["f1:CA", "f1:CB", "f1:CC"] and path["path_length"] == 2
    hop = path["hops"][0]
    assert hop["tx_count"] == 3 and hop["transactions_total"] == 3
    # (timestamp, transaction_id) order: step 1 → tx 2, step 2 → tx 3, step 3 → tx 1
    assert hop["transactions"] == ["f1:0000000002", "f1:0000000003", "f1:0000000001"]
    assert hop["amounts"] == ["20.000000", "30.000000", "10.000000"] and hop["total_amount"] == "60.000000"
    assert path["path_id"] == str(ids.path_id(body["graph_snapshot_id"], path["accounts"]))
    assert "connectivity only" in body["statement"]
    detail = client.get(
        f"/api/v1/graph/paths/{path['path_id']}",
        params={"graph_snapshot_id": body["graph_snapshot_id"], "accounts": ",".join(path["accounts"]), "page_size": 2},
        headers=admin.headers,
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["hops"][0]["transactions"] == ["f1:0000000002", "f1:0000000003"]
    wrong = client.get(
        f"/api/v1/graph/paths/{path['path_id']}",
        params={"graph_snapshot_id": body["graph_snapshot_id"], "accounts": "f1:CA,f1:CC"},
        headers=admin.headers,
    )
    assert wrong.status_code == 404
