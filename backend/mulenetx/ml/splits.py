"""Chronological split boundaries and windows (SRS §11.4, §11.5)."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from mulenetx.core.timeutil import floor_to_resolution, isoformat_utc

SPLITS = ("train", "val", "test")


@dataclass(frozen=True)
class SplitBoundaries:
    t0: datetime
    t_train: datetime
    t_val: datetime
    t_test: datetime
    resolution_seconds: int

    def windows(self) -> dict[str, tuple[datetime, datetime]]:
        """Half-open windows (start, end]: train (T0 − r, T_train], val (T_train, T_val], test (T_val, T_test]."""
        r = timedelta(seconds=self.resolution_seconds)
        return {
            "train": (self.t0 - r, self.t_train),
            "val": (self.t_train, self.t_val),
            "test": (self.t_val, self.t_test),
        }

    def cutoff(self, split: str) -> datetime:
        return self.windows()[split][1]

    def as_json(self) -> dict[str, str | int]:
        return {
            "T_0": isoformat_utc(self.t0),
            "T_train": isoformat_utc(self.t_train),
            "T_val": isoformat_utc(self.t_val),
            "T_test": isoformat_utc(self.t_test),
            "resolution_seconds": self.resolution_seconds,
        }

    def window_table(self) -> dict[str, dict[str, str]]:
        return {
            split: {
                "window": f"({isoformat_utc(lo)}, {isoformat_utc(hi)}]",
                "feature_cutoff": isoformat_utc(hi),
                "graph_snapshot": f"TRAINING_SPLIT, data_cutoff <= {isoformat_utc(hi)}",
            }
            for split, (lo, hi) in self.windows().items()
        }


def percentile_timestamp(sorted_epochs: Sequence[int], q: float) -> int:
    """Nearest-rank percentile of the transaction timestamps (multiset) (OQ-47)."""
    n = len(sorted_epochs)
    rank = max(1, math.ceil(q * n))
    return sorted_epochs[rank - 1]


def compute_boundaries(
    sorted_epochs: Sequence[int], resolution_seconds: int, q_train: float = 0.70, q_val: float = 0.85
) -> SplitBoundaries:
    if not sorted_epochs:
        raise ValueError("no transactions")

    def dt(epoch: int) -> datetime:
        return datetime.fromtimestamp(epoch, UTC)

    t_train = floor_to_resolution(dt(percentile_timestamp(sorted_epochs, q_train)), resolution_seconds)
    t_val = floor_to_resolution(dt(percentile_timestamp(sorted_epochs, q_val)), resolution_seconds)
    return SplitBoundaries(dt(sorted_epochs[0]), t_train, t_val, dt(sorted_epochs[-1]), resolution_seconds)
