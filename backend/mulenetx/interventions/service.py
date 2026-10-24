"""InterventionService (SRS §16A, §19.15): scenario submission, the INTERVENTION job, and read models.

It reads canonical and analytical state through read-only loaders and writes only its own two tables
(`intervention_scenarios`, `intervention_candidates`) — §16A.17. Nothing here changes an account, a
transaction, the graph store, risk, cases or any external system."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from mulenetx.audit.service import AuditService
from mulenetx.auth.service import Principal
from mulenetx.core import error_codes as ec
from mulenetx.core.config import Settings
from mulenetx.core.errors import AppError
from mulenetx.core.timeutil import isoformat_utc, utcnow
from mulenetx.db.models.auth import User
from mulenetx.db.models.communities import CommunityMembership
from mulenetx.db.models.interventions import InterventionCandidate, InterventionScenario
from mulenetx.db.models.lineage import GraphSnapshot
from mulenetx.db.models.rings import RingCandidate
from mulenetx.flow.analytic_paths import Budget, enumerate_ring_scope, load_projection
from mulenetx.flow.vocabulary import load_context
from mulenetx.interventions import ranking
from mulenetx.interventions.baseline import Baseline, build
from mulenetx.interventions.engine import Result, evaluate
from mulenetx.interventions.metrics import money4
from mulenetx.interventions.pool import PoolTooLargeError, Spec, rank_pool, validate

STATEMENT = (
    "Hypothetical simulation: these results describe a counterfactual graph analysis only. No account, transaction, "
    "payment or external system is blocked, frozen or changed, and a candidate is not a recommendation to act."
)
ACTIVE = ("QUEUED", "RUNNING")


@dataclass(frozen=True)
class Submission:
    mode: str
    intervention_type: str | None
    target_ids: list[str] | None


def budget(settings: Settings) -> Budget:
    return Budget(settings.analytic_max_depth, settings.analytic_max_paths, settings.analytic_max_expansions)


def ranking_configuration(settings: Settings) -> dict[str, Any]:
    return ranking.configuration(
        settings.intervention_max_candidates,
        settings.analytic_max_depth,
        settings.analytic_max_paths,
        settings.analytic_max_expansions,
    )


def ring_candidate(db: Session, ring_id: uuid.UUID) -> RingCandidate:
    c = db.get(RingCandidate, ring_id)
    if c is None:
        raise AppError(ec.NOT_FOUND, details={"resource": "ring"})
    if c.candidate_class != "POTENTIAL_FRAUD_RING_CANDIDATE":
        raise AppError(ec.RING_INTELLIGENCE_NOT_APPLICABLE, details={"candidate_class": c.candidate_class})
    return c


def members(db: Session, c: RingCandidate) -> list[str]:
    return list(
        db.execute(
            select(CommunityMembership.account_id)
            .where(
                CommunityMembership.analytics_run_id == c.analytics_run_id,
                CommunityMembership.community_id == c.community_id,
            )
            .order_by(CommunityMembership.account_id)
        ).scalars()
    )


def compute_baseline(
    engine: Engine, settings: Settings, snapshot: GraphSnapshot, scoring_run_id: uuid.UUID, ring_members: list[str]
) -> Baseline:
    """Read-only: the snapshot projection and the scoring run's final scores, then §16A.5."""
    assert snapshot.data_cutoff is not None
    proj = load_projection(engine, snapshot.graph_snapshot_id, snapshot.dataset_id, snapshot.data_cutoff)
    run = load_context(engine, scoring_run_id)
    return build(proj, run, enumerate_ring_scope(proj, ring_members, run, budget(settings)))


