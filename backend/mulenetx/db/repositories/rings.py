"""Ring read models (SRS §19.2 rings rows, §19.13, §9.4, §9A). Wording is analytical (§9.5, §9A.6)."""

from __future__ import annotations

import functools
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session

from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.core.lineage import Lineage, lineage_envelope
from mulenetx.core.pagination import PageRequest, decode_cursor, encode_cursor, offset_page
from mulenetx.core.timeutil import isoformat_utc
from mulenetx.db.models.canonical import Account
from mulenetx.db.models.communities import CommunityMembership
from mulenetx.db.models.lineage import AnalyticsRun, GraphSnapshot, ScoringRun
from mulenetx.db.models.rings import RingCandidate, RingFeatureSet, RingRiskAssessment

__all__ = ["RingCandidate"]
from mulenetx.db.repositories.context import active, active_lineage
from mulenetx.flow.analytic_paths import Budget
from mulenetx.rings import evidence as ring_evidence
from mulenetx.rings import inputs as ring_inputs
from mulenetx.rings.candidates import POTENTIAL_FRAUD_RING_CANDIDATE, SUSPICIOUS_COMMUNITY
from mulenetx.rings.features import RING_FEATURE_VERSION
from mulenetx.rings.service import intelligence

INTERPRETATION = (
    "Analytical candidate: a potential fraud ring or suspicious network for investigation. Community membership "
    "is not proof of a fraud ring, and a candidate is not a confirmed criminal organisation."
)
CLASSES = (SUSPICIOUS_COMMUNITY, POTENTIAL_FRAUD_RING_CANDIDATE)
STATUSES = ("CANDIDATE", "REVIEWED", "DISMISSED")
STATUS_TRANSITIONS = {
    "CANDIDATE": {"REVIEWED", "DISMISSED"},
    "REVIEWED": {"DISMISSED"},
    "DISMISSED": {"REVIEWED"},
}
EVIDENCE_SECTIONS = ("accounts", "transactions", "relationships", "motifs", "paths")


def _iso(value: datetime | None) -> str | None:
    return None if value is None else isoformat_utc(value)


