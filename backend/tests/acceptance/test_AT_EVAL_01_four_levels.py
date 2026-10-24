"""AT-EVAL-01: an evaluation run reports transaction, account, ring and network metrics with the reference
construction and lineage; the transaction score is max(final_score(source), final_score(destination))."""

import numpy as np
import pytest
from sklearn.metrics import average_precision_score
from sqlalchemy import text

from mulenetx.api.deps import get_services
from tests.apiutil import _Req
from tests.evalutil import evaluate, metric, seed_with_ring
from tests.openapiutil import validate

pytestmark = pytest.mark.integration


def test_AT_EVAL_01_four_levels(app, client, users) -> None:
    admin = users("ADMIN")
    seed_with_ring(app, client, admin, "e1")
    s = evaluate(app, client, admin)
    validate("GET", "/api/v1/evaluation/runs/{id}", 200, s)
    assert set(s["levels"]) == {"TRANSACTION", "ACCOUNT", "RING", "NETWORK"}
    assert all(s["levels"][lvl] for lvl in s["levels"])
    lineage = s["configuration"]["lineage"]
    for key in (
        "dataset_id",
        "graph_snapshot_id",
        "scoring_run_id",
        "analytics_version",
        "feature_version",
        "model_version",
        "risk_logic_version",
    ):
        assert lineage[key], key
    assert s["reference_construction_version"] == "reference-v1" and s["dataset_profile"]

    # recompute the transaction PR-AUC independently from the stated rule
    rt = get_services(_Req(app)).runtime
    window = s["configuration"]["test_window"]
    with rt.engine.connect() as conn:
        rows = conn.execute(
            text(
                """
            SELECT t.fraud_label AS y, greatest(coalesce(a.final_score, 0), coalesce(b.final_score, 0)) AS score
            FROM transactions t
            LEFT JOIN risk_assessments a ON a.scoring_run_id = :s AND a.account_id = t.source_account_id
            LEFT JOIN risk_assessments b ON b.scoring_run_id = :s AND b.account_id = t.destination_account_id
            WHERE t.dataset_id = :d AND t."timestamp" > :lo AND t."timestamp" <= :hi AND t.fraud_label IS NOT NULL
            """
            ),
            {"s": s["scoring_run_id"], "d": s["dataset_id"], "lo": window["after"], "hi": window["until"]},
        ).all()
    y = np.array([int(r.y) for r in rows])
    score = np.array([float(r.score) for r in rows])
    pr = metric(s, "TRANSACTION", "pr_auc")
    assert pr["sample_count"] == len(rows) and pr["value"] == pytest.approx(average_precision_score(y, score))
    for lvl, name in (
        ("TRANSACTION", "roc_auc"),
        ("ACCOUNT", "pr_auc"),
        ("RING", "ring_recall"),
        ("NETWORK", "suspicious_flow_coverage"),
    ):
        assert metric(s, lvl, name)["state"] == "AVAILABLE", (lvl, name)
    level = client.get(f"/api/v1/evaluation/runs/{s['evaluation_run_id']}/account", headers=admin.headers).json()
    validate("GET", "/api/v1/evaluation/runs/{id}/{level}", 200, level)
    assert level["level"] == "ACCOUNT" and {m["metric"] for m in level["metrics"]} >= {
        "pr_auc",
        "mule_account_identity",
    }
