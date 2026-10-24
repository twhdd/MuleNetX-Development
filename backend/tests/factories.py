"""Raw-SQL row factories for every SRS §6.3 table.

`Fresh.make(table)` inserts a valid row whose primary key and unique columns are new and whose parent
rows are created fresh as well, so two rows made by the factory never collide. Used by the schema
constraint tests (AT-OPS-06).
"""

from __future__ import annotations

import itertools
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

TS = datetime(2020, 1, 1, 10, tzinfo=UTC)
Row = dict[str, Any]
_COUNTER = itertools.count(1)


class Fresh:
    def __init__(self, conn: psycopg.Connection[Any]) -> None:
        self.conn = conn

    def n(self) -> int:
        return next(_COUNTER)

    def text(self, prefix: str) -> str:
        return f"{prefix}{self.n()}"

    def build(self, table: str) -> Row:
        """A fresh valid row (parents inserted, row itself not inserted)."""
        return FACTORIES[table](self)

    def make(self, table: str, **overrides: Any) -> Row:
        row = self.build(table)
        row.update(overrides)
        insert(self.conn, table, row)
        return row


def insert(conn: psycopg.Connection[Any], table: str, row: Row) -> None:
    cols = list(row)
    values = [Jsonb(v) if isinstance(v, dict | list) and not _is_array_col(table, c) else v for c, v in row.items()]
    collist = ", ".join(f'"{c}"' for c in cols)
    placeholders = ", ".join(["%s"] * len(cols))
    conn.execute(f'INSERT INTO "{table}" ({collist}) VALUES ({placeholders})', values)


def _is_array_col(table: str, col: str) -> bool:
    return table == "account_feature_values" and col in ("feature_values", "feature_states")


def _uid() -> uuid.UUID:
    return uuid.uuid4()


# ── factories ───────────────────────────────────────────────────────────────


def users(f: Fresh) -> Row:
    return {
        "user_id": _uid(),
        "username": f.text("user"),
        "password_hash": "$argon2id$placeholder",
        "role": "ANALYST",
        "is_active": True,
        "created_at": TS,
        "updated_at": TS,
    }


def auth_sessions(f: Fresh) -> Row:
    u = f.make("users")
    return {
        "session_id": _uid(),
        "token_hash": f"{f.n():064d}",
        "user_id": u["user_id"],
        "role_at_issue": "ANALYST",
        "created_at": TS,
        "last_seen_at": TS,
        "idle_expires_at": TS + timedelta(minutes=30),
        "absolute_expires_at": TS + timedelta(hours=12),
    }


def datasets(f: Fresh) -> Row:
    k = f.n()
    return {
        "dataset_id": _uid(),
        "dataset_key": f"ds{k}",
        "name": f"dataset {k}",
        "source": "fixture",
        "dataset_version": "v1",
        "schema_version": "paysim-1",
        "adapter": "paysim-v1",
        "adapter_config": {"epoch_anchor": "2020-01-01T00:00:00Z"},
        "checksum": f"{k:064d}",
        "timestamp_resolution_seconds": 3600,
        "is_synthetic_injection": False,
        "created_at": TS,
    }


def ingestion_runs(f: Fresh) -> Row:
    d = f.make("datasets")
    return {
        "ingestion_run_id": _uid(),
        "dataset_id": d["dataset_id"],
        "pipeline_version": "p1",
        "started_at": TS,
        "status": "SUCCEEDED",
        "records_seen": 0,
        "records_accepted": 0,
        "records_rejected": 0,
        "records_duplicate": 0,
        "rejection_summary": {},
    }


def accounts(f: Fresh) -> Row:
    d = f.make("datasets")
    ref = f.text("C")
    return {
        "account_id": f"{d['dataset_key']}:{ref}",
        "dataset_id": d["dataset_id"],
        "source_account_ref": ref,
        "account_type": "CUSTOMER",
    }


def _account_in(f: Fresh, dataset: Row) -> Row:
    ref = f.text("C")
    return f.make(
        "accounts",
        account_id=f"{dataset['dataset_key']}:{ref}",
        dataset_id=dataset["dataset_id"],
        source_account_ref=ref,
    )