def _f(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def get_candidate(db: Session, ring_id: uuid.UUID) -> RingCandidate:
    c = db.get(RingCandidate, ring_id)
    if c is None:
        raise AppError(ec.NOT_FOUND, details={"resource": "ring"})
    return c


def require_intelligence(c: RingCandidate) -> None:
    if c.candidate_class != POTENTIAL_FRAUD_RING_CANDIDATE:
        raise AppError(ec.RING_INTELLIGENCE_NOT_APPLICABLE, details={"candidate_class": c.candidate_class})


def lineage(db: Session, c: RingCandidate) -> Lineage:
    scoring = db.get(ScoringRun, c.scoring_run_id)
    return Lineage(
        graph_snapshot_id=str(c.graph_snapshot_id),
        analytics_run_id=str(c.analytics_run_id),
        scoring_run_id=str(c.scoring_run_id),
        model_version=None if scoring is None else scoring.model_version,
        risk_logic_version=c.risk_logic_version,
    )


def _members(db: Session, c: RingCandidate) -> list[str]:
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


def _constituent_stats(db: Session, c: RingCandidate) -> tuple[int, datetime | None, datetime | None]:
    snap = db.get(GraphSnapshot, c.graph_snapshot_id)
    assert snap is not None
    row = db.execute(
        text(
            """
            SELECT count(*) AS n, min(t."timestamp") AS lo, max(t."timestamp") AS hi
            FROM transactions t
            JOIN community_memberships s ON s.account_id = t.source_account_id
                 AND s.analytics_run_id = :r AND s.community_id = :c
            JOIN community_memberships d ON d.account_id = t.destination_account_id
                 AND d.analytics_run_id = :r AND d.community_id = :c
            WHERE t.dataset_id = :ds AND t."timestamp" <= :cut
            """
        ),
        {"r": c.analytics_run_id, "c": c.community_id, "ds": snap.dataset_id, "cut": snap.data_cutoff},
    ).one()
    return int(row.n), row.lo, row.hi


def _latest(db: Session, model: Any, ring_id: uuid.UUID, scoring_run_id: uuid.UUID) -> Any:
    return db.execute(
        select(model).where(model.ring_id == ring_id, model.scoring_run_id == scoring_run_id)
    ).scalar_one_or_none()


def ring_view(db: Session, c: RingCandidate, active_lin: Lineage, summary_stats: bool = True) -> dict[str, Any]:
    fs = _latest(db, RingFeatureSet, c.candidate_id, c.scoring_run_id)
    rr = _latest(db, RingRiskAssessment, c.candidate_id, c.scoring_run_id)
    if fs is not None:
        n, lo, hi, size = fs.transaction_count, fs.start_time, fs.end_time, fs.ring_size
    elif summary_stats:
        n, lo, hi = _constituent_stats(db, c)
        size = len(_members(db, c))
    else:
        n, lo, hi, size = None, None, None, None
    return {
        "ring_id": str(c.candidate_id),
        "candidate_class": c.candidate_class,
        "candidate_status": c.candidate_status,
        "candidate_score": float(c.candidate_score),
        "signal_summary": c.signal_summary,
        "community_id": c.community_id,
        "member_count": size,
        "transaction_count": n,
        "start_time": _iso(lo),
        "end_time": _iso(hi),
        "temporal_span_seconds": None if lo is None or hi is None else int((hi - lo).total_seconds()),
        "ring_risk_score": None if rr is None else float(rr.ring_risk_score),
        "ring_risk_tier": None if rr is None else rr.risk_tier,
        "status_changed_by": None if c.status_changed_by is None else str(c.status_changed_by),
        "status_changed_at": _iso(c.status_changed_at),
        "analytics_version": c.analytics_version,
        "created_at": _iso(c.created_at),
        "interpretation": INTERPRETATION,
        **lineage_envelope(lineage(db, c), active_lin, c.created_at),
    }


def list_rings(
    db: Session,
    page: PageRequest,
    cap: int,
    candidate_class: str | None,
    status: str | None,
    min_score: Decimal | None,
    scoring_run_id: uuid.UUID | None,
) -> dict[str, Any]:
    if candidate_class is not None and candidate_class not in CLASSES:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "class"})
    if status is not None and status not in STATUSES:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "status"})
    if min_score is not None and not (0 <= min_score <= 1):
        raise AppError(ec.VALIDATION_ERROR, details={"field": "min_score"})
    run_id = scoring_run_id if scoring_run_id is not None else active(db).scoring_run_id
    active_lin = active_lineage(db)
    if run_id is None:
        return {**offset_page([], page, 0, cap), "interpretation": INTERPRETATION}
    q = select(RingCandidate).where(RingCandidate.scoring_run_id == run_id)
    if candidate_class is not None:
        q = q.where(RingCandidate.candidate_class == candidate_class)
    if status is not None:
        q = q.where(RingCandidate.candidate_status == status)
    if min_score is not None:
        q = q.where(RingCandidate.candidate_score >= min_score)
    total = int(db.execute(select(func.count()).select_from(q.subquery())).scalar_one())
    rows = db.execute(
        q.order_by(RingCandidate.candidate_score.desc(), RingCandidate.candidate_id)
        .offset(page.offset)
        .limit(page.page_size)
    ).scalars()
    items = [ring_view(db, c, active_lin) for c in rows]
    return {**offset_page(items, page, total, cap), "interpretation": INTERPRETATION}


def accounts(db: Session, c: RingCandidate, page: PageRequest, cap: int) -> dict[str, Any]:
    members = _members(db, c)
    selected = members[page.offset : page.offset + page.page_size]
    scores = {
        r.account_id: r.final_score
        for r in db.execute(
            text(
                "SELECT account_id, final_score FROM risk_assessments "
                "WHERE scoring_run_id = :r AND account_id = ANY(:a)"
            ),
            {"r": c.scoring_run_id, "a": selected},
        )
    }
    by_id = {a.account_id: a for a in db.execute(select(Account).where(Account.account_id.in_(selected))).scalars()}
    items = [
        {
            "account_id": a,
            "source_account_ref": by_id[a].source_account_ref if a in by_id else None,
            "account_type": by_id[a].account_type if a in by_id else None,
            "final_score": _f(scores.get(a)),
            "risk_tier": by_id[a].risk_tier if a in by_id else None,
        }
        for a in selected
    ]
    return {
        **offset_page(items, page, len(members), cap),
        **lineage_envelope(lineage(db, c), active_lineage(db), c.created_at),
    }


