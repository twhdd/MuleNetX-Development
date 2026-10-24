"""GET /accounts/{id}/motifs (SRS §19.2, §19.14): motifs detected in ANALYTICS, matched by any participating
account, with filters and limits; GET /rings/{id}/motifs answers 404 until rings exist (T34)."""

import pytest

from tests.ingestutil import seed_synth_and_activate
from tests.openapiutil import validate

pytestmark = pytest.mark.integration


def test_account_motifs(app, client, users) -> None:
    admin = users("ADMIN")
    seed_synth_and_activate(app, client, admin, key="mo")
    analyst = users("ANALYST")
    h = analyst.headers
    mule = "mo:C90000"  # receives a fraud-labelled transfer and cashes out in the same hour
    resp = client.get(f"/api/v1/accounts/{mule}/motifs", headers=h)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    validate("GET", "/api/v1/accounts/{id}/motifs", 200, body)
    assert body["total"] > 0 and "not a fraud" in body["interpretation"]
    for m in body["items"]:
        assert mule in m["participating_account_ids"]
        assert 0 <= m["motif_confidence"] <= 1 and m["detector_version"] == "motifs-v1"
        assert m["participating_account_ids"] == sorted(m["participating_account_ids"])
        assert m["transaction_count"] == len(m["participating_transaction_ids"])
    rapid = client.get(f"/api/v1/accounts/{mule}/motifs", params={"type": "RAPID_PASS_THROUGH"}, headers=h).json()
    assert rapid["total"] > 0 and {m["motif_type"] for m in rapid["items"]} == {"RAPID_PASS_THROUGH"}
    # PaySim-style hourly steps: a same-hour pass-through has equal timestamps → order_ambiguous
    assert all(m["order_ambiguous"] for m in rapid["items"] if m["start_time"] == m["end_time"])
    window = {"start": "2000-01-01T00:00:00Z", "end": "2000-01-02T00:00:00Z"}
    assert client.get(f"/api/v1/accounts/{mule}/motifs", params=window, headers=h).json()["total"] == 0


@pytest.mark.parametrize(
    ("params", "status", "code"),
    [
        ({"type": "NOPE"}, 400, "VALIDATION_ERROR"),
        ({"start": "2020-02-01T00:00:00Z", "end": "2020-01-01T00:00:00Z"}, 400, "VALIDATION_ERROR"),
        ({"start": "yesterday"}, 400, "VALIDATION_ERROR"),
        ({"page_size": 101}, 400, "LIMIT_EXCEEDED"),
    ],
)
def test_account_motifs_invalid(client, users, params, status, code) -> None:
    resp = client.get("/api/v1/accounts/x:CA/motifs", params=params, headers=users("ANALYST").headers)
    assert resp.status_code == status and resp.json()["error"]["code"] == code


def test_unknown_account_and_ring(client, users) -> None:
    h = users("ANALYST").headers
    assert client.get("/api/v1/accounts/nope:X/motifs", headers=h).status_code == 404
    assert client.get("/api/v1/rings/00000000-0000-4000-8000-000000000000/motifs", headers=h).status_code == 404
