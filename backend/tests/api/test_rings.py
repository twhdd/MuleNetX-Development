"""Ring APIs (SRS §19.2, §19.13): lists, detail, members, constituent transactions, intelligence (potential fraud
rings only), evidence, motifs and the /fraud-ring-candidates aliases."""

import pytest

from tests.openapiutil import validate
from tests.ringapi import rings_by_class

pytestmark = pytest.mark.integration


def test_ring_reads(app, client, users) -> None:
    rings = rings_by_class(app, client, users("ADMIN"), "rr")
    h = users("ANALYST").headers
    pot, sc = rings["POTENTIAL_FRAUD_RING_CANDIDATE"], rings["SUSPICIOUS_COMMUNITY"]

    listing = client.get("/api/v1/rings", headers=h).json()
    validate("GET", "/api/v1/rings", 200, listing)
    scores = [r["candidate_score"] for r in listing["items"]]
    assert scores == sorted(scores, reverse=True) and "not proof of a fraud ring" in listing["interpretation"]
    only = client.get("/api/v1/rings", params={"class": "SUSPICIOUS_COMMUNITY", "min_score": "0.6"}, headers=h).json()
    assert all(r["candidate_class"] == "SUSPICIOUS_COMMUNITY" and r["candidate_score"] >= 0.6 for r in only["items"])
    for params in ({"class": "RING"}, {"status": "OPEN"}, {"min_score": "2"}, {"min_score": "x"}, {"page_size": 101}):
        assert client.get("/api/v1/rings", params=params, headers=h).status_code == 400, params

    for ring in (pot, sc):
        rid = ring["ring_id"]
        detail = client.get(f"/api/v1/rings/{rid}", headers=h).json()
        validate("GET", "/api/v1/rings/{id}", 200, detail)
        assert detail["member_count"] >= 3 and detail["lineage"]["scoring_run_id"]
        members = client.get(f"/api/v1/rings/{rid}/accounts", headers=h).json()
        validate("GET", "/api/v1/rings/{id}/accounts", 200, members)
        assert members["total"] == detail["member_count"]
        ids = [m["account_id"] for m in members["items"]]
        assert ids == sorted(ids)
        txs = client.get(f"/api/v1/rings/{rid}/transactions", params={"page_size": 5}, headers=h).json()
        validate("GET", "/api/v1/rings/{id}/transactions", 200, txs)
        member_set = set(ids) if members["total"] <= 25 else None
        for t in txs["items"]:
            if member_set is not None:
                assert t["source_account_id"] in member_set and t["destination_account_id"] in member_set
        if txs["next_cursor"]:
            nxt = client.get(
                f"/api/v1/rings/{rid}/transactions", params={"page_size": 5, "cursor": txs["next_cursor"]}, headers=h
            ).json()
            assert not {t["transaction_id"] for t in nxt["items"]} & {t["transaction_id"] for t in txs["items"]}
        motifs = client.get(f"/api/v1/rings/{rid}/motifs", headers=h)
        assert motifs.status_code == 200

    for section in ("features", "risk", "evidence"):
        resp = client.get(f"/api/v1/rings/{sc['ring_id']}/{section}", headers=h)
        assert resp.status_code == 409 and resp.json()["error"]["code"] == "RING_INTELLIGENCE_NOT_APPLICABLE"

    feats = client.get(f"/api/v1/rings/{pot['ring_id']}/features", headers=h).json()
    validate("GET", "/api/v1/rings/{id}/features", 200, feats)
    assert [f["feature"] for f in feats["features"]] == ["RSD", "RC", "TC", "MFC", "CS", "FI", "FO", "CP", "SPD"]
    risk = client.get(f"/api/v1/rings/{pot['ring_id']}/risk", headers=h).json()
    validate("GET", "/api/v1/rings/{id}/risk", 200, risk)
    assert risk["ring_risk_score"] == pot["ring_risk_score"]
    assert abs(sum(c["value"] * c["weight"] for c in risk["components"]) - risk["ring_risk_score"]) < 1e-6
    ev = client.get(f"/api/v1/rings/{pot['ring_id']}/evidence", params={"page_size": 3}, headers=h).json()
    validate("GET", "/api/v1/rings/{id}/evidence", 200, ev)
    assert set(ev["sections"]) == {"accounts", "transactions", "relationships", "motifs", "paths"}
    assert ev["ring_risk_score"] == format(risk["ring_risk_score"], ".7f")
    paths = client.get(f"/api/v1/rings/{pot['ring_id']}/evidence", params={"section": "paths"}, headers=h).json()
    assert set(paths["sections"]) == {"paths"}
    assert paths["sections"]["paths"]["total"] == feats["qualifying_path_count"]
    assert client.get(f"/api/v1/rings/{pot['ring_id']}/evidence", params={"section": "x"}, headers=h).status_code == 400


def test_aliases(app, client, users) -> None:
    rings = rings_by_class(app, client, users("ADMIN"), "ra")
    h = users("ANALYST").headers
    target = client.get("/api/v1/rings", headers=h).json()
    alias = client.get("/api/v1/fraud-ring-candidates", headers=h)
    assert alias.headers["deprecation"] == "true" and "/api/v1/rings" in alias.headers["link"]
    assert alias.json() == target
    rid = rings["POTENTIAL_FRAUD_RING_CANDIDATE"]["ring_id"]
    one = client.get(f"/api/v1/fraud-ring-candidates/{rid}", headers=h)
    assert one.headers["deprecation"] == "true" and one.json() == client.get(f"/api/v1/rings/{rid}", headers=h).json()
