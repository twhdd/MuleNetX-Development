"""Account search and profile (SRS §19.6, DEC-04)."""

import pytest

from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration
ABC = [("CA", "CB", 100.0, 1), ("CB", "CC", 50.0, 2), ("CD", "M1", 5.0, 3)]


def test_search_within_active_dataset(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, ABC, key="acc")
    analyst = users("ANALYST")
    all_accounts = client.get(
        "/api/v1/accounts", params={"sort": "account_id", "order": "asc"}, headers=analyst.headers
    ).json()
    assert all_accounts["total"] == 5
    assert [a["account_id"] for a in all_accounts["items"]] == ["acc:CA", "acc:CB", "acc:CC", "acc:CD", "acc:M1"]
    prefix = client.get("/api/v1/accounts", params={"q": "C"}, headers=analyst.headers).json()
    assert prefix["total"] == 4
    exact = client.get("/api/v1/accounts", params={"q": "CB"}, headers=analyst.headers).json()
    assert [a["source_account_ref"] for a in exact["items"]] == ["CB"]
    wildcard = client.get("/api/v1/accounts", params={"q": "%"}, headers=analyst.headers).json()
    assert wildcard["total"] == 0  # LIKE metacharacters are escaped
    merchants = client.get("/api/v1/accounts", params={"account_type": "MERCHANT"}, headers=analyst.headers).json()
    assert [a["account_id"] for a in merchants["items"]] == ["acc:M1"]


def test_search_validation(client, users) -> None:
    analyst = users("ANALYST")
    assert client.get("/api/v1/accounts", params={"risk_tier": "EXTREME"}, headers=analyst.headers).status_code == 400
    assert client.get("/api/v1/accounts", params={"sort": "password"}, headers=analyst.headers).status_code == 400
    over = client.get("/api/v1/accounts", params={"page_size": 101}, headers=analyst.headers)
    assert over.status_code == 400 and over.json()["error"]["code"] == "LIMIT_EXCEEDED"
    empty = client.get("/api/v1/accounts", headers=analyst.headers).json()
    assert empty["items"] == [] and empty["total"] == 0  # no active dataset yet


def test_account_profile(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, ABC, key="prof")
    body = client.get("/api/v1/accounts/prof:CB", headers=admin.headers).json()
    assert body["account_id"] == "prof:CB" and body["source_account_ref"] == "CB"
    assert body["dataset_key"] == "prof" and body["account_type"] == "CUSTOMER"
    assert body["is_stale"] is False and body["lineage"]["graph_snapshot_id"]
    assert set(body) >= {"risk_score", "risk_tier", "community_id", "latest_risk_assessment_id"}
    assert client.get("/api/v1/accounts/prof:NOPE", headers=admin.headers).status_code == 404