def transactions(db: Session, c: RingCandidate, page_size: int, cursor: str | None) -> dict[str, Any]:
    snap = db.get(GraphSnapshot, c.graph_snapshot_id)
    assert snap is not None
    params: dict[str, Any] = {
        "r": c.analytics_run_id,
        "c": c.community_id,
        "ds": snap.dataset_id,
        "cut": snap.data_cutoff,
        "n": page_size + 1,
    }
    after = ""
    if cursor is not None:
        try:
            ts, tid = decode_cursor(cursor)
        except ValueError as exc:
            raise AppError(ec.VALIDATION_ERROR, details={"field": "cursor"}) from exc
        after = 'AND (t."timestamp", t.transaction_id) > (:at, :aid)'
        params.update(at=ts, aid=tid)
    rows = db.execute(
        text(
            f"""
            SELECT t.transaction_id, t.source_account_id, t.destination_account_id, t.amount, t."timestamp",
                   t.transaction_type
            FROM transactions t
            JOIN community_memberships s ON s.account_id = t.source_account_id
                 AND s.analytics_run_id = :r AND s.community_id = :c
            JOIN community_memberships d ON d.account_id = t.destination_account_id
                 AND d.analytics_run_id = :r AND d.community_id = :c
            WHERE t.dataset_id = :ds AND t."timestamp" <= :cut {after}
            ORDER BY t."timestamp", t.transaction_id
            LIMIT :n
            """  # noqa: S608 - `after` is a fixed fragment; values are bound
        ),
        params,
    ).all()
    more = len(rows) > page_size
    rows = rows[:page_size]
    items = [
        {
            "transaction_id": r.transaction_id,
            "source_account_id": r.source_account_id,
            "destination_account_id": r.destination_account_id,
            "amount": format(r.amount, "f"),
            "timestamp": isoformat_utc(r.timestamp),
            "transaction_type": r.transaction_type,
        }
        for r in rows
    ]
    return {
        "items": items,
        "next_cursor": encode_cursor(rows[-1].timestamp, rows[-1].transaction_id) if more and rows else None,
        **lineage_envelope(lineage(db, c), active_lineage(db), c.created_at),
    }


def features(db: Session, c: RingCandidate) -> dict[str, Any]:
    require_intelligence(c)
    fs = _latest(db, RingFeatureSet, c.candidate_id, c.scoring_run_id)
    if fs is None:
        raise AppError(ec.NOT_FOUND, details={"resource": "ring_features"})
    names = {
        "RSD": "suspicious_transaction_density",
        "RC": "risk_concentration",
        "TC": "temporal_coordination",
        "MFC": "money_flow_concentration",
        "CS": "centrality_signal",
        "FI": "fan_in_signal",
        "FO": "fan_out_signal",
        "CP": "cycle_presence",
        "SPD": "suspicious_path_density",
    }
    availability = dict(fs.availability)
    counters = availability.pop("counters", {})
    return {
        "ring_id": str(c.candidate_id),
        "ring_feature_set_id": str(fs.ring_feature_set_id),
        "feature_version": fs.feature_version,
        "ring_size": fs.ring_size,
        "transaction_count": fs.transaction_count,
        "start_time": _iso(fs.start_time),
        "end_time": _iso(fs.end_time),
        "temporal_span_seconds": fs.temporal_span_seconds,
        "features": [
            {"feature": k, "name": v, "value": float(getattr(fs, v)), "availability": availability.get(k)}
            for k, v in names.items()
        ],
        "eligible_path_count": fs.eligible_path_count,
        "qualifying_path_count": fs.qualifying_path_count,
        "paths_truncated": fs.paths_truncated,
        "enumeration_counters": counters,
        **lineage_envelope(lineage(db, c), active_lineage(db), fs.computed_at),
    }


