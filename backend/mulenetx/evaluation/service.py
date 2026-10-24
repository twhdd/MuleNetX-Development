"""EvaluationService (SRS §28.7, §19.16): multi-level evaluation runs as EVALUATION jobs, and their read models.

Population: the test split of the model's split boundaries, scored by the active context's scoring run, whose
snapshot must have `data_cutoff = T_test` (PLAN T38 default). Labels are used here and in training only (§3.5).
"""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from mulenetx.audit.service import AuditService
from mulenetx.auth.service import Principal
from mulenetx.core import error_codes as ec
from mulenetx.core.config import Settings
from mulenetx.core.errors import AppError
from mulenetx.core.timeutil import isoformat_utc, parse_utc, utcnow
from mulenetx.db.models.evaluation import EvaluationMetric, EvaluationRun
from mulenetx.db.models.lineage import ActiveContext, GraphSnapshot, ModelVersion, ScoringRun
from mulenetx.evaluation.matching import match
from mulenetx.evaluation.metrics import (
    Row,
    average_precision,
    distribution,
    not_measurable,
    ranking_rows,
    ratio,
)
from mulenetx.evaluation.reference import REFERENCE_CONSTRUCTION_VERSION, reference_rings
from mulenetx.interventions import ranking as intervention_ranking
from mulenetx.interventions.engine import evaluate as evaluate_interventions
from mulenetx.interventions.pool import eligibility, validate
from mulenetx.interventions.service import compute_baseline

LEVELS = ("TRANSACTION", "ACCOUNT", "RING", "NETWORK")
LIMITATION = (
    "PaySim provides synthetic transaction-level fraud labels only. It has no authoritative mule-account or "
    "mule-ring ground truth: account and ring references here are derived from transaction labels, so account, "
    "ring and network metrics measure agreement with that derived reference, not real-world mule detection."
)
SIMULATED = (
    "Intervention effectiveness is computed from hypothetical simulations; it is never a measure of real-world "
    "enforcement effectiveness."
)


class EvaluationFailedError(Exception):
    pass


def submit(
    db: Session,
    settings: Settings,
    audit: AuditService,
    principal: Principal,
    model_version: str | None,
    configuration: dict[str, Any] | None,
    request_id: str | None,
) -> EvaluationRun:
    ctx = db.execute(select(ActiveContext)).scalar_one()
    if ctx.dataset_id is None or ctx.scoring_run_id is None or ctx.graph_snapshot_id is None:
        raise AppError(
            ec.PIPELINE_PREREQUISITE_MISSING,
            "No active analytical context to evaluate.",
            {"prerequisite": "active_context"},
        )
    version = model_version or ctx.model_version
    if version is None:
        raise AppError(
            ec.PIPELINE_PREREQUISITE_MISSING, "No model is registered for this context.", {"prerequisite": "model"}
        )
    model = db.get(ModelVersion, version)
    if model is None:
        raise AppError(ec.NOT_FOUND, details={"resource": "model"})
    scoring = db.get(ScoringRun, ctx.scoring_run_id)
    assert scoring is not None
    from mulenetx.jobs.queue import enqueue

    run_id = uuid.uuid4()
    job = enqueue(
        db,
        "EVALUATION",
        {"evaluation_run_id": str(run_id)},
        max_attempts=settings.job_max_attempts,
        requested_by=principal.user_id,
        request_id=request_id,
    )
    db.flush()
    config = {
        **(configuration or {}),
        "population": "test split of the model's split boundaries (§28.7)",
        "test_window": {"after": model.split_boundaries["T_val"], "until": model.split_boundaries["T_test"]},
        "transaction_score": "max(final_score(source), final_score(destination))",
        "account_reference": "participates in ≥ 1 reference-positive test transaction; MERCHANT excluded",
        "ring_reference": "WCC of reference-positive test transactions with ≥ 3 accounts",
        "matching": "one-to-one, Jaccard ≥ 0.5, max Jaccard; ties by reference then analytical ring ID",
        "lineage": {
            "dataset_id": str(ctx.dataset_id),
            "graph_snapshot_id": str(ctx.graph_snapshot_id),
            "analytics_run_id": None if ctx.analytics_run_id is None else str(ctx.analytics_run_id),
            "scoring_run_id": str(ctx.scoring_run_id),
            "analytics_version": None,
            "feature_version": scoring.feature_version,
            "model_version": version,
            "risk_logic_version": scoring.risk_logic_version,
        },
        "job_id": str(job.job_id),
    }
    analytics_version = db.execute(
        text("SELECT analytics_version FROM analytics_runs WHERE analytics_run_id = :r"), {"r": ctx.analytics_run_id}
    ).scalar_one()
    config["lineage"]["analytics_version"] = analytics_version
    run = EvaluationRun(
        evaluation_run_id=run_id,
        dataset_id=ctx.dataset_id,
        model_version=version,
        test_snapshot_id=ctx.graph_snapshot_id,
        scoring_run_id=ctx.scoring_run_id,
        analytics_version=analytics_version,
        risk_logic_version=scoring.risk_logic_version,
        reference_construction_version=REFERENCE_CONSTRUCTION_VERSION,
        configuration=config,
        status="QUEUED",
        created_at=utcnow(),
    )
    db.add(run)
    audit.record_in(
        db,
        "evaluation.create",
        "evaluation_run",
        "SUCCESS",
        user_id=principal.user_id,
        resource_id=str(run_id),
        metadata={"model_version": version},
    )
    db.commit()
    return run


