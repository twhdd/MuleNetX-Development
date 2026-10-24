"""Classification metrics (SRS §11.10) on one split. Undefined metrics are reported as null."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score


def _ranked(y: np.ndarray, scores: np.ndarray, ids: list[str]) -> list[int]:
    order = sorted(range(len(ids)), key=lambda i: (-float(scores[i]), ids[i]))
    return [int(y[i]) for i in order]


def precision_at(y_ranked: list[int], k: int) -> float | None:
    if k <= 0 or not y_ranked:
        return None
    top = y_ranked[:k]
    return sum(top) / len(top)


def max_f1_threshold(y: np.ndarray, scores: np.ndarray) -> float:
    """Operating threshold chosen on validation: the score cut that maximizes F1 (predict positive ≥ t)."""
    best_t, best_f1 = 0.5, -1.0
    for t in sorted({float(s) for s in scores}, reverse=True):
        pred = scores >= t
        tp = int(np.sum(pred & (y == 1)))
        fp = int(np.sum(pred & (y == 0)))
        fn = int(np.sum(~pred & (y == 1)))
        denom = 2 * tp + fp + fn
        f1 = (2 * tp / denom) if denom else 0.0
        if f1 > best_f1:
            best_t, best_f1 = t, f1
    return best_t


def evaluate(y: np.ndarray, scores: np.ndarray, ids: list[str], threshold: float) -> dict[str, Any]:
    n = len(y)
    if n == 0:
        return {"sample_count": 0, "available": False}
    positives = int(np.sum(y == 1))
    pred = scores >= threshold
    tp = int(np.sum(pred & (y == 1)))
    fp = int(np.sum(pred & (y == 0)))
    fn = int(np.sum(~pred & (y == 1)))
    tn = int(np.sum(~pred & (y == 0)))
    both = 0 < positives < n
    ranked = _ranked(y, scores, ids)

    def ratio(a: int, b: int) -> float | None:
        return a / b if b else None

    precision = ratio(tp, tp + fp)
    recall = ratio(tp, tp + fn)
    f1 = (
        None
        if precision is None or recall is None or (precision + recall) == 0
        else (2 * precision * recall / (precision + recall))
    )
    return {
        "sample_count": n,
        "available": True,
        "prevalence": positives / n,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": float(roc_auc_score(y, scores)) if both else None,
        "pr_auc": float(average_precision_score(y, scores)) if both else None,
        "pr_auc_baseline": positives / n,
        "precision_at_100": precision_at(ranked, 100),
        "precision_at_top_1pct": precision_at(ranked, max(1, math.ceil(0.01 * n))),
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "false_positive_rate": ratio(fp, fp + tn),
        "false_negative_rate": ratio(fn, fn + tp),
        "threshold": threshold,
    }