def risk(db: Session, c: RingCandidate) -> dict[str, Any]:
    require_intelligence(c)
    rr = _latest(db, RingRiskAssessment, c.candidate_id, c.scoring_run_id)
    if rr is None:
        raise AppError(ec.NOT_FOUND, details={"resource": "ring_risk"})
    availability = dict(rr.availability)
    indicators = availability.pop("temporal_indicators", {})
    weights = {
        "member_risk": 0.25,
        "transaction_risk": 0.20,
        "topology_signal": 0.20,
        "temporal_signal": 0.20,
        "money_flow_signal": 0.15,
    }
    return {
        "ring_id": str(c.candidate_id),
        "ring_risk_assessment_id": str(rr.ring_risk_assessment_id),
        "ring_risk_score": float(rr.ring_risk_score),
        "risk_tier": rr.risk_tier,
        "components": [
            {"component": k, "value": float(getattr(rr, k)), "weight": w, "availability": availability.get(k)}
            for k, w in weights.items()
        ],
        "temporal_indicators": indicators,
        "risk_logic_version": rr.risk_logic_version,
        "feature_version": rr.feature_version,
        "analytics_version": rr.analytics_version,
        "interpretation": "Ring risk assessment: an analytical score for prioritising review, separate from account "
        "risk; not a determination that the ring exists or acted criminally.",
        **lineage_envelope(lineage(db, c), active_lineage(db), rr.generated_at),
    }


@functools.lru_cache(maxsize=2)
def _context(
    engine: Engine,
    ids: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
    cutoff: datetime,
    version: str,
    budget: Budget,
) -> ring_inputs.ContextInputs:
    dataset_id, snapshot_id, analytics_run_id, scoring_run_id = ids
    return ring_inputs.load(engine, dataset_id, snapshot_id, cutoff, analytics_run_id, version, scoring_run_id, budget)


def evidence(
    db: Session, engine: Engine, budget: Budget, c: RingCandidate, section: str | None, page: PageRequest, cap: int
) -> dict[str, Any]:
    """Rebuilt on read from the stored context with the same deterministic computation (OQ-78)."""
    require_intelligence(c)
    if section is not None and section not in EVIDENCE_SECTIONS:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "section"})
    snap = db.get(GraphSnapshot, c.graph_snapshot_id)
    analytics = db.get(AnalyticsRun, c.analytics_run_id)
    scoring = db.get(ScoringRun, c.scoring_run_id)
    assert snap is not None and analytics is not None and scoring is not None and snap.data_cutoff is not None
    ctx = _context(
        engine,
        (snap.dataset_id, snap.graph_snapshot_id, analytics.analytics_run_id, scoring.scoring_run_id),
        snap.data_cutoff,
        analytics.analytics_version,
        budget,
    )
    ring = intelligence(ctx, _members(db, c))
    versions = {
        "graph_snapshot_id": str(snap.graph_snapshot_id),
        "analytics_run_id": str(analytics.analytics_run_id),
        "analytics_version": analytics.analytics_version,
        "scoring_run_id": str(scoring.scoring_run_id),
        "feature_version": scoring.feature_version,
        "model_version": scoring.model_version,
        "risk_logic_version": scoring.risk_logic_version,
        "ring_feature_version": RING_FEATURE_VERSION,
    }
    full = ring_evidence.build(ctx, ring.membership, ring.features, ring.risk, versions)
    sections = {}
    for name in EVIDENCE_SECTIONS if section is None else (section,):
        items = full[name]
        sections[name] = offset_page(items[page.offset : page.offset + page.page_size], page, len(items), cap)
    return {
        "ring_id": str(c.candidate_id),
        "source_community": {"community_id": c.community_id, "analytics_run_id": str(c.analytics_run_id)},
        "statement": full["statement"],
        "sections": sections,
        "scope": full["scope"],
        "features": full["features"],
        "feature_availability": full["feature_availability"],
        "components": full["components"],
        "component_availability": full["component_availability"],
        "ring_risk_score": full["ring_risk_score"],
        "risk_tier": full["risk_tier"],
        "versions": versions,
        **lineage_envelope(lineage(db, c), active_lineage(db), c.created_at),
    }


def member_ids(db: Session, c: RingCandidate) -> list[str]:
    return _members(db, c)