def transactions(f: Fresh) -> Row:
    ir = f.make("ingestion_runs")
    d = {"dataset_id": ir["dataset_id"], "dataset_key": _dataset_key(f, ir["dataset_id"])}
    a = _account_in(f, d)
    b = _account_in(f, d)
    ref = f"{f.n():010d}"
    return {
        "transaction_id": f"{d['dataset_key']}:{ref}",
        "dataset_id": d["dataset_id"],
        "ingestion_run_id": ir["ingestion_run_id"],
        "source_transaction_ref": ref,
        "source_account_id": a["account_id"],
        "destination_account_id": b["account_id"],
        "amount": 10,
        "timestamp": TS,
        "transaction_type": "TRANSFER",
        "fraud_label": False,
        "source_record_hash": f"{f.n():064d}",
    }


def _dataset_key(f: Fresh, dataset_id: uuid.UUID) -> str:
    row = f.conn.execute("SELECT dataset_key FROM datasets WHERE dataset_id = %s", (dataset_id,)).fetchone()
    assert row is not None
    return str(row[0])


def audit_events(f: Fresh) -> Row:
    return {
        "event_id": _uid(),
        "action": "test",
        "resource_type": "test",
        "outcome": "SUCCESS",
        "timestamp": TS,
    }


def dataset_profiles(f: Fresh) -> Row:
    d = f.make("datasets")
    return {"dataset_id": d["dataset_id"], "profile_version": "1", "metrics": {}, "created_at": TS}


def graph_snapshots(f: Fresh) -> Row:
    ir = f.make("ingestion_runs")
    return {
        "graph_snapshot_id": _uid(),
        "dataset_id": ir["dataset_id"],
        "ingestion_run_id": ir["ingestion_run_id"],
        "purpose": "OPERATIONAL",
        "data_cutoff": TS,
        "pipeline_version": "p1",
        "graph_schema_version": "g1",
        "source_record_count": 0,
        "status": "READY",
        "created_at": TS,
    }


def analytics_runs(f: Fresh) -> Row:
    g = f.make("graph_snapshots")
    return {
        "analytics_run_id": _uid(),
        "graph_snapshot_id": g["graph_snapshot_id"],
        "analytics_version": "nx-v1",
        "engine": "NETWORKX",
        "algorithm_configuration": {},
        "started_at": TS,
        "status": "SUCCEEDED",
    }


def feature_versions(f: Fresh) -> Row:
    k = f.n()
    return {
        "feature_version": f"fv{k}",
        "definition_hash": f"{k:064d}",
        "feature_count": 42,
        "feature_registry_reference": "features/registry_v1.json",
        "created_at": TS,
    }


def model_versions(f: Fresh) -> Row:
    fv = f.make("feature_versions")
    d = f.make("datasets")
    return {
        "model_version": f.text("model"),
        "model_type": "xgboost",
        "target_definition": {},
        "feature_version": fv["feature_version"],
        "feature_regime": "RISK_FEATURES_UNAVAILABLE",
        "training_dataset_id": d["dataset_id"],
        "training_snapshot_ids": {},
        "split_boundaries": {},
        "training_config": {},
        "class_distribution": {},
        "evaluation_metrics": {},
        "operating_threshold": 0.5,
        "artifact_reference": "x/model.json",
        "artifact_sha256": f"{f.n():064d}",
        "implementation_version": "test",
        "random_seed": 42,
        "created_at": TS,
    }


def risk_logic_versions(f: Fresh) -> Row:
    return {
        "risk_logic_version": f.text("rl"),
        "formula_identifier": "weighted-normalized-v1",
        "configuration": {},
        "normalization_reference": {},
        "rules": {},
        "tier_thresholds": {},
        "propagation_parameters": {},
        "ring_parameters": {},
        "created_at": TS,
    }


