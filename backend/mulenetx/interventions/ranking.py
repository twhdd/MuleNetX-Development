"""Intervention score and the five-key deterministic sort (SRS §16A.14)."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Any

from mulenetx.core.decimal import round7
from mulenetx.interventions.metrics import Metrics
from mulenetx.interventions.pool import K_MAX

WEIGHTS = {
    "flow_disruption_percentage": "0.45",
    "normalized_risk_reduction": "0.25",
    "normalized_connectivity_disruption": "0.20",
    "normalized_path_disruption": "0.10",
    "normalized_intervention_cost": "-0.10",
}


def configuration(max_candidates: int, max_depth: int, max_paths: int, max_expansions: int) -> dict[str, Any]:
    return {
        "version": "intervention-ranking-v1",
        "weights": WEIGHTS,
        "clamp": [0, 1],
        "k_max": K_MAX,
        "intervention_max_candidates": max_candidates,
        "analytic_bounds": {"max_depth": max_depth, "max_paths": max_paths, "max_expansions": max_expansions},
        "sort": [
            "intervention_score desc",
            "flow_disruption_percentage desc",
            "normalized_risk_reduction desc",
            "intervention_cost asc",
            "candidate_id asc",
        ],
        "cost": {
            "ACCOUNT_REMOVAL": 1,
            "INTERMEDIARY_REMOVAL": 1,
            "EDGE_REMOVAL": 1,
            "ACCOUNT_SET_REMOVAL": "|targets|",
        },
        "rounding": "half-even to 7 dp for normalized values; flows NUMERIC(20,4)",
    }


def configuration_hash(config: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def score(m: Metrics) -> Decimal:
    raw = sum(
        (Decimal(w) * getattr(m, name) for name, w in WEIGHTS.items()),
        Decimal(0),
    )
    return round7(min(Decimal(1), max(Decimal(0), raw)))


def sort_key(intervention_score: Decimal, m: Metrics, candidate_id: str) -> tuple[Any, ...]:
    return (
        -intervention_score,
        -m.flow_disruption_percentage,
        -m.normalized_risk_reduction,
        m.intervention_cost,
        candidate_id,
    )