# ── computation ─────────────────────────────────────────────────────────────


def compute(engine: Engine, settings: Settings, db: Session, run: EvaluationRun) -> list[Row]:
    snapshot = db.get(GraphSnapshot, run.test_snapshot_id)
    model = db.get(ModelVersion, run.model_version)
    assert snapshot is not None and model is not None
    t_val, t_test = parse_utc(model.split_boundaries["T_val"]), parse_utc(model.split_boundaries["T_test"])
    if snapshot.data_cutoff != t_test:
        raise EvaluationFailedError(
            f"the scoring run's snapshot cutoff {isoformat_utc(snapshot.data_cutoff)} is not the test cutoff "
            f"T_test {isoformat_utc(t_test)}; evaluate a context whose snapshot covers the test window"
        )
    params = {"d": run.dataset_id, "lo": t_val, "hi": t_test, "s": run.scoring_run_id}
    with engine.connect() as conn:
        txs = conn.execute(
            text(
                """
            SELECT t.transaction_id, t.source_account_id AS src, t.destination_account_id AS dst, t.amount,
                   t.fraud_label, coalesce(rs.final_score, 0) AS fs_src, coalesce(rd.final_score, 0) AS fs_dst,
                   rs.ml_score AS ml_src, rd.ml_score AS ml_dst
            FROM transactions t
            LEFT JOIN risk_assessments rs ON rs.scoring_run_id = :s AND rs.account_id = t.source_account_id
            LEFT JOIN risk_assessments rd ON rd.scoring_run_id = :s AND rd.account_id = t.destination_account_id
            WHERE t.dataset_id = :d AND t."timestamp" > :lo AND t."timestamp" <= :hi
            ORDER BY t."timestamp", t.transaction_id
            """
            ),
            params,
        ).all()
        accounts = {
            r.account_id: (r.account_type, r.final_score)
            for r in conn.execute(
                text(
                    """
            SELECT a.account_id, a.account_type, coalesce(r.final_score, 0) AS final_score
            FROM accounts a LEFT JOIN risk_assessments r ON r.scoring_run_id = :s AND r.account_id = a.account_id
            WHERE a.dataset_id = :d
            """
                ),
                params,
            )
        }
        candidates = conn.execute(
            text(
                """
            SELECT c.candidate_id, c.candidate_class, c.analytics_run_id, c.community_id, rr.ring_risk_score,
                   array_agg(m.account_id ORDER BY m.account_id) AS members
            FROM potential_fraud_ring_candidates c
            JOIN community_memberships m ON m.analytics_run_id = c.analytics_run_id AND m.community_id = c.community_id
            LEFT JOIN ring_risk_assessments rr ON rr.ring_id = c.candidate_id AND rr.scoring_run_id = c.scoring_run_id
            WHERE c.scoring_run_id = :s
            GROUP BY c.candidate_id, c.candidate_class, c.analytics_run_id, c.community_id, rr.ring_risk_score
            """
            ),
            params,
        ).all()

    rows: list[Row] = []
    # transaction level
    labelled = [t for t in txs if t.fraud_label is not None]
    rows += ranking_rows(
        "TRANSACTION",
        [int(t.fraud_label) for t in labelled],
        [float(max(t.fs_src, t.fs_dst)) for t in labelled],
        [t.transaction_id for t in labelled],
        {
            "unlabelled_excluded": len(txs) - len(labelled),
            "test_window": [isoformat_utc(t_val), isoformat_utc(t_test)],
            "ml_score_mean_source": _mean([t.ml_src for t in labelled]),
            "ml_score_mean_destination": _mean([t.ml_dst for t in labelled]),
        },
    )
    positive = [t for t in labelled if t.fraud_label]
    # account level
    participants = {a for t in txs for a in (t.src, t.dst)}
    positive_accounts = {a for t in positive for a in (t.src, t.dst)}
    population = sorted(a for a in participants if accounts.get(a, ("", 0))[0] != "MERCHANT")
    rows += ranking_rows(
        "ACCOUNT",
        [int(a in positive_accounts) for a in population],
        [float(accounts.get(a, ("", 0))[1]) for a in population],
        population,
        {"merchants_excluded": len(participants) - len(population)},
    )
    rows.append(
        not_measurable(
            "ACCOUNT",
            "mule_account_identity",
            "PaySim does not label mule accounts; the account reference is derived from transaction labels.",
        )
    )
    # ring level
    refs = reference_rings((t.src, t.dst) for t in positive)
    analytical = {str(c.candidate_id): frozenset(c.members) for c in candidates}
    matches = match(analytical, {r.ring_id: r.members for r in refs})
    matched_ids = {m.analytical_id for m in matches}
    rows += [
        ratio("RING", "ring_precision", len(matches), len(analytical), len(analytical)),
        ratio("RING", "ring_recall", len(matches), len(refs), len(refs)),
    ]
    p, r = rows[-2], rows[-1]
    f1 = (2 * p.value * r.value / (p.value + r.value)) if p.value and r.value else 0.0
    rows.append(
        Row(
            "RING",
            "ring_f1",
            f1,
            len(analytical),
            "AVAILABLE" if p.value and r.value else "UNAVAILABLE",
            {} if p.value and r.value else {"reason": "precision or recall is 0 or unavailable"},
        )
    )
    rows.append(
        Row(
            "RING",
            "mean_matched_jaccard",
            float(sum(m.jaccard for m in matches) / len(matches)) if matches else 0.0,
            len(matches),
            "AVAILABLE" if matches else "UNAVAILABLE",
            {
                "matches": [
                    {
                        "analytical_ring_id": m.analytical_id,
                        "reference_ring_id": m.reference_id,
                        "jaccard": float(m.jaccard),
                    }
                    for m in matches
                ],
                "reference_rings": len(refs),
                "analytical_rings": len(analytical),
                "reference_construction_version": REFERENCE_CONSTRUCTION_VERSION,
            },
        )
    )
    rows.append(
        not_measurable(
            "RING",
            "ring_identity_ground_truth",
            "PaySim has no mule-ring identities; reference rings are components of labelled transactions.",
        )
    )
    # network level
    identified = set().union(*analytical.values()) if analytical else set()
    reference_accounts = set().union(*(r.members for r in refs)) if refs else set()
    both = identified & reference_accounts
    rows += [
        ratio("NETWORK", "network_precision", len(both), len(identified), len(identified)),
        ratio("NETWORK", "network_recall", len(both), len(reference_accounts), len(reference_accounts)),
    ]
    covered = sum(float(t.amount) for t in positive if t.src in identified and t.dst in identified)
    rows.append(
        ratio("NETWORK", "suspicious_flow_coverage", covered, sum(float(t.amount) for t in positive), len(positive))
    )
    ranked = sorted(
        (c for c in candidates if c.ring_risk_score is not None),
        key=lambda c: (-float(c.ring_risk_score), str(c.candidate_id)),
    )
    ap = average_precision([str(c.candidate_id) in matched_ids for c in ranked])
    rows.append(
        Row(
            "NETWORK",
            "network_risk_ranking",
            ap if ap is not None else 0.0,
            len(ranked),
            "AVAILABLE" if ap is not None else "UNAVAILABLE",
            {"ranked_by": "ring_risk_score (potential fraud ring candidates)"}
            if ap is not None
            else {"reason": "no ranked ring is matched"},
        )
    )
    rows += intervention_effectiveness(engine, settings, db, run, candidates, matched_ids)
    return rows