def scoring_runs(f: Fresh) -> Row:
    ar = f.make("analytics_runs")
    fv = f.make("feature_versions")
    m = f.make("model_versions")
    rl = f.make("risk_logic_versions")
    return {
        "scoring_run_id": _uid(),
        "graph_snapshot_id": ar["graph_snapshot_id"],
        "analytics_run_id": ar["analytics_run_id"],
        "as_of": TS,
        "feature_version": fv["feature_version"],
        "feature_snapshot_id": _uid(),
        "model_version": m["model_version"],
        "risk_logic_version": rl["risk_logic_version"],
        "started_at": TS,
        "status": "RUNNING",
    }


def pipeline_runs(f: Fresh) -> Row:
    d = f.make("datasets")
    return {
        "pipeline_run_id": _uid(),
        "dataset_id": d["dataset_id"],
        "current_state": "CREATED",
        "started_at": TS,
        "updated_at": TS,
    }


def jobs(f: Fresh) -> Row:
    return {
        "job_id": _uid(),
        "kind": "INGEST",
        "payload": {},
        "status": "QUEUED",
        "attempts": 0,
        "max_attempts": 3,
        "created_at": TS,
    }


def active_context(f: Fresh) -> Row:
    return {"singleton": True, "updated_at": TS}


def communities(f: Fresh) -> Row:
    ar = f.make("analytics_runs")
    return {
        "community_id": f.text("comm"),
        "analytics_run_id": ar["analytics_run_id"],
        "graph_snapshot_id": ar["graph_snapshot_id"],
        "algorithm": "louvain",
        "algorithm_version": "networkx-3",
        "member_count": 1,
        "computed_at": TS,
    }


def community_memberships(f: Fresh) -> Row:
    c = f.make("communities")
    a = f.make("accounts")
    return {"analytics_run_id": c["analytics_run_id"], "community_id": c["community_id"], "account_id": a["account_id"]}


def account_graph_metrics(f: Fresh) -> Row:
    c = f.make("communities")
    a = f.make("accounts")
    return {
        "analytics_run_id": c["analytics_run_id"],
        "account_id": a["account_id"],
        "degree": 1,
        "in_degree": 0,
        "out_degree": 1,
        "pagerank_raw": 0.1,
        "pagerank_norm": 0.5,
        "betweenness_raw": 0.0,
        "component_id": a["account_id"],
        "component_size": 1,
        "community_id": c["community_id"],
        "community_size": 1,
    }


def account_feature_values(f: Fresh) -> Row:
    ar = f.make("analytics_runs")
    fv = f.make("feature_versions")
    a = f.make("accounts")
    return {
        "feature_snapshot_id": _uid(),
        "account_id": a["account_id"],
        "as_of": TS,
        "feature_version": fv["feature_version"],
        "graph_snapshot_id": ar["graph_snapshot_id"],
        "analytics_run_id": ar["analytics_run_id"],
        "feature_values": [1.0, 2.0],
        "feature_states": [0, 1],
        "created_at": TS,
    }


def risk_assessments(f: Fresh) -> Row:
    afv = f.make("account_feature_values")
    s = f.make(
        "scoring_runs",
    )
    return {
        "assessment_id": _uid(),
        "scoring_run_id": s["scoring_run_id"],
        "account_id": afv["account_id"],
        "as_of": TS,
        "graph_snapshot_id": afv["graph_snapshot_id"],
        "feature_snapshot_id": afv["feature_snapshot_id"],
        "model_version": s["model_version"],
        "feature_version": afv["feature_version"],
        "analytics_version": "nx-v1",
        "risk_logic_version": s["risk_logic_version"],
        "ml_score": 0.1,
        "graph_signal_score": 0.1,
        "behavioral_signal_score": 0.1,
        "rule_signal_score": 0,
        "pre_propagation_score": 0.1,
        "propagated_risk": 0,
        "final_score": 0.1,
        "risk_tier": "LOW",
        "signal_availability": {},
        "fired_rules": [],
        "generated_at": TS,
    }


def propagation_contributions(f: Fresh) -> Row:
    ra = f.make("risk_assessments")
    src = f.make("accounts")
    return {
        "scoring_run_id": ra["scoring_run_id"],
        "account_id": ra["account_id"],
        "source_account_id": src["account_id"],
        "source_assessment_id": ra["assessment_id"],
        "distance": 1,
        "source_score": 0.6,
        "decay_value": 0.5,
        "contribution": 0.3,
        "rank": 1,
    }


