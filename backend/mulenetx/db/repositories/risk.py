"""Risk read model (SRS §19.7, §19.12, §15.8): assessments, history, provenance, features, temporal."""

from __future__ import annotations

import math
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.core.lineage import Lineage, lineage_envelope
from mulenetx.core.pagination import PageRequest
from mulenetx.core.timeutil import isoformat_utc
from mulenetx.db.models.account_analytics import AccountFeatureValues, PropagationContribution, RiskAssessment
from mulenetx.db.models.lineage import ScoringRun
from mulenetx.db.repositories.context import active, active_lineage
from mulenetx.features.encoding import State
from mulenetx.features.registry import load as load_registry

TEMPORAL_IDS = ("F21", "F22", "F23", "F24", "F25", "F26", "F27", "F28", "F29", "F30")


def _f(x: Any) -> float | None:
    return None if x is None else float(x)


def _lineage(ra: RiskAssessment, db: Session) -> Lineage:
    sr = db.get(ScoringRun, ra.scoring_run_id)
    return Lineage(
        graph_snapshot_id=str(ra.graph_snapshot_id),
        analytics_run_id=None if sr is None else str(sr.analytics_run_id),
        scoring_run_id=str(ra.scoring_run_id),
        model_version=ra.model_version,
        risk_logic_version=ra.risk_logic_version,
    )


def assessment_view(ra: RiskAssessment, db: Session, active_lin: Lineage) -> dict[str, Any]:
    lineage = _lineage(ra, db)
    availability = dict(ra.signal_availability)
    return {
        "assessment_id": str(ra.assessment_id),
        "account_id": ra.account_id,
        "scoring_run_id": str(ra.scoring_run_id),
        "as_of": isoformat_utc(ra.as_of),
        "ml_score": _f(ra.ml_score),
        "graph_signal_score": float(ra.graph_signal_score),
        "behavioral_signal_score": float(ra.behavioral_signal_score),
        "rule_signal_score": float(ra.rule_signal_score),
        "pre_propagation_score": float(ra.pre_propagation_score),
        "propagated_risk": float(ra.propagated_risk),
        "final_score": float(ra.final_score),
        "risk_tier": ra.risk_tier,
        "signal_availability": {
            k: v for k, v in availability.items() if k not in ("signal_coverage", "max_attainable_score")
        },
        "signal_coverage": float(availability.get("signal_coverage", 0)),
        "max_attainable_score": float(availability.get("max_attainable_score", 0)),
        "fired_rules": ra.fired_rules,
        "model_version": ra.model_version,
        "feature_version": ra.feature_version,
        "analytics_version": ra.analytics_version,
        "risk_logic_version": ra.risk_logic_version,
        "generated_at": isoformat_utc(ra.generated_at),
        "interpretation": "Analytical risk score; not a determination of fraud, mule status or criminality.",
        **lineage_envelope(lineage, active_lin, ra.generated_at),
    }


def _scoring_run(db: Session, scoring_run_id: uuid.UUID | None) -> uuid.UUID:
    if scoring_run_id is not None:
        return scoring_run_id
    sid = active(db).scoring_run_id
    if sid is None:
        raise AppError(ec.RISK_NOT_AVAILABLE)
    return sid


def get_assessment(db: Session, account_id: str, scoring_run_id: uuid.UUID | None) -> RiskAssessment:
    run_id = _scoring_run(db, scoring_run_id)
    ra = db.execute(
        select(RiskAssessment).where(RiskAssessment.account_id == account_id, RiskAssessment.scoring_run_id == run_id)
    ).scalar_one_or_none()
    if ra is None:
        raise AppError(ec.RISK_NOT_AVAILABLE)
    sr = db.get(ScoringRun, ra.scoring_run_id)
    if sr is None or sr.status != "SUCCEEDED":
        raise AppError(ec.RISK_NOT_AVAILABLE)  # assessments become visible only with their succeeded run (§6.6)
    return ra


