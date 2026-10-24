"""AT-ML-02: training records the window table and passes every §11.6 leakage check, including entity
separation and label-window containment; class weight and §11.10 metrics are recorded."""

import pytest
from sqlalchemy import select

from mulenetx.api.deps import get_services
from mulenetx.db.models.lineage import GraphSnapshot, ModelVersion
from tests.apiutil import _Req
from tests.ingestutil import seed_synth_and_activate

pytestmark = pytest.mark.integration


def test_AT_ML_02_split_and_leakage(app, client, users) -> None:
    admin = users("ADMIN")
    _ds, run = seed_synth_and_activate(app, client, admin, key="ml2")
    assert run["model_version"], run
    rt = get_services(_Req(app)).runtime
    with rt.session_factory() as db:
        mv = db.get(ModelVersion, run["model_version"])
        snapshots = db.execute(select(GraphSnapshot).where(GraphSnapshot.purpose == "TRAINING_SPLIT")).scalars().all()
    assert mv is not None
    td = mv.target_definition
    assert td["target_semantics"] == "RETROSPECTIVE_DETECTION" and td["forward_horizon"] is None
    assert set(td["window_table"]) == {"train", "val", "test"}
    assert set(mv.split_boundaries) == {"T_0", "T_train", "T_val", "T_test", "resolution_seconds"}
    checks = mv.evaluation_metrics["leakage_checks"]
    assert [c["check"] for c in checks] == [
        "1_feature_event_time",
        "2_graph_snapshot_cutoff",
        "3_entity_separation",
        "4_no_label_or_balance_columns",
        "5_regime_risk_features_unavailable",
        "7_label_window_containment",
        "6_test_split_unused",
    ]
    assert all(c["passed"] for c in checks)
    dist = mv.class_distribution
    assert all(dist[s]["positive"] > 0 and dist[s]["negative"] > 0 for s in ("train", "val", "test"))
    hp = mv.training_config["hyperparameters"]
    assert (
        hp["n_estimators"],
        hp["max_depth"],
        hp["learning_rate"],
        hp["subsample"],
        hp["colsample_bytree"],
        hp["random_state"],
        hp["tree_method"],
        hp["n_jobs"],
    ) == (300, 6, 0.05, 0.8, 0.8, 42, "hist", 1)
    assert hp["early_stopping"] is None
    spw = mv.training_config["class_weight"]["scale_pos_weight"]
    assert spw == pytest.approx(dist["train"]["negative"] / dist["train"]["positive"])
    for split in ("validation", "test"):
        m = mv.evaluation_metrics[split]
        for key in (
            "prevalence",
            "precision",
            "recall",
            "f1",
            "roc_auc",
            "pr_auc",
            "pr_auc_baseline",
            "precision_at_100",
            "precision_at_top_1pct",
            "confusion_matrix",
            "false_positive_rate",
            "false_negative_rate",
        ):
            assert key in m, (split, key)
    assert 0 <= float(mv.operating_threshold) <= 1
    assert {str(s.graph_snapshot_id) for s in snapshots} == set(mv.training_snapshot_ids.values())
    assert all(s.status == "RETIRED" for s in snapshots)  # retired once training completed (§6.8.6)
    assert mv.artifact_reference.endswith(f"{mv.model_version}/model.json") and len(mv.artifact_sha256) == 64
