"""RingIntelligenceService (SRS §9, §9A, §18.1): candidates from communities after SCORING, then ring
intelligence for POTENTIAL_FRAUD_RING_CANDIDATE. Computation happens outside the database transaction; the
RING_ANALYSIS stage writes everything in its final transaction (idempotent inserts)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from mulenetx.core import ids
from mulenetx.core.runtime import Runtime
from mulenetx.db.models.lineage import AnalyticsRun, GraphSnapshot, ScoringRun
from mulenetx.db.models.rings import RingCandidate, RingFeatureSet, RingMembership, RingRiskAssessment
from mulenetx.flow.analytic_paths import Budget
from mulenetx.rings import features as ring_features
from mulenetx.rings import inputs
from mulenetx.rings import risk as ring_risk
from mulenetx.rings.candidates import POTENTIAL_FRAUD_RING_CANDIDATE, CandidateScore, score_communities
from mulenetx.rings.membership import Membership, membership

RING_NAMESPACE = uuid.UUID("2b7d0c55-3d3a-4c6b-9f4e-8a1f0d2c6e91")


@dataclass
class RingIntelligence:
    membership: Membership
    features: ring_features.RingFeatures
    risk: ring_risk.RingRisk


def feature_set_id(ring_id: uuid.UUID, scoring_run_id: uuid.UUID) -> uuid.UUID:
    return uuid.uuid5(RING_NAMESPACE, f"ring-features|{ring_id}|{scoring_run_id}|{ring_features.RING_FEATURE_VERSION}")


def ring_risk_id(ring_id: uuid.UUID, scoring_run_id: uuid.UUID) -> uuid.UUID:
    return uuid.uuid5(RING_NAMESPACE, f"ring-risk|{ring_id}|{scoring_run_id}|{ring_features.RING_FEATURE_VERSION}")


def intelligence(ctx: inputs.ContextInputs, community_members: list[str]) -> RingIntelligence:
    m = membership(ctx, community_members)
    f = ring_features.compute(ctx, m)
    return RingIntelligence(m, f, ring_risk.compute(ctx, m, f))


@dataclass
class RingAnalysis:
    snapshot: GraphSnapshot
    analytics: AnalyticsRun
    scoring: ScoringRun
    candidates: dict[str, CandidateScore]  # persisted classes only, by community_id
    context: inputs.ContextInputs
    rings: dict[str, RingIntelligence]  # POTENTIAL_FRAUD_RING_CANDIDATE only, by community_id


class RingIntelligenceService:
    def __init__(self, runtime: Runtime) -> None:
        self.rt = runtime

    def budget(self) -> Budget:
        s = self.rt.settings
        return Budget(s.analytic_max_depth, s.analytic_max_paths, s.analytic_max_expansions)

    def analyze(
        self, dataset_id: uuid.UUID, snapshot_id: uuid.UUID, analytics_run_id: uuid.UUID, scoring_run_id: uuid.UUID
    ) -> RingAnalysis:
        with self.rt.session_factory() as db:
            snapshot = db.get(GraphSnapshot, snapshot_id)
            analytics = db.get(AnalyticsRun, analytics_run_id)
            scoring = db.get(ScoringRun, scoring_run_id)
            assert snapshot is not None and analytics is not None and scoring is not None
            assert snapshot.data_cutoff is not None
            db.expunge_all()
        ctx = inputs.load(
            self.rt.engine,
            dataset_id,
            snapshot_id,
            snapshot.data_cutoff,
            analytics_run_id,
            analytics.analytics_version,
            scoring_run_id,
            self.budget(),
        )
        scored = score_communities(ctx)
        persisted = {cid: c for cid, c in scored.items() if c.candidate_class != "NOT_SUSPICIOUS"}
        rings = {
            cid: intelligence(ctx, ctx.communities[cid])
            for cid, c in persisted.items()
            if c.candidate_class == POTENTIAL_FRAUD_RING_CANDIDATE
        }
        return RingAnalysis(snapshot, analytics, scoring, persisted, ctx, rings)

    @staticmethod
    def persist(db: Session, analysis: RingAnalysis, now: datetime) -> list[uuid.UUID]:
        """Insert candidates (ON CONFLICT DO NOTHING: a rerun of the same scoring run derives the same IDs)."""
        snap, run = analysis.snapshot.graph_snapshot_id, analysis.scoring.scoring_run_id
        written: list[uuid.UUID] = []
        for community_id, c in sorted(analysis.candidates.items()):
            candidate_id = ids.candidate_id(snap, run, community_id)
            db.execute(
                insert(RingCandidate)
                .values(
                    candidate_id=candidate_id,
                    community_id=community_id,
                    analytics_run_id=analysis.analytics.analytics_run_id,
                    graph_snapshot_id=snap,
                    scoring_run_id=run,
                    candidate_score=c.score,
                    candidate_class=c.candidate_class,
                    signal_summary=c.signals,
                    candidate_status="CANDIDATE",
                    analytics_version=analysis.analytics.analytics_version,
                    risk_logic_version=analysis.scoring.risk_logic_version,
                    created_at=now,
                )
                .on_conflict_do_nothing()
            )
            written.append(candidate_id)
            ring = analysis.rings.get(community_id)
            if ring is not None:
                persist_ring(db, analysis, candidate_id, community_id, ring, now)
        return written


def persist_ring(
    db: Session, analysis: RingAnalysis, ring_id: uuid.UUID, community_id: str, ring: RingIntelligence, now: datetime
) -> None:
    run = analysis.scoring.scoring_run_id
    for account_id in ring.membership.members:
        db.execute(insert(RingMembership).values(ring_id=ring_id, account_id=account_id).on_conflict_do_nothing())
    fs_id = feature_set_id(ring_id, run)
    m = ring.membership
    db.execute(
        insert(RingFeatureSet)
        .values(
            ring_feature_set_id=fs_id,
            ring_id=ring_id,
            analytics_run_id=analysis.analytics.analytics_run_id,
            community_id=community_id,
            graph_snapshot_id=analysis.snapshot.graph_snapshot_id,
            scoring_run_id=run,
            analytics_version=analysis.analytics.analytics_version,
            feature_version=ring_features.RING_FEATURE_VERSION,
            ring_size=m.ring_size,
            transaction_count=len(m.constituent),
            start_time=m.start_time,
            end_time=m.end_time,
            temporal_span_seconds=m.temporal_span_seconds,
            availability={**ring.features.availability, "counters": ring.features.scope.counters},
            computed_at=now,
            **ring_features.as_columns(ring.features),
        )
        .on_conflict_do_nothing()
    )
    r = ring.risk
    db.execute(
        insert(RingRiskAssessment)
        .values(
            ring_risk_assessment_id=ring_risk_id(ring_id, run),
            ring_id=ring_id,
            feature_set_id=fs_id,
            scoring_run_id=run,
            ring_risk_score=r.score,
            risk_tier=r.tier,
            availability={**r.availability, "temporal_indicators": r.temporal_indicators},
            risk_logic_version=analysis.scoring.risk_logic_version,
            analytics_version=analysis.analytics.analytics_version,
            feature_version=ring_features.RING_FEATURE_VERSION,
            generated_at=now,
            **r.components,
        )
        .on_conflict_do_nothing()
    )


def candidates_of_run(db: Session, scoring_run_id: uuid.UUID) -> list[RingCandidate]:
    return list(
        db.execute(
            select(RingCandidate)
            .where(RingCandidate.scoring_run_id == scoring_run_id)
            .order_by(RingCandidate.candidate_score.desc(), RingCandidate.candidate_id)
        ).scalars()
    )
