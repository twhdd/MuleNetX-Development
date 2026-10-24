"""Motif fixtures (tests/fixtures/motifs/*.json): transactions with second-level timestamps and hand-computed
expected instances."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from mulenetx.motifs.common import Instance, MTx
from mulenetx.motifs.service import detect
from tests.conftest import make_settings

DIR = Path(__file__).parent / "fixtures" / "motifs"


def load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((DIR / f"{name}.json").read_text())
    return data


def transactions(name: str) -> list[MTx]:
    return [MTx(t["ts"], t["id"], t["src"], t["dst"], Decimal(t["amount"])) for t in load(name)["transactions"]]


def summary(inst: Instance) -> dict[str, Any]:
    return {
        "type": inst.motif_type,
        "anchor": inst.anchor,
        "txs": list(inst.tx_ids),
        "confidence": format(inst.confidence, "f"),
        "order_ambiguous": inst.order_ambiguous,
        "temporal_match": inst.components["temporal_match"],
    }


def run(name: str, **settings: Any) -> list[dict[str, Any]]:
    found = detect(transactions(name), make_settings(**settings))
    return sorted((summary(i) for i in found), key=lambda s: (s["type"], s["anchor"], s["txs"]))


def expected(name: str) -> list[dict[str, Any]]:
    return sorted(load(name)["expected"], key=lambda s: (s["type"], s["anchor"], s["txs"]))
