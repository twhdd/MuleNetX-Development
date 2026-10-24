"""Lineage and staleness (SRS §19.12).

Analytical responses carry `{lineage, computed_at, is_stale}`. `is_stale` is true when any lineage
element differs from the active context. Elements that do not apply to a response are omitted
(None) and are not compared.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from mulenetx.core.timeutil import isoformat_utc

LINEAGE_FIELDS = ("graph_snapshot_id", "analytics_run_id", "scoring_run_id", "model_version", "risk_logic_version")


@dataclass(frozen=True)
class Lineage:
    graph_snapshot_id: str | None = None
    analytics_run_id: str | None = None
    scoring_run_id: str | None = None
    model_version: str | None = None
    risk_logic_version: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return asdict(self)


def is_stale(lineage: Lineage, active: Lineage | None) -> bool:
    for name in LINEAGE_FIELDS:
        value = getattr(lineage, name)
        if value is None:
            continue
        active_value = None if active is None else getattr(active, name)
        if str(value) != (None if active_value is None else str(active_value)):
            return True
    return False


def lineage_envelope(lineage: Lineage, active: Lineage | None, computed_at: datetime | None) -> dict[str, Any]:
    return {
        "lineage": lineage.as_dict(),
        "computed_at": None if computed_at is None else isoformat_utc(computed_at),
        "is_stale": is_stale(lineage, active),
    }
