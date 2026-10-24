"""Row validation and rejection codes (SRS §7.3, §7.4)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Final

REJECTION_CODES: Final[tuple[str, ...]] = (
    "MISSING_COLUMN",
    "TYPE_ERROR",
    "INVALID_ACCOUNT_ID",
    "INVALID_AMOUNT",
    "INVALID_TIMESTAMP",
    "INVALID_TYPE",
    "INVALID_LABEL",
    "FIELD_TOO_LONG",
)
MAX_SAMPLES_PER_REASON: Final[int] = 100


class RowRejectedError(Exception):
    def __init__(self, code: str) -> None:
        if code not in REJECTION_CODES:
            raise ValueError(code)
        super().__init__(code)
        self.code = code


@dataclass
class RejectionSummary:
    """Reason-code histogram plus up to 100 sample row ordinals per reason; row content is never copied."""

    counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    samples: dict[str, list[int]] = field(default_factory=lambda: defaultdict(list))

    def add(self, code: str, ordinal: int) -> None:
        self.counts[code] += 1
        bucket = self.samples[code]
        if len(bucket) < MAX_SAMPLES_PER_REASON:
            bucket.append(ordinal)

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    def as_json(self) -> dict[str, Any]:
        return {
            "counts": {k: self.counts[k] for k in sorted(self.counts)},
            "samples": {k: self.samples[k] for k in sorted(self.samples)},
        }