def shap_explanations(f: Fresh) -> Row:
    ra = f.make("risk_assessments")
    return {
        "assessment_id": ra["assessment_id"],
        "model_version": ra["model_version"],
        "feature_version": ra["feature_version"],
        "explainer": "tree_shap_path_dependent",
        "base_value": 0.0,
        "output_space": "LOG_ODDS",
        "contributions": [],
        "computed_at": TS,
    }


def potential_fraud_ring_candidates(f: Fresh) -> Row:
    c = f.make("communities")
    s = f.make("scoring_runs")
    return {
        "candidate_id": _uid(),
        "community_id": c["community_id"],
        "analytics_run_id": c["analytics_run_id"],
        "graph_snapshot_id": c["graph_snapshot_id"],
        "scoring_run_id": s["scoring_run_id"],
        "candidate_score": 0.8,
        "candidate_class": "POTENTIAL_FRAUD_RING_CANDIDATE",
        "signal_summary": {},
        "candidate_status": "CANDIDATE",
        "analytics_version": "nx-v1",
        "risk_logic_version": s["risk_logic_version"],
        "created_at": TS,
    }


def ring_memberships(f: Fresh) -> Row:
    r = f.make("potential_fraud_ring_candidates")
    a = f.make("accounts")
    return {"ring_id": r["candidate_id"], "account_id": a["account_id"]}


def ring_feature_sets(f: Fresh) -> Row:
    r = f.make("potential_fraud_ring_candidates")
    return {
        "ring_feature_set_id": _uid(),
        "ring_id": r["candidate_id"],
        "analytics_run_id": r["analytics_run_id"],
        "community_id": r["community_id"],
        "graph_snapshot_id": r["graph_snapshot_id"],
        "scoring_run_id": r["scoring_run_id"],
        "analytics_version": "nx-v1",
        "feature_version": "ring-v1",
        "ring_size": 3,
        "transaction_count": 0,
        "temporal_span_seconds": 0,
        "suspicious_transaction_density": 0,
        "risk_concentration": 0,
        "temporal_coordination": 0,
        "money_flow_concentration": 0,
        "centrality_signal": 0,
        "fan_in_signal": 0,
        "fan_out_signal": 0,
        "cycle_presence": 0,
        "suspicious_path_density": 0,
        "eligible_path_count": 0,
        "qualifying_path_count": 0,
        "paths_truncated": False,
        "availability": {},
        "computed_at": TS,
    }


def ring_risk_assessments(f: Fresh) -> Row:
    fs = f.make("ring_feature_sets")
    rl = f.make("risk_logic_versions")
    return {
        "ring_risk_assessment_id": _uid(),
        "ring_id": fs["ring_id"],
        "feature_set_id": fs["ring_feature_set_id"],
        "scoring_run_id": fs["scoring_run_id"],
        "member_risk": 0.5,
        "transaction_risk": 0.5,
        "topology_signal": 0.5,
        "temporal_signal": 0.5,
        "money_flow_signal": 0.5,
        "ring_risk_score": 0.5,
        "risk_tier": "HIGH",
        "availability": {},
        "risk_logic_version": rl["risk_logic_version"],
        "analytics_version": "nx-v1",
        "feature_version": "ring-v1",
        "generated_at": TS,
    }


def temporal_motifs(f: Fresh) -> Row:
    ar = f.make("analytics_runs")
    a = f.make("accounts")
    return {
        "motif_id": _uid(),
        "analytics_run_id": ar["analytics_run_id"],
        "graph_snapshot_id": ar["graph_snapshot_id"],
        "motif_type": "FAN_IN",
        "anchor_account_id": a["account_id"],
        "start_time": TS,
        "end_time": TS,
        "temporal_window_seconds": 3600,
        "participating_account_ids": [a["account_id"]],
        "participating_transaction_ids": ["x:1"],
        "transaction_count": 1,
        "motif_confidence": 0.9,
        "order_ambiguous": False,
        "evidence": {},
        "analytics_version": "nx-v1",
        "computed_at": TS,
    }