def _mean(values: list[Any]) -> float | None:
    vals = [float(v) for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def intervention_effectiveness(
    engine: Engine,
    settings: Settings,
    db: Session,
    run: EvaluationRun,
    candidates: Sequence[Any],
    matched_ids: set[str],
) -> list[Row]:
    """Rank-1 RANK candidate vs a degree-ranked baseline evaluated with the intervention code path (§28.7)."""
    rank1: list[float] = []
    degree: list[float] = []
    per_ring: list[dict[str, Any]] = []
    snapshot = db.get(GraphSnapshot, run.test_snapshot_id)
    assert snapshot is not None
    for c in candidates:
        rid = str(c.candidate_id)
        if rid not in matched_ids or c.candidate_class != "POTENTIAL_FRAUD_RING_CANDIDATE":
            continue
        top = db.execute(
            text(
                """
            SELECT ic.flow_disruption_percentage FROM intervention_scenarios s
            JOIN intervention_candidates ic ON ic.scenario_id = s.scenario_id AND ic.rank_position = 1
            WHERE s.target_ring_id = :r AND s.scoring_run_id = :s AND s.mode = 'RANK' AND s.status = 'COMPLETED'
            ORDER BY s.completed_at DESC LIMIT 1
            """
            ),
            {"r": c.candidate_id, "s": run.scoring_run_id},
        ).scalar_one_or_none()
        if top is None:
            per_ring.append({"ring_id": rid, "state": "NO_COMPLETED_RANK_SCENARIO"})
            continue
        degrees = db.execute(
            text(
                "SELECT account_id, degree FROM account_graph_metrics WHERE analytics_run_id = :a "
                "AND account_id = ANY(:m) ORDER BY degree DESC, account_id LIMIT 1"
            ),
            {"a": c.analytics_run_id, "m": list(c.members)},
        ).one_or_none()
        base = compute_baseline(engine, settings, snapshot, run.scoring_run_id, list(c.members))
        types, _edges, _counts = eligibility(base)
        entry: dict[str, Any] = {"ring_id": rid, "rank1_flow_disruption_percentage": float(top)}
        rank1.append(float(top))
        if degrees is None or degrees.account_id not in types:
            entry["degree_baseline"] = {
                "account_id": None if degrees is None else degrees.account_id,
                "state": "NOT_ON_BASELINE_PATHS",
            }
        else:
            spec = validate(base, types[degrees.account_id], [degrees.account_id])
            config_hash = intervention_ranking.configuration_hash(
                intervention_ranking.configuration(
                    settings.intervention_max_candidates,
                    settings.analytic_max_depth,
                    settings.analytic_max_paths,
                    settings.analytic_max_expansions,
                )
            )
            (result,) = evaluate_interventions(base, [spec], c.candidate_id, run.scoring_run_id, config_hash)
            value = float(result.metrics.flow_disruption_percentage)
            degree.append(value)
            entry["degree_baseline"] = {
                "account_id": degrees.account_id,
                "operation_type": spec.operation_type,
                "flow_disruption_percentage": value,
            }
        per_ring.append(entry)
    details = {"simulated": True, "statement": SIMULATED, "rings": per_ring}
    rows = []
    for metric, values in (
        ("intervention_effectiveness_rank1", rank1),
        ("intervention_effectiveness_degree_baseline", degree),
    ):
        dist = distribution(values)
        rows.append(
            Row(
                "NETWORK",
                metric,
                dist["mean"] if values else 0.0,
                len(values),
                "AVAILABLE" if values else "UNAVAILABLE",
                {
                    **details,
                    "distribution": dist,
                    **(
                        {}
                        if values
                        else {
                            "reason": "no matched potential fraud ring has a completed RANK "
                            "scenario with an eligible degree-baseline account"
                        }
                    ),
                },
            )
        )
    return rows


# ── read models ─────────────────────────────────────────────────────────────


def _iso(x: datetime | None) -> str | None:
    return None if x is None else isoformat_utc(x)


def run_view(db: Session, r: EvaluationRun) -> dict[str, Any]:
    failure = None
    if r.status == "FAILED":
        failure = db.execute(
            text("SELECT error_summary FROM jobs WHERE job_id = :j"), {"j": r.configuration.get("job_id")}
        ).scalar_one_or_none()
    return {
        "evaluation_run_id": str(r.evaluation_run_id),
        "status": r.status,
        "dataset_id": str(r.dataset_id),
        "model_version": r.model_version,
        "test_snapshot_id": str(r.test_snapshot_id),
        "scoring_run_id": str(r.scoring_run_id),
        "analytics_version": r.analytics_version,
        "risk_logic_version": r.risk_logic_version,
        "reference_construction_version": r.reference_construction_version,
        "configuration": r.configuration,
        "failure": failure,
        "created_at": _iso(r.created_at),
        "completed_at": _iso(r.completed_at),
        "limitation": LIMITATION,
    }


def metric_view(m: EvaluationMetric) -> dict[str, Any]:
    details = m.details or {}
    state = details.get("state", m.availability)
    return {
        "level": m.level,
        "metric": m.metric,
        "value": m.value,
        "sample_count": m.sample_count,
        "availability": m.availability,
        "state": state,
        "details": details,
    }


def metrics_of(db: Session, run_id: uuid.UUID, level: str | None = None) -> list[EvaluationMetric]:
    q = select(EvaluationMetric).where(EvaluationMetric.evaluation_run_id == run_id)
    if level is not None:
        q = q.where(EvaluationMetric.level == level)
    order = {name: i for i, name in enumerate(LEVELS)}
    return sorted(db.execute(q).scalars(), key=lambda m: (order[m.level], m.metric))


HEADLINE = {"TRANSACTION": "pr_auc", "ACCOUNT": "pr_auc", "RING": "ring_f1", "NETWORK": "suspicious_flow_coverage"}


def summary(db: Session, r: EvaluationRun) -> dict[str, Any]:
    rows = metrics_of(db, r.evaluation_run_id)
    by_level: dict[str, list[dict[str, Any]]] = {lvl: [] for lvl in LEVELS}
    for m in rows:
        by_level[m.level].append(metric_view(m))
    progression = []
    for lvl in LEVELS:
        head = next((m for m in by_level[lvl] if m["metric"] == HEADLINE[lvl]), None)
        progression.append(
            {
                "level": lvl,
                "headline_metric": HEADLINE[lvl],
                "value": None if head is None else head["value"],
                "state": None if head is None else head["state"],
                "sample_count": None if head is None else head["sample_count"],
            }
        )
    profile = db.execute(
        text("SELECT metrics FROM dataset_profiles WHERE dataset_id = :d ORDER BY created_at DESC LIMIT 1"),
        {"d": r.dataset_id},
    ).scalar_one_or_none()
    states = Counter(m["state"] for lvl in by_level.values() for m in lvl)
    return {
        **run_view(db, r),
        "progression": progression,
        "levels": by_level,
        "dataset_profile": profile,
        "state_counts": dict(states),
    }
