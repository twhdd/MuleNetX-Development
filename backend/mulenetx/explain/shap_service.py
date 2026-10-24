"""ExplainabilityService (SRS §14): SHAP for the ML component, computed on demand from the persisted feature
vector and the assessment's model artifact, then cached immutably in `shap_explanations`."""

from __future__ import annotations

import logging
import math
import time
import uuid
from typing import Any

import numpy as np
import xgboost as xgb
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.core.lineage import lineage_envelope
from mulenetx.core.logging import log_fields
from mulenetx.core.timeutil import utcnow
from mulenetx.db.models.account_analytics import AccountFeatureValues, RiskAssessment, ShapExplanation
from mulenetx.db.models.lineage import ModelVersion
from mulenetx.db.repositories.context import active_lineage
from mulenetx.db.repositories.risk import _lineage, get_assessment
from mulenetx.features.encoding import State
from mulenetx.features.registry import load as load_registry
from mulenetx.ml.inference import ModelIncompatibleError, ModelUnavailableError, ScoringRequest, load_model

logger = logging.getLogger("mulenetx.explain")
EXPLAINER = "tree_shap_path_dependent"
OUTPUT_SPACE = "LOG_ODDS"
STATEMENT = (
    "This explanation covers the ML component (ml_score) only, which carries 50% of the "
    "pre-propagation score. It does not explain the other risk components and is not proof of fraud "
    "or criminality."
)


def _assessment(db: Session, account_id: str, assessment_id: uuid.UUID | None) -> RiskAssessment:
    if assessment_id is None:
        return get_assessment(db, account_id, None)
    ra = db.get(RiskAssessment, assessment_id)
    if ra is None or ra.account_id != account_id:
        raise AppError(ec.NOT_FOUND, details={"resource": "assessment"})
    return ra


def compute(mv: ModelVersion, ra: RiskAssessment, afv: AccountFeatureValues) -> tuple[float, list[dict[str, Any]]]:
    model = load_model(mv, ScoringRequest(feature_version=ra.feature_version))
    reg = load_registry()
    x = np.array([afv.feature_values], dtype=np.float64)
    assert model.booster is not None
    # XGBoost's built-in TreeSHAP (path-dependent); the last column is the bias (expected value) in log-odds.
    contribs = np.asarray(model.booster.predict(xgb.DMatrix(x, missing=float("nan")), pred_contribs=True))[0]
    values = contribs[:-1]
    base = float(contribs[-1])
    values = values.astype(np.float64)
    total = float(np.sum(np.abs(values)))
    contributions = []
    for i, fd in enumerate(reg.features):
        v = afv.feature_values[i]
        s = float(values[i])
        contributions.append(
            {
                "feature_id": fd.id,
                "name": fd.name,
                "value": None if math.isnan(v) else v,
                "state": State(afv.feature_states[i]).name,
                "shap": s,
                "direction": "increases" if s > 0 else ("decreases" if s < 0 else "none"),
                "relative_importance": abs(s) / total if total > 0 else 0.0,
            }
        )
    return base, contributions


def explain(db: Session, account_id: str, assessment_id: uuid.UUID | None, top_n: int) -> dict[str, Any]:
    ra = _assessment(db, account_id, assessment_id)
    if ra.ml_score is None or ra.model_version is None:
        raise AppError(ec.EXPLANATION_NOT_AVAILABLE)
    afv = db.get(AccountFeatureValues, (ra.feature_snapshot_id, ra.account_id))
    if afv is None or afv.feature_version != ra.feature_version:
        raise AppError(ec.EXPLANATION_VERSION_MISMATCH)
    cached = db.get(ShapExplanation, ra.assessment_id)
    if cached is None:
        mv = db.get(ModelVersion, ra.model_version)
        if mv is None:
            raise AppError(ec.MODEL_UNAVAILABLE)
        started = time.perf_counter()
        try:
            base, contributions = compute(mv, ra, afv)
        except ModelUnavailableError as exc:
            raise AppError(ec.MODEL_UNAVAILABLE) from exc
        except ModelIncompatibleError as exc:
            raise AppError(ec.EXPLANATION_VERSION_MISMATCH) from exc
        log_fields(
            logger,
            logging.INFO,
            "shap computed",
            assessment_id=str(ra.assessment_id),
            SHAP_duration=round(time.perf_counter() - started, 4),
        )
        db.execute(
            insert(ShapExplanation)
            .values(
                assessment_id=ra.assessment_id,
                model_version=ra.model_version,
                feature_version=ra.feature_version,
                explainer=EXPLAINER,
                base_value=base,
                output_space=OUTPUT_SPACE,
                contributions=contributions,
                computed_at=utcnow(),
            )
            .on_conflict_do_nothing()
        )
        db.commit()
        cached = db.execute(
            select(ShapExplanation).where(ShapExplanation.assessment_id == ra.assessment_id)
        ).scalar_one()
    if cached.model_version != ra.model_version or cached.feature_version != ra.feature_version:
        raise AppError(ec.EXPLANATION_VERSION_MISMATCH)
    ranked = sorted(cached.contributions, key=lambda c: (-abs(c["shap"]), c["feature_id"]))
    return {
        "assessment_id": str(ra.assessment_id),
        "account_id": ra.account_id,
        "model_version": cached.model_version,
        "feature_version": cached.feature_version,
        "explainer": cached.explainer,
        "output_space": cached.output_space,
        "base_value": cached.base_value,
        "ml_score": float(ra.ml_score),
        "explains": "ML_COMPONENT_ONLY",
        "statement": STATEMENT,
        "top_n": top_n,
        "contributions": ranked[:top_n],
        "feature_count": len(cached.contributions),
        **lineage_envelope(_lineage(ra, db), active_lineage(db), cached.computed_at),
    }