class InterventionService:
    def __init__(self, settings: Settings, audit: AuditService) -> None:
        self.settings = settings
        self.audit = audit

    def submit(
        self,
        db: Session,
        engine: Engine,
        principal: Principal,
        ring_id: uuid.UUID,
        body: Submission,
        request_id: str | None,
    ) -> InterventionScenario:
        c = ring_candidate(db, ring_id)
        targets: list[str] | None = None
        if body.mode == "EVALUATE":
            snapshot = db.get(GraphSnapshot, c.graph_snapshot_id)
            assert snapshot is not None
            base = compute_baseline(engine, self.settings, snapshot, c.scoring_run_id, members(db, c))
            spec = validate(base, body.intervention_type, body.target_ids)  # 400 before any scenario exists
            targets = list(spec.targets)
        elif body.intervention_type is not None or body.target_ids is not None:
            raise AppError(ec.INTERVENTION_TARGET_INVALID, "RANK mode takes no targets.", {"field": "target_ids"})
        db.get(User, principal.user_id, with_for_update=True)  # serialises this user's submissions
        active = int(
            db.execute(
                select(func.count())
                .select_from(InterventionScenario)
                .where(InterventionScenario.requested_by == principal.user_id, InterventionScenario.status.in_(ACTIVE))
            ).scalar_one()
        )
        limit = self.settings.max_concurrent_scenarios_per_user
        if active >= limit:
            raise AppError(
                ec.RATE_LIMITED,
                "Too many simulations are queued or running for this user.",
                {"limit": limit, "active": active},
            )
        config = ranking_configuration(self.settings)
        from mulenetx.jobs.queue import enqueue

        scenario_id = uuid.uuid4()
        job = enqueue(
            db,
            "INTERVENTION",
            {"scenario_id": str(scenario_id)},
            max_attempts=self.settings.job_max_attempts,
            requested_by=principal.user_id,
            request_id=request_id,
        )
        db.flush()  # the job row must exist before the scenario references it
        scenario = InterventionScenario(
            scenario_id=scenario_id,
            mode=body.mode,
            target_ring_id=ring_id,
            baseline_graph_snapshot_id=c.graph_snapshot_id,
            scoring_run_id=c.scoring_run_id,
            intervention_type=body.intervention_type if body.mode == "EVALUATE" else None,
            target_ids=targets,
            ranking_configuration=config,
            ranking_configuration_hash=ranking.configuration_hash(config),
            analytics_version=c.analytics_version,
            risk_logic_version=c.risk_logic_version,
            requested_by=principal.user_id,
            job_id=job.job_id,
            status="QUEUED",
            created_at=utcnow(),
        )
        db.add(scenario)
        self.audit.record_in(
            db,
            "intervention.create",
            "intervention_scenario",
            "SUCCESS",
            user_id=principal.user_id,
            resource_id=str(scenario_id),
            metadata={
                "ring_id": str(ring_id),
                "mode": body.mode,
                "intervention_type": scenario.intervention_type,
                "target_ids": targets,
            },
        )
        db.commit()
        return scenario


def run_scenario(
    engine: Engine, settings: Settings, db: Session, scenario: InterventionScenario
) -> tuple[Baseline, list[Result], list[str] | None]:
    """The job's computation: returns the baseline, the ranked results and (RANK) the eligible candidate IDs."""
    c = db.get(RingCandidate, scenario.target_ring_id)
    snapshot = db.get(GraphSnapshot, scenario.baseline_graph_snapshot_id)
    assert c is not None and snapshot is not None
    base = compute_baseline(engine, settings, snapshot, scenario.scoring_run_id, members(db, c))
    if scenario.mode == "RANK":
        specs = rank_pool(base, settings.intervention_max_candidates)
    else:
        specs = [validate(base, scenario.intervention_type, list(scenario.target_ids or []))]
    results = evaluate(
        base, specs, scenario.target_ring_id, scenario.scoring_run_id, scenario.ranking_configuration_hash
    )
    eligible = None
    if scenario.mode == "RANK":
        by_spec = {(r.spec.operation_type, r.spec.targets): r.candidate_id for r in results}
        eligible = [by_spec[(s.operation_type, s.targets)] for s in specs]  # §16A.4.3 enumeration order
    return base, results, eligible