def risk(db: Session, account_id: str, scoring_run_id: uuid.UUID | None) -> dict[str, Any]:
    return assessment_view(get_assessment(db, account_id, scoring_run_id), db, active_lineage(db))


def history(db: Session, account_id: str, page: PageRequest) -> tuple[list[dict[str, Any]], int]:
    base = (
        select(RiskAssessment)
        .join(ScoringRun, ScoringRun.scoring_run_id == RiskAssessment.scoring_run_id)
        .where(RiskAssessment.account_id == account_id, ScoringRun.status == "SUCCEEDED")
    )
    total = int(db.execute(select(func.count()).select_from(base.subquery())).scalar_one())
    rows = db.execute(
        base.order_by(RiskAssessment.as_of.desc(), RiskAssessment.generated_at.desc(), RiskAssessment.assessment_id)
        .offset(page.offset)
        .limit(page.page_size)
    ).scalars()
    lin = active_lineage(db)
    return [assessment_view(ra, db, lin) for ra in rows], total


def propagation(db: Session, account_id: str, scoring_run_id: uuid.UUID | None) -> dict[str, Any]:
    ra = get_assessment(db, account_id, scoring_run_id)
    rows = db.execute(
        select(PropagationContribution)
        .where(
            PropagationContribution.scoring_run_id == ra.scoring_run_id,
            PropagationContribution.account_id == account_id,
        )
        .order_by(PropagationContribution.rank)
    ).scalars()
    items = [
        {
            "rank": r.rank,
            "source_account_id": r.source_account_id,
            "source_assessment_id": str(r.source_assessment_id),
            "distance": r.distance,
            "source_score": float(r.source_score),
            "decay_value": float(r.decay_value),
            "contribution": float(r.contribution),
        }
        for r in rows
    ]
    return {
        "account_id": account_id,
        "assessment_id": str(ra.assessment_id),
        "propagated_risk": float(ra.propagated_risk),
        "contributions": items,
        **lineage_envelope(_lineage(ra, db), active_lineage(db), ra.generated_at),
    }


def _feature_items(afv: AccountFeatureValues, ids: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    reg = load_registry()
    items = []
    for i, fd in enumerate(reg.features):
        if ids is not None and fd.id not in ids:
            continue
        value = afv.feature_values[i]
        state = State(afv.feature_states[i]).name
        items.append(
            {
                "feature_id": fd.id,
                "name": fd.name,
                "value": None if math.isnan(value) else value,
                "state": state,
                "window": fd.window,
                "unit": fd.unit,
                "description": fd.description,
            }
        )
    return items


def _features_for(
    db: Session, account_id: str, scoring_run_id: uuid.UUID | None
) -> tuple[RiskAssessment, AccountFeatureValues]:
    ra = get_assessment(db, account_id, scoring_run_id)
    afv = db.get(AccountFeatureValues, (ra.feature_snapshot_id, account_id))
    if afv is None:
        raise AppError(ec.NOT_FOUND, details={"resource": "feature_vector"})
    return ra, afv


def features(db: Session, account_id: str, scoring_run_id: uuid.UUID | None) -> dict[str, Any]:
    ra, afv = _features_for(db, account_id, scoring_run_id)
    return {
        "account_id": account_id,
        "feature_snapshot_id": str(afv.feature_snapshot_id),
        "feature_version": afv.feature_version,
        "as_of": isoformat_utc(afv.as_of),
        "features": _feature_items(afv),
        **lineage_envelope(_lineage(ra, db), active_lineage(db), afv.created_at),
    }


def temporal(db: Session, account_id: str, scoring_run_id: uuid.UUID | None) -> dict[str, Any]:
    """The persisted F21–F30 with states and windows (§15.8); arbitrary cutoffs are not accepted."""
    ra, afv = _features_for(db, account_id, scoring_run_id)
    return {
        "account_id": account_id,
        "cutoff": isoformat_utc(afv.as_of),
        "feature_version": afv.feature_version,
        "features": _feature_items(afv, TEMPORAL_IDS),
        **lineage_envelope(_lineage(ra, db), active_lineage(db), afv.created_at),
    }
