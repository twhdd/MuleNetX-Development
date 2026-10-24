"""RiskService: one scoring run (SRS §11 inference, §12, §13 in the order of §12.1).

1. ml_score → 2. graph_signal → 3. behavioral_signal → 4. rule_signal → 5. pre_propagation (per account)
→ 6. propagated_risk (from step 5 of other accounts) → 7. final_score → 8. risk_tier.
Assessments are written first; the scoring run becomes SUCCEEDED (and visible) in the stage's final
transaction, after every row is written (§6.6).
"""

from __future__ import annotations

import json
import logging
import math
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import numpy as np
from sqlalchemy import text

from mulenetx.core.decimal import D, round7
from mulenetx.core.percentile import percentile_rank
from mulenetx.core.runtime import Runtime
from mulenetx.core.timeutil import utcnow
from mulenetx.db.models.lineage import AnalyticsRun, GraphSnapshot, ModelVersion, RiskLogicVersion, ScoringRun
from mulenetx.features.registry import load as load_registry
from mulenetx.features.service import feature_snapshot_id
from mulenetx.ml.inference import ModelIncompatibleError, ModelUnavailableError, ScoringRequest, load_model
from mulenetx.propagation.bfs import propagated_risk
from mulenetx.propagation.service import run_propagation
from mulenetx.risk.components import component
from mulenetx.risk.compose import Components, Weights, compose
from mulenetx.risk.rules import evaluate as evaluate_rules

logger = logging.getLogger("mulenetx.risk")
ASSESSMENT_NAMESPACE = uuid.UUID("6f1c2a3e-5b7d-4e0a-9c1f-2d8b4a6e0f13")


def assessment_id(scoring_run_id: uuid.UUID, account_id: str) -> uuid.UUID:
    return uuid.uuid5(ASSESSMENT_NAMESPACE, f"assessment|{scoring_run_id}|{account_id}")


@dataclass
class MLState:
    model_version: str | None
    reason: str | None
    scores: dict[str, Decimal]


def _snapshot_percentiles(rt: Runtime, analytics_run_id: uuid.UUID) -> dict[str, dict[str, float]]:
    """F14/F15 for risk composition: percentile rank within the snapshot (§8.4)."""
    with rt.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT account_id, pagerank_raw, betweenness_raw FROM account_graph_metrics "
                "WHERE analytics_run_id = :r ORDER BY account_id"
            ),
            {"r": analytics_run_id},
        ).all()
    ids = [r.account_id for r in rows]
    pr = percentile_rank([float(r.pagerank_raw) for r in rows])
    bc = percentile_rank([float(r.betweenness_raw) for r in rows])
    return {a: {"F14": p, "F15": b} for a, p, b in zip(ids, pr, bc, strict=True)}


def _outgoing_24h(rt: Runtime, dataset_id: uuid.UUID, cutoff: datetime) -> dict[str, float]:
    with rt.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT source_account_id AS a, sum(amount) AS total FROM transactions WHERE dataset_id = :d "
                'AND "timestamp" > :lo AND "timestamp" <= :c GROUP BY source_account_id'
            ),
            {"d": dataset_id, "lo": cutoff - timedelta(hours=24), "c": cutoff},
        ).all()
    return {r.a: float(r.total) for r in rows}


