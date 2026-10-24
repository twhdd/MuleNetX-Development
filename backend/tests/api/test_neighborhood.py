"""Bounded neighborhood ordering and truncation (SRS §19.2)."""

import pytest

from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration
ABC = [("CA", "CB", 100.0, 1), ("CB", "CC", 50.0, 2), ("CB", "CA", 1.0, 3)]


def test_neighborhood_order_and_truncation(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, ABC, key="nb")
    full = client.get(
        "/api/v1/graph/neighborhood", params={"account_id": "nb:CB", "depth": 1}, headers=admin.headers
    ).json()
    assert [n["account_id"] for n in full["nodes"]] == ["nb:CB", "nb:CA", "nb:CC"]
    assert [n["hop"] for n in full["nodes"]] == [0, 1, 1]
    assert [(e["source_account_id"], e["destination_account_id"]) for e in full["edges"]] == [
        ("nb:CA", "nb:CB"),
        ("nb:CB", "nb:CC"),
        ("nb:CB", "nb:CA"),
    ]
    assert full["edges"][0]["total_amount"] == "100.000000" and full["edges"][0]["tx_count"] == 1
    assert full["truncated"] is False and full["is_stale"] is False
    assert full["applied_limits"]["depth"] == 1

    cut = client.get(
        "/api/v1/graph/neighborhood", params={"account_id": "nb:CB", "max_nodes": 2}, headers=admin.headers
    ).json()
    assert [n["account_id"] for n in cut["nodes"]] == ["nb:CB", "nb:CA"]
    assert cut["truncated"] is True
    edge_cut = client.get(
        "/api/v1/graph/neighborhood", params={"account_id": "nb:CB", "max_edges": 1}, headers=admin.headers
    ).json()
    assert len(edge_cut["edges"]) == 1 and edge_cut["truncated"] is True

    two = client.get(
        "/api/v1/graph/neighborhood", params={"account_id": "nb:CC", "depth": 2}, headers=admin.headers
    ).json()
    assert [(n["account_id"], n["hop"]) for n in two["nodes"]] == [("nb:CC", 0), ("nb:CB", 1), ("nb:CA", 2)]


def test_unknown_account_and_snapshot(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, ABC, key="nu")
    assert (
        client.get("/api/v1/graph/neighborhood", params={"account_id": "nu:ZZ"}, headers=admin.headers).status_code
        == 404
    )
    unknown = client.get(
        "/api/v1/graph/neighborhood",
        params={"account_id": "nu:CA", "graph_snapshot_id": "00000000-0000-4000-8000-000000000001"},
        headers=admin.headers,
    )
    assert unknown.status_code == 404
