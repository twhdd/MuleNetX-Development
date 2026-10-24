"""AT-OPS-04: rerunning the pipeline on identical inputs with fixed versions gives identical deterministic
identifiers (snapshot, communities) and identical scores to 7 dp (OQ-37 explains which IDs are run-scoped)."""

import pytest
from sqlalchemy import text

from mulenetx.api.deps import get_services
from tests.apiutil import _Req
from tests.ingestutil import run_worker, seed_synth_and_activate

pytestmark = pytest.mark.integration


def test_AT_OPS_04_rerun_identical(app, client, users) -> None:
    admin = users("ADMIN")
    ds, first = seed_synth_and_activate(app, client, admin, key="op4")
    run_id = client.post(
        "/api/v1/pipeline-runs", json={"dataset_id": str(ds.dataset_id)}, headers=admin.headers
    ).json()["pipeline_run_id"]
    run_worker(app, timeout=600)
    second = client.get(f"/api/v1/pipeline-runs/{run_id}", headers=admin.headers).json()
    assert second["current_state"] == "READY"
    assert second["graph_snapshot_id"] == first["graph_snapshot_id"]
    assert second["analytics_run_id"] != first["analytics_run_id"]
    assert second["model_version"] == first["model_version"]
    rt = get_services(_Req(app)).runtime
    with rt.engine.connect() as conn:

        def communities(run):  # type: ignore[no-untyped-def]
            return {
                r[0]: r[1]
                for r in conn.execute(
                    text("SELECT community_id, member_count FROM communities WHERE analytics_run_id = :r"), {"r": run}
                )
            }

        def scores(run):  # type: ignore[no-untyped-def]
            return {
                r.account_id: (
                    r.ml_score,
                    r.graph_signal_score,
                    r.behavioral_signal_score,
                    r.rule_signal_score,
                    r.pre_propagation_score,
                    r.propagated_risk,
                    r.final_score,
                    r.risk_tier,
                )
                for r in conn.execute(text("SELECT * FROM risk_assessments WHERE scoring_run_id = :r"), {"r": run})
            }

        def features(run):  # type: ignore[no-untyped-def]
            return {
                r.account_id: (list(r.feature_values), list(r.feature_states))
                for r in conn.execute(
                    text(
                        "SELECT account_id, feature_values, feature_states FROM account_feature_values "
                        "WHERE analytics_run_id = "
                        ":r AND graph_snapshot_id = :s"
                    ),
                    {"r": run, "s": first["graph_snapshot_id"]},
                )
            }

        def motifs(run):  # type: ignore[no-untyped-def]
            return {
                (r.motif_id, r.motif_type, r.motif_confidence)
                for r in conn.execute(
                    text(
                        "SELECT m.motif_id, m.motif_type, m.motif_confidence FROM temporal_motifs m "
                        "JOIN analytics_runs a ON a.graph_snapshot_id = m.graph_snapshot_id "
                        "AND a.analytics_version = m.analytics_version WHERE a.analytics_run_id = :r"
                    ),
                    {"r": run},
                )
            }

        m1, m2 = motifs(first["analytics_run_id"]), motifs(second["analytics_run_id"])
        c1, c2 = communities(first["analytics_run_id"]), communities(second["analytics_run_id"])
        s1, s2 = scores(first["scoring_run_id"]), scores(second["scoring_run_id"])
        f1, f2 = features(first["analytics_run_id"]), features(second["analytics_run_id"])
    assert c1 == c2 and len(c1) > 1
    assert m1 == m2 and len(m1) > 0
    assert s1.keys() == s2.keys() and len(s1) > 100
    assert s1 == s2
    assert f1.keys() == f2.keys()
    for acc in f1:
        a, b = f1[acc], f2[acc]
        assert a[1] == b[1]
        assert all((x != x and y != y) or x == y for x, y in zip(a[0], b[0], strict=True)), acc
