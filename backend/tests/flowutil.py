"""In-memory analytical projections from fixture CSVs (PaySim columns; no database)."""

from __future__ import annotations

import csv
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from mulenetx.flow.analytic_paths import AnalyticProjection, Tx
from mulenetx.flow.vocabulary import ScoringContext
from tests.ingestutil import fixture_csv

SNAPSHOT = uuid.UUID("00000000-0000-5000-8000-0000000000aa")
RUN = uuid.UUID("00000000-0000-4000-8000-0000000000bb")
T0 = datetime(2020, 1, 1, tzinfo=UTC)


def projection_from_edges(edges: list[tuple[str, str, str]], snapshot: uuid.UUID = SNAPSHOT) -> AnalyticProjection:
    """edges: (source, destination, amount); one transaction each, in order."""
    hops: dict[tuple[str, str], list[Tx]] = {}
    for i, (src, dst, amount) in enumerate(edges):
        hops.setdefault((src, dst), []).append(Tx(f"t{i:05d}", T0 + timedelta(hours=i), Decimal(amount)))
    return AnalyticProjection(snapshot, hops)


def projection_from_fixture(name: str) -> AnalyticProjection:
    with fixture_csv(name).open(newline="") as f:
        return projection_from_edges([(r["nameOrig"], r["nameDest"], r["amount"]) for r in csv.DictReader(f)])


def context(scores: dict[str, str], threshold: str = "0.50", snapshot: uuid.UUID = SNAPSHOT) -> ScoringContext:
    return ScoringContext(RUN, snapshot, Decimal(threshold), {a: Decimal(s) for a, s in scores.items()})
