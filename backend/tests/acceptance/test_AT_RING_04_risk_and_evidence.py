"""AT-RING-04: ring risk components, score, tier, evidence and lineage; no criminality claim (§9A.3–§9A.6)."""

from mulenetx.rings import evidence
from mulenetx.rings.service import intelligence
from tests.ringutil import inputs, load

EXP = load()["expected_ring"]
VERSIONS = {
    "analytics_version": "nx-test",
    "feature_version": "ring-features-v1",
    "risk_logic_version": "rl-test",
    "model_version": "xgb-test",
    "scoring_run_id": "run",
    "graph_snapshot_id": "snap",
}


def test_AT_RING_04_risk() -> None:
    ctx = inputs()
    r = intelligence(ctx, ctx.communities["c-ring"]).risk
    assert {k: format(v, "f") for k, v in r.components.items()} == EXP["risk"]
    assert format(r.score, "f") == EXP["ring_risk_score"] and r.tier == EXP["risk_tier"]
    assert r.temporal_indicators == EXP["temporal_indicators"]
    assert all(v == "AVAILABLE" for v in r.availability.values())


def test_AT_RING_04_evidence_reconstructs_the_assessment() -> None:
    ctx = inputs()
    ring = intelligence(ctx, ctx.communities["c-ring"])
    ev = evidence.build(ctx, ring.membership, ring.features, ring.risk, VERSIONS)
    assert [a["account_id"] for a in ev["accounts"]] == EXP["members"]
    assert [t["transaction_id"] for t in ev["transactions"]] == EXP["constituent"]
    assert len(ev["paths"]) == EXP["qualifying_path_count"] and all(p["path_id"] for p in ev["paths"])
    assert ev["components"] == EXP["risk"] and ev["ring_risk_score"] == EXP["ring_risk_score"]
    assert ev["versions"] == VERSIONS
    assert {m["motif_type"] for m in ev["motifs"] if m["all_accounts_in_ring"]} == {
        "RAPID_PASS_THROUGH",
        "CIRCULAR_FLOW",
    }
    # reconstruct the score from the evidence alone
    from decimal import Decimal

    weights = {
        "member_risk": "0.25",
        "transaction_risk": "0.20",
        "topology_signal": "0.20",
        "temporal_signal": "0.20",
        "money_flow_signal": "0.15",
    }
    total = sum(Decimal(weights[k]) * Decimal(v) for k, v in ev["components"].items())
    assert total.quantize(Decimal("0.0000001")) == Decimal(ev["ring_risk_score"])
    text = str(ev).lower()
    assert "not a confirmed criminal organisation" in text
    for claim in ("is a fraud ring", "criminal network", "money launderer", "guilty"):
        assert claim not in text
