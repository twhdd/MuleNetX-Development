"""Path motifs: rapid pass-through (§15.9.2), circular flow (§15.9.4), layered movement (§15.9.5)."""

from __future__ import annotations

from mulenetx.motifs.common import (
    CIRCULAR_FLOW,
    LAYERED_MOVEMENT,
    RAPID_PASS_THROUGH,
    Budget,
    Index,
    Instance,
    MTx,
    enumerate_paths,
    maximal,
    order_ambiguous_path,
)
from mulenetx.motifs.confidence import confidence

PER_HOP_WINDOW = 900
SPAN_WINDOW = 86_400


def _instance(motif_type: str, seq: list[MTx], window: int, truncated: bool) -> Instance:
    hops = len(seq)
    span = seq[-1].ts - seq[0].ts
    participants = len({a for t in seq for a in (t.source, t.destination)})
    gaps = [b.ts - a.ts for a, b in zip(seq, seq[1:], strict=False)] if motif_type == RAPID_PASS_THROUGH else None
    value, components = confidence(motif_type, min(hops, 5), participants, span, gaps)
    return Instance(
        motif_type, seq[0].source, list(seq), window, components, value, order_ambiguous_path(seq), truncated
    )


def detect_path_motifs(index: Index, max_depth: int, budget_per_anchor: int) -> list[Instance]:
    """All three path motif types, maximal sequences only."""
    candidates: dict[str, list[tuple[list[MTx], bool]]] = {
        RAPID_PASS_THROUGH: [],
        CIRCULAR_FLOW: [],
        LAYERED_MOVEMENT: [],
    }
    for anchor in index.accounts():
        # rapid pass-through: each successive gap in [0, 900]
        b = Budget(budget_per_anchor)
        rapid = enumerate_paths(
            index, anchor, max_depth, b, lambda s: (s[-1].ts, s[-1].ts + PER_HOP_WINDOW), closes=False
        )
        candidates[RAPID_PASS_THROUGH] += [(s, b.exhausted) for s in rapid if 2 <= len(s) <= 5]
        # circular and layered share one span-bounded enumeration (total span ≤ 86,400 s)
        b = Budget(budget_per_anchor)
        spans = enumerate_paths(index, anchor, max_depth, b, lambda s: (s[-1].ts, s[0].ts + SPAN_WINDOW), closes=True)
        for s in spans:
            closed = s[-1].destination == anchor
            if closed and 3 <= len(s) <= 5:
                candidates[CIRCULAR_FLOW].append((s, b.exhausted))
            elif not closed and 4 <= len(s) <= 5:
                candidates[LAYERED_MOVEMENT].append((s, b.exhausted))
    out: list[Instance] = []
    for motif_type, seqs in candidates.items():
        keep = maximal([tuple(t.transaction_id for t in s) for s, _ in seqs])
        window = PER_HOP_WINDOW if motif_type == RAPID_PASS_THROUGH else SPAN_WINDOW
        emitted: set[tuple[str, ...]] = set()
        for s, truncated in seqs:
            key = tuple(t.transaction_id for t in s)
            if key in keep and key not in emitted:
                emitted.add(key)
                out.append(_instance(motif_type, s, window, truncated))
    return out
