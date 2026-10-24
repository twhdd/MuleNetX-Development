"""Community endpoints (SRS §19.2)."""

import pytest

from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration
TWO_GROUPS = [
    ("CA", "CB", 100.0, 1),
    ("CB", "CC", 100.0, 2),
    ("CC", "CA", 100.0, 3),
    ("CX", "CY", 100.0, 1),
    ("CY", "CZ", 100.0, 2),
    ("CZ", "CX", 100.0, 3),
    ("CC", "CX", 1.0, 4),
]


def test_communities_list_detail_and_account(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, TWO_GROUPS, key="cm")
    listing = client.get("/api/v1/communities", headers=admin.headers).json()
    assert listing["total"] == 2 and all(c["member_count"] == 3 for c in listing["items"])
    assert {"lineage", "is_stale", "page", "total_is_capped"} <= set(listing)
    cid = listing["items"][0]["community_id"]
    detail = client.get(f"/api/v1/communities/{cid}", params={"page_size": 2}, headers=admin.headers).json()
    assert detail["members"]["total"] == 3 and len(detail["members"]["items"]) == 2
    assert "not evidence" in detail["interpretation"]
    mine = client.get("/api/v1/accounts/cm:CA/community", headers=admin.headers).json()
    assert {m["account_id"] for m in mine["members"]["items"]} == {"cm:CA", "cm:CB", "cm:CC"}
    assert client.get("/api/v1/communities/nope", headers=admin.headers).status_code == 404
    assert client.get("/api/v1/communities", params={"page_size": 101}, headers=admin.headers).status_code == 400
