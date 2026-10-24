"""Metric rows of the four evaluation levels (SRS §28.7). Zero denominators give 0 with UNAVAILABLE; metrics
whose labels PaySim does not provide are NOT_MEASURABLE with a reason, never 0."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from mulenetx.ml.metrics import evaluate as classification


@dataclass
class Row:
    level: str
    metric: str
    value: float | None
    sample_count: int
    availability: str = "AVAILABLE"
    details: dict[str, Any] = field(default_factory=dict)


def ratio(level: str, metric: str, num: float, den: float, sample: int, **details: Any) -> Row:
    if den == 0:
        return Row(level, metric, 0.0, sample, "UNAVAILABLE", {"reason": "zero denominator", **details})
    return Row(level, metric, num / den, sample, "AVAILABLE", details)


def not_measurable(level: str, metric: str, reason: str) -> Row:
    return Row(level, metric, None, 0, "UNAVAILABLE", {"state": "NOT_MEASURABLE", "reason": reason})


def ranking_rows(
    level: str, labels: list[int], scores: list[float], ids: list[str], extra: dict[str, Any]
) -> list[Row]:
    """PR-AUC, ROC-AUC, precision@100 and precision at top 1% on one population (§28.7)."""
    y, s = np.array(labels, dtype=np.int32), np.array(scores, dtype=np.float64)
    m = classification(y, s, ids, 0.5) if len(labels) else {"sample_count": 0}
    n = len(labels)
    rows = []
    for metric in ("pr_auc", "roc_auc", "precision_at_100", "precision_at_top_1pct"):
        value = m.get(metric)
        if value is None:
            reason = "no samples" if n == 0 else "single class in the population"
            rows.append(Row(level, metric, None, n, "UNAVAILABLE", {"reason": reason}))
        else:
            rows.append(Row(level, metric, float(value), n, "AVAILABLE", {}))
    positives = int(sum(labels))
    rows.append(
        Row(
            level,
            "prevalence",
            positives / n if n else 0.0,
            n,
            "AVAILABLE" if n else "UNAVAILABLE",
            {"positives": positives, "pr_auc_baseline": positives / n if n else None, **extra},
        )
    )
    return rows


def average_precision(ranked_positive: list[bool]) -> float | None:
    """AP of a ranked list (rings ranked by ring risk; positive = matched)."""
    hits, total = 0, 0.0
    for i, positive in enumerate(ranked_positive, start=1):
        if positive:
            hits += 1
            total += hits / i
    return total / hits if hits else None


def distribution(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "count": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
    }
