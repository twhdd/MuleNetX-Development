"""Normalization reference (SRS §12.2): per input feature, the empirical distribution over the training
population at T_train as a 101-point quantile table (of log1p(x) for the log1p inputs) and the median of the
strictly positive values (for the x/(x+m) inputs)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from mulenetx.risk.config import NORMALIZATION

QUANTILE_POINTS = 101


def quantile_table(values: list[float]) -> list[float]:
    """101 quantiles (0..100 %) with linear interpolation; empty input → empty table."""
    if not values:
        return []
    arr = np.sort(np.asarray(values, dtype=np.float64))
    return [float(q) for q in np.quantile(arr, np.linspace(0.0, 1.0, QUANTILE_POINTS), method="linear")]


def build(feature_ids: list[str], matrix: np.ndarray, states: np.ndarray) -> dict[str, Any]:
    """`matrix`/`states`: training-split feature rows (registry order). Unavailable values are ignored."""
    out: dict[str, Any] = {
        "quantile_points": QUANTILE_POINTS,
        "population": "training split at T_train",
        "features": {},
    }
    for fid, method in sorted(NORMALIZATION.items()):
        col = feature_ids.index(fid)
        column = (
            [
                float(v)
                for v, st in zip(matrix[:, col], states[:, col], strict=True)
                if st in (0, 1) and not math.isnan(v)
            ]
            if len(matrix)
            else []
        )
        entry: dict[str, Any] = {"method": method, "sample_count": len(column)}
        if method == "log1p_percentile_reference":
            entry["quantiles_log1p"] = quantile_table([math.log1p(v) for v in column])
        elif method == "x_over_x_plus_median":
            positive = sorted(v for v in column if v > 0)
            entry["median_positive"] = float(np.median(positive)) if positive else None
        out["features"][fid] = entry
    return out