def candidate_row(scenario_id: uuid.UUID, r: Result, now: datetime) -> InterventionCandidate:
    m = r.metrics
    return InterventionCandidate(
        candidate_id=uuid.UUID(r.candidate_id),
        scenario_id=scenario_id,
        operation_type=r.spec.operation_type,
        target_ids=list(r.spec.targets),
        residual_suspicious_flow=money4(m.residual_suspicious_flow),
        flow_disruption=money4(m.flow_disruption),
        flow_disruption_percentage=m.flow_disruption_percentage,
        residual_suspicious_paths=m.residual_suspicious_paths,
        normalized_path_disruption=m.normalized_path_disruption,
        residual_reachable_suspicious_pairs=m.residual_reachable_suspicious_pairs,
        normalized_connectivity_disruption=m.normalized_connectivity_disruption,
        residual_risk_mass=m.residual_risk_mass,
        residual_network_risk=m.residual_network_risk,
        normalized_risk_reduction=m.normalized_risk_reduction,
        intervention_cost=m.intervention_cost,
        normalized_intervention_cost=m.normalized_intervention_cost,
        intervention_score=r.intervention_score,
        rank_position=r.rank_position,
        affected_account_ids=r.affected_account_ids,
        affected_path_ids=r.affected_path_ids,
        alternative_path_ids=r.alternative_path_ids,
        unavailable_metrics=m.unavailable,
        evidence=r.evidence,
        created_at=now,
    )


def _f(x: Decimal | None) -> float | None:
    return None if x is None else float(x)


def _iso(x: datetime | None) -> str | None:
    return None if x is None else isoformat_utc(x)


def scenario_view(s: InterventionScenario) -> dict[str, Any]:
    return {
        "scenario_id": str(s.scenario_id),
        "hypothetical": True,
        "statement": STATEMENT,
        "mode": s.mode,
        "status": s.status,
        "target_ring_id": str(s.target_ring_id),
        "baseline_graph_snapshot_id": str(s.baseline_graph_snapshot_id),
        "scoring_run_id": str(s.scoring_run_id),
        "intervention_type": s.intervention_type,
        "target_ids": s.target_ids,
        "baseline": {
            "suspicious_flow": None if s.baseline_suspicious_flow is None else format(s.baseline_suspicious_flow, "f"),
            "suspicious_paths": s.baseline_suspicious_paths,
            "reachable_suspicious_pairs": s.baseline_reachable_suspicious_pairs,
            "risk_mass": None if s.baseline_risk_mass is None else format(s.baseline_risk_mass, "f"),
            "network_risk": None if s.baseline_risk_mass is None else 1.0,
        },
        "baseline_paths_truncated": s.baseline_paths_truncated,
        "metrics_are_lower_bounds": bool(s.baseline_paths_truncated),
        "eligible_candidate_count": None if s.eligible_candidate_ids is None else len(s.eligible_candidate_ids),
        "ranking_configuration": s.ranking_configuration,
        "ranking_configuration_hash": s.ranking_configuration_hash,
        "analytics_version": s.analytics_version,
        "risk_logic_version": s.risk_logic_version,
        "requested_by": str(s.requested_by),
        "job_id": None if s.job_id is None else str(s.job_id),
        "error_summary": s.error_summary,
        "created_at": _iso(s.created_at),
        "completed_at": _iso(s.completed_at),
    }


def candidate_view(c: InterventionCandidate, truncated: bool | None) -> dict[str, Any]:
    return {
        "candidate_id": str(c.candidate_id),
        "hypothetical": True,
        "baseline_paths_truncated": bool(truncated),
        "rank_position": c.rank_position,
        "operation_type": c.operation_type,
        "target_ids": c.target_ids,
        "intervention_score": float(c.intervention_score),
        "residual_suspicious_flow": format(c.residual_suspicious_flow, "f"),
        "flow_disruption": format(c.flow_disruption, "f"),
        "flow_disruption_percentage": float(c.flow_disruption_percentage),
        "residual_suspicious_paths": c.residual_suspicious_paths,
        "normalized_path_disruption": float(c.normalized_path_disruption),
        "residual_reachable_suspicious_pairs": c.residual_reachable_suspicious_pairs,
        "normalized_connectivity_disruption": float(c.normalized_connectivity_disruption),
        "residual_risk_mass": format(c.residual_risk_mass, "f"),
        "residual_network_risk": float(c.residual_network_risk),
        "normalized_risk_reduction": float(c.normalized_risk_reduction),
        "intervention_cost": float(c.intervention_cost),
        "normalized_intervention_cost": float(c.normalized_intervention_cost),
        "affected_account_ids": c.affected_account_ids,
        "affected_path_ids": c.affected_path_ids,
        "alternative_path_ids": c.alternative_path_ids,
        "unavailable_metrics": c.unavailable_metrics,
        "evidence": c.evidence,
    }


__all__ = ["InterventionService", "PoolTooLargeError", "Spec", "candidate_row", "run_scenario", "scenario_view"]