def intervention_scenarios(f: Fresh) -> Row:
    r = f.make("potential_fraud_ring_candidates")
    u = f.make("users")
    j = f.make("jobs")
    return {
        "scenario_id": _uid(),
        "mode": "RANK",
        "target_ring_id": r["candidate_id"],
        "baseline_graph_snapshot_id": r["graph_snapshot_id"],
        "scoring_run_id": r["scoring_run_id"],
        "ranking_configuration": {},
        "ranking_configuration_hash": f"{f.n():064d}",
        "analytics_version": "nx-v1",
        "risk_logic_version": r["risk_logic_version"],
        "requested_by": u["user_id"],
        "job_id": j["job_id"],
        "status": "QUEUED",
        "created_at": TS,
    }


def intervention_candidates(f: Fresh) -> Row:
    sc = f.make("intervention_scenarios")
    return {
        "candidate_id": _uid(),
        "scenario_id": sc["scenario_id"],
        "operation_type": "ACCOUNT_REMOVAL",
        "target_ids": ["x"],
        "residual_suspicious_flow": 0,
        "flow_disruption": 0,
        "flow_disruption_percentage": 0,
        "residual_suspicious_paths": 0,
        "normalized_path_disruption": 0,
        "residual_reachable_suspicious_pairs": 0,
        "normalized_connectivity_disruption": 0,
        "residual_risk_mass": 0,
        "residual_network_risk": 0,
        "normalized_risk_reduction": 0,
        "intervention_cost": 1,
        "normalized_intervention_cost": 0.3333333,
        "intervention_score": 0,
        "rank_position": f.n(),
        "affected_account_ids": [],
        "affected_path_ids": [],
        "alternative_path_ids": [],
        "unavailable_metrics": [],
        "evidence": {},
        "created_at": TS,
    }


def cases(f: Fresh) -> Row:
    u = f.make("users")
    return {
        "case_id": _uid(),
        "title": "case",
        "status": "OPEN",
        "priority": "LOW",
        "created_by": u["user_id"],
        "created_at": TS,
        "updated_at": TS,
        "version": 1,
    }


def case_subjects(f: Fresh) -> Row:
    c = f.make("cases")
    return {
        "case_id": c["case_id"],
        "subject_type": "ACCOUNT",
        "subject_id": f.text("ds:C"),
        "added_by": c["created_by"],
        "added_at": TS + timedelta(seconds=f.n()),
    }


def findings(f: Fresh) -> Row:
    c = f.make("cases")
    return {
        "finding_id": _uid(),
        "case_id": c["case_id"],
        "type": "NOTE",
        "description": "finding",
        "evidence": [],
        "source": "investigator",
        "created_by": c["created_by"],
        "created_at": TS,
    }


def evaluation_runs(f: Fresh) -> Row:
    s = f.make("scoring_runs")
    d = f.make("datasets")
    return {
        "evaluation_run_id": _uid(),
        "dataset_id": d["dataset_id"],
        "model_version": s["model_version"],
        "test_snapshot_id": s["graph_snapshot_id"],
        "scoring_run_id": s["scoring_run_id"],
        "analytics_version": "nx-v1",
        "risk_logic_version": s["risk_logic_version"],
        "reference_construction_version": "refring-v1",
        "configuration": {},
        "status": "QUEUED",
        "created_at": TS,
    }


def evaluation_metrics(f: Fresh) -> Row:
    e = f.make("evaluation_runs")
    return {
        "evaluation_run_id": e["evaluation_run_id"],
        "level": "ACCOUNT",
        "metric": f.text("metric"),
        "value": 0.5,
        "sample_count": 10,
        "availability": "AVAILABLE",
    }


FACTORIES: dict[str, Callable[[Fresh], Row]] = {
    name: fn
    for name, fn in globals().items()
    if callable(fn)
    and not name.startswith("_")
    and name not in {"insert", "Fresh", "Callable", "Row"}
    and getattr(fn, "__module__", None) == __name__
    and name.islower()
}
