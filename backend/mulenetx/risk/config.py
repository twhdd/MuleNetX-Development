"""Risk logic configuration (SRS §12.2–§12.7, §13.2, §9.2, §9A.3) assembled from settings (V) into the
content of a `risk_logic_versions` row. Computations read these values from the version row."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Final

from mulenetx.core.config import Settings

FORMULA_IDENTIFIER: Final[str] = "weighted-normalized-v1"
G_SET: Final[tuple[str, ...]] = ("F11", "F12", "F13", "F14", "F15", "F16", "F17", "F32")
B_SET: Final[tuple[str, ...]] = (
    "F09",
    "F20",
    "F21",
    "F22",
    "F25",
    "F26",
    "F28",
    "F29",
    "F30",
    "F35",
    "F38",
    "F39",
    "F40",
)
NORMALIZATION: Final[dict[str, str]] = {
    **dict.fromkeys(("F20", "F25", "F28", "F29", "F30", "F35", "F39"), "identity"),
    **dict.fromkeys(("F21", "F22", "F32", "F38"), "x_over_x_plus_median"),
    **dict.fromkeys(("F11", "F12", "F13", "F16", "F17", "F09", "F26", "F40"), "log1p_percentile_reference"),
    **dict.fromkeys(("F14", "F15"), "percentile_within_snapshot"),
}
RULES: Final[list[dict[str, Any]]] = [
    {
        "id": "R01",
        "conditions": [
            {"feature": "F28", "op": ">=", "value": "0.80"},
            {"quantity": "outgoing_amount_24h", "op": ">", "value": "0"},
        ],
        "contribution": "0.80",
        "priority": 30,
    },
    {
        "id": "R02",
        "conditions": [{"feature": "F25", "op": ">=", "value": "0.75"}, {"feature": "F21", "op": ">=", "value": "10"}],
        "contribution": "0.70",
        "priority": 20,
    },
    {
        "id": "R03",
        "conditions": [{"feature": "F36", "op": ">=", "value": "0.60"}],
        "contribution": "0.60",
        "priority": 10,
    },
    {
        "id": "R04",
        "conditions": [{"feature": "F37", "op": ">=", "value": "0.60"}],
        "contribution": "0.60",
        "priority": 10,
    },
    {"id": "R05", "conditions": [{"feature": "F31", "op": ">=", "value": "5"}], "contribution": "0.50", "priority": 5},
]


def risk_logic_content(settings: Settings) -> dict[str, Any]:
    s = settings
    return {
        "formula_identifier": FORMULA_IDENTIFIER,
        "configuration": {
            "weights": {
                "ml": s.risk_weight_ml,
                "graph": s.risk_weight_graph,
                "behavioral": s.risk_weight_behavioral,
                "propagation": s.risk_weight_propagation,
                "rules": s.risk_weight_rules,
            },
            "G_SET": list(G_SET),
            "B_SET": list(B_SET),
            "normalization": NORMALIZATION,
            "rounding": {"places": 7, "mode": "ROUND_HALF_EVEN", "applied": "before tier assignment"},
            "suspicious_threshold": s.suspicious_threshold,
            "unavailable_components": "contribute 0; weights are not renormalized",
        },
        "rules": {
            "rules": RULES,
            "aggregation": "maximum contribution among fired rules, capped at 1.0",
            "unavailable_input": "does not fire",
        },
        "tier_thresholds": {
            "LOW": "0.00",
            "MEDIUM": s.risk_tier_medium,
            "HIGH": s.risk_tier_high,
            "CRITICAL": s.risk_tier_critical,
        },
        "propagation_parameters": {
            "maximum_distance": s.propagation_maximum_distance,
            "decay": "1/(1+d)",
            "maximum_contribution": s.propagation_maximum_contribution,
            "source_condition": f"pre_propagation_score >= {s.suspicious_threshold}",
            "source_threshold": s.suspicious_threshold,
            "adjacency": "undirected account projection",
            "provenance_top_n": s.propagation_provenance_top_n,
        },
        "ring_parameters": {
            "candidate_weights": {
                "H": "0.35",
                "D": "0.25",
                "C": "0.15",
                "community_temporal_density": "0.15",
                "M": "0.10",
            },
            "candidate_threshold": s.candidate_threshold,
            "ring_candidate_threshold": s.ring_candidate_threshold,
            "min_candidate_community_size": s.min_candidate_community_size,
            "ring_risk_weights": {
                "member_risk": "0.25",
                "transaction_risk": "0.20",
                "topology_signal": "0.20",
                "temporal_signal": "0.20",
                "money_flow_signal": "0.15",
            },
            "mfc_top_k": s.mfc_top_k,
            "temporal_density_window_seconds": 3600,
            "temporal_density_min_transactions": 3,
        },
    }


def risk_logic_version_name(content: dict[str, Any], normalization_reference: dict[str, Any]) -> str:
    canonical = json.dumps(
        {"content": content, "reference": normalization_reference}, sort_keys=True, separators=(",", ":")
    )
    return "rl-" + hashlib.sha256(canonical.encode()).hexdigest()[:16]
