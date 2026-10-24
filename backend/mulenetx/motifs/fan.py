"""Fan-in and fan-out with greedy non-overlapping segmentation (SRS §15.9.3)."""

from __future__ import annotations

from mulenetx.motifs.common import FAN_IN, FAN_OUT, Index, Instance, MTx
from mulenetx.motifs.confidence import confidence

WINDOW = 3600
MIN_COUNTERPARTIES = 3


def _segment(anchor: str, txs: list[MTx], motif_type: str) -> list[Instance]:
    def other(t: MTx) -> str:
        return t.source if motif_type == FAN_IN else t.destination

    txs = [t for t in txs if other(t) != anchor]  # a self-transfer has no counterparty
    out: list[Instance] = []
    i = 0
    while i < len(txs):
        t0 = txs[i].ts
        j = i
        while j < len(txs) and txs[j].ts <= t0 + WINDOW:
            j += 1
        window = txs[i:j]
        earliest: dict[str, MTx] = {}
        for t in window:
            earliest.setdefault(other(t), t)
        if len(earliest) >= MIN_COUNTERPARTIES:
            selected = sorted(earliest.values())
            span = selected[-1].ts - selected[0].ts
            value, components = confidence(motif_type, len(earliest), len(earliest) + 1, span)
            ambiguous = len({t.ts for t in selected}) < len(selected)
            out.append(Instance(motif_type, anchor, selected, WINDOW, components, value, ambiguous))
            i = j  # every transaction in the window is processed
        else:
            i += 1
    return out


def detect_fans(index: Index) -> list[Instance]:
    out: list[Instance] = []
    for account in sorted(index.inn):
        out += _segment(account, index.inn[account], FAN_IN)
    for account in sorted(index.out):
        out += _segment(account, index.out[account], FAN_OUT)
    return out