class RiskService:
    def __init__(self, runtime: Runtime) -> None:
        self.rt = runtime

    def ml_scores(
        self, model_version: str | None, feature_version: str, accounts: list[str], matrix: np.ndarray
    ) -> MLState:
        if model_version is None:
            return MLState(None, "NO_COMPATIBLE_MODEL", {})
        with self.rt.session_factory() as db:
            mv = db.get(ModelVersion, model_version)
        if mv is None:
            return MLState(None, "MODEL_UNAVAILABLE", {})
        try:
            model = load_model(mv, ScoringRequest(feature_version=feature_version))
            probs = model.predict(matrix) if len(accounts) else np.zeros(0)
        except ModelIncompatibleError:
            return MLState(None, "MODEL_INCOMPATIBLE", {})
        except (ModelUnavailableError, OSError, ValueError):
            logger.exception("inference failed")
            return MLState(None, "MODEL_UNAVAILABLE", {})
        return MLState(model_version, None, {a: round7(D(float(p))) for a, p in zip(accounts, probs, strict=True)})

    def score(
        self,
        scoring_run_id: uuid.UUID,
        snapshot: GraphSnapshot,
        analytics: AnalyticsRun,
        risk_logic: RiskLogicVersion,
        model_version: str | None,
        check: Callable[[], None] | None = None,
    ) -> int:
        """Write every assessment and provenance row of the scoring run (status stays RUNNING); return the count."""
        reg = load_registry()
        cutoff = snapshot.data_cutoff
        fsid = feature_snapshot_id(analytics.analytics_run_id, reg.feature_version, cutoff)
        with self.rt.engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT account_id, feature_values, feature_states FROM account_feature_values "
                    "WHERE feature_snapshot_id = :f ORDER BY account_id"
                ),
                {"f": fsid},
            ).all()
        accounts = [r.account_id for r in rows]
        matrix = np.array([r.feature_values for r in rows], dtype=np.float64) if rows else np.zeros((0, 42))
        ml = self.ml_scores(model_version, reg.feature_version, accounts, matrix)
        cfg = risk_logic.configuration
        weights = Weights.from_config(cfg["weights"])
        normalization = cfg["normalization"]
        reference = risk_logic.normalization_reference.get("features", {})
        percentiles = _snapshot_percentiles(self.rt, analytics.analytics_run_id)
        outgoing = _outgoing_24h(self.rt, snapshot.dataset_id, cutoff)
        rules = risk_logic.rules["rules"]

        per_account: dict[str, dict[str, Any]] = {}
        pre_scores: dict[str, Decimal] = {}
        for r in rows:
            values = dict(zip(reg.ids, r.feature_values, strict=True))
            states = dict(zip(reg.ids, r.feature_states, strict=True))
            g = component(cfg["G_SET"], values, states, normalization, reference, percentiles.get(r.account_id))
            b = component(cfg["B_SET"], values, states, normalization, reference, None)
            rr = evaluate_rules(rules, values, states, {"outgoing_amount_24h": outgoing.get(r.account_id, 0.0)})
            comps = Components(
                ml.scores.get(r.account_id), g.score, g.available, b.score, b.available, rr.score, rr.available
            )
            pre = compose(comps, Decimal(0), weights, risk_logic.tier_thresholds).pre_propagation_score
            pre_scores[r.account_id] = pre
            per_account[r.account_id] = {"components": comps, "graph": g, "behavioral": b, "rules": rr}
        if check is not None:
            check()
        received = run_propagation(
            self.rt.engine, snapshot.dataset_id, cutoff, pre_scores, risk_logic.propagation_parameters
        )
        if check is not None:
            check()
        now = utcnow()
        analytics_version = analytics.analytics_version
        raw = self.rt.engine.raw_connection()
        try:
            cur = raw.cursor()
            cur.execute("SELECT purge_scoring_outputs(%s)", (scoring_run_id,))
            with cur.copy(
                "COPY risk_assessments (assessment_id, scoring_run_id, account_id, as_of, graph_snapshot_id, "
                "feature_snapshot_id, model_version, feature_version, analytics_version, risk_logic_version, ml_score, "
                "graph_signal_score, behavioral_signal_score, rule_signal_score, pre_propagation_score, "
                "propagated_risk, final_score, risk_tier, signal_availability, fired_rules, generated_at) FROM STDIN"
            ) as copy:
                for account in accounts:
                    data = per_account[account]
                    ac: Components = data["components"]
                    prop = propagated_risk(received.get(account))
                    result = compose(ac, prop, weights, risk_logic.tier_thresholds)
                    availability = {
                        "ml": {
                            "state": "AVAILABLE" if ac.ml_score is not None else "UNAVAILABLE",
                            "reason": ml.reason,
                        },
                        "graph": {
                            "state": "AVAILABLE" if ac.graph_available else "UNAVAILABLE",
                            "inputs": _inputs(data["graph"].inputs),
                        },
                        "behavioral": {
                            "state": "AVAILABLE" if ac.behavioral_available else "UNAVAILABLE",
                            "inputs": _inputs(data["behavioral"].inputs),
                        },
                        "rules": {"state": "AVAILABLE" if ac.rules_available else "UNAVAILABLE"},
                        "propagation": {"state": "AVAILABLE"},
                        "signal_coverage": format(result.signal_coverage, "f"),
                        "max_attainable_score": format(result.max_attainable_score, "f"),
                    }
                    copy.write_row(
                        (
                            assessment_id(scoring_run_id, account),
                            scoring_run_id,
                            account,
                            cutoff,
                            snapshot.graph_snapshot_id,
                            fsid,
                            ml.model_version,
                            reg.feature_version,
                            analytics_version,
                            risk_logic.risk_logic_version,
                            ac.ml_score,
                            ac.graph,
                            ac.behavioral,
                            ac.rules,
                            result.pre_propagation_score,
                            result.propagated_risk,
                            result.final_score,
                            result.risk_tier,
                            json.dumps(availability),
                            json.dumps(data["rules"].fired),
                            now,
                        )
                    )
            with cur.copy(
                "COPY propagation_contributions (scoring_run_id, account_id, source_account_id, source_assessment_id, "
                "distance, source_score, decay_value, contribution, rank) FROM STDIN"
            ) as copy:
                for receiver in sorted(received):
                    if receiver not in per_account:
                        continue
                    for rank, c in enumerate(received[receiver], start=1):
                        copy.write_row(
                            (
                                scoring_run_id,
                                receiver,
                                c.source_account_id,
                                assessment_id(scoring_run_id, c.source_account_id),
                                c.distance,
                                c.source_score,
                                c.decay_value,
                                c.contribution,
                                rank,
                            )
                        )
            raw.commit()
        except BaseException:
            raw.rollback()
            raise
        finally:
            raw.close()
        return len(accounts)


def _inputs(normalized: dict[str, float | None]) -> dict[str, float | None]:
    return {
        k: (None if v is None or (isinstance(v, float) and math.isnan(v)) else round(v, 7))
        for k, v in normalized.items()
    }


def create_scoring_run(
    rt: Runtime,
    scoring_run_id: uuid.UUID,
    snapshot: GraphSnapshot,
    analytics: AnalyticsRun,
    risk_logic_version: str,
    model_version: str | None,
) -> None:
    reg = load_registry()
    with rt.session_factory() as db:
        if db.get(ScoringRun, scoring_run_id) is not None:
            return
        db.add(
            ScoringRun(
                scoring_run_id=scoring_run_id,
                graph_snapshot_id=snapshot.graph_snapshot_id,
                analytics_run_id=analytics.analytics_run_id,
                as_of=snapshot.data_cutoff,
                feature_version=reg.feature_version,
                feature_snapshot_id=feature_snapshot_id(
                    analytics.analytics_run_id, reg.feature_version, snapshot.data_cutoff
                ),
                model_version=model_version,
                risk_logic_version=risk_logic_version,
                started_at=utcnow(),
                status="RUNNING",
            )
        )
        db.commit()
