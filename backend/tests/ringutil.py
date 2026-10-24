"""ring_basic fixture → ContextInputs (no database); motifs are detected from the fixture's transactions."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from mulenetx.flow.analytic_paths import AnalyticProjection, Budget, Tx
from mulenetx.motifs.common import MTx
from mulenetx.motifs.service import detect
from mulenetx.rings.inputs import ContextInputs, MotifRef
from tests.conftest import make_settings
from tests.flowutil import SNAPSHOT, context

FIXTURE = Path(__file__).parent / "fixtures" / "ring_basic" / "expected.json"


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(FIXTURE.read_text())
    return data


def inputs(budget: Budget | None = None) -> ContextInputs:
    fx = load()
    hops: dict[tuple[str, str], list[Tx]] = {}
    for t in fx["transactions"]:
        hops.setdefault((t["src"], t["dst"]), []).append(
            Tx(t["id"], datetime.fromtimestamp(t["ts"], UTC), Decimal(t["amount"]))
        )
    found = detect(
        [MTx(t["ts"], t["id"], t["src"], t["dst"], Decimal(t["amount"])) for t in fx["transactions"]], make_settings()
    )
    motifs = [MotifRef(m.motif_type, m.anchor, frozenset(m.accounts), frozenset(m.tx_ids)) for m in found]
    return ContextInputs(
        run=context(fx["final_scores"]),
        projection=AnalyticProjection(SNAPSHOT, hops),
        pagerank_pct=fx["pagerank_pct"],
        betweenness_pct=fx["betweenness_pct"],
        motifs=motifs,
        budget=budget or Budget(),
        communities=fx["communities"],
    )
