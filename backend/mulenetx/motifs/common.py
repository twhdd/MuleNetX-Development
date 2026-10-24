"""Common motif detection contract (SRS §15.9.1): ordering, path enumeration with a per-anchor expansion
budget, maximality and instance shape. Timestamps are epoch seconds (UTC)."""

from __future__ import annotations

import bisect
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

DETECTOR_VERSION = "motifs-v1"

RAPID_PASS_THROUGH = "RAPID_PASS_THROUGH"  # noqa: S105 - motif type, not a secret
FAN_IN = "FAN_IN"
FAN_OUT = "FAN_OUT"
CIRCULAR_FLOW = "CIRCULAR_FLOW"
LAYERED_MOVEMENT = "LAYERED_MOVEMENT"
BURST_ACTIVITY = "BURST_ACTIVITY"
MOTIF_TYPES = (RAPID_PASS_THROUGH, FAN_IN, FAN_OUT, CIRCULAR_FLOW, LAYERED_MOVEMENT, BURST_ACTIVITY)


@dataclass(frozen=True, order=True)
class MTx:
    """One transaction; field order makes the natural sort the §15.9.1 `(timestamp, transaction_id)` order."""

    ts: int
    transaction_id: str
    source: str
    destination: str
    amount: Decimal = Decimal(0)


@dataclass
class Instance:
    motif_type: str
    anchor: str
    transactions: list[MTx]
    window_seconds: int
    components: dict[str, Any]
    confidence: Decimal
    order_ambiguous: bool
    truncated: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def accounts(self) -> list[str]:
        return sorted({a for t in self.transactions for a in (t.source, t.destination)})

    @property
    def tx_ids(self) -> tuple[str, ...]:
        return tuple(t.transaction_id for t in self.transactions)

    @property
    def start(self) -> int:
        return min(t.ts for t in self.transactions)

    @property
    def end(self) -> int:
        return max(t.ts for t in self.transactions)


class Index:
    """Per-account outgoing/incoming transactions in `(timestamp, transaction_id)` order."""

    def __init__(self, txs: Iterable[MTx]) -> None:
        self.txs = sorted(txs)
        self.out: dict[str, list[MTx]] = {}
        self.inn: dict[str, list[MTx]] = {}
        for t in self.txs:
            self.out.setdefault(t.source, []).append(t)
            self.inn.setdefault(t.destination, []).append(t)
        self._out_ts = {a: [t.ts for t in ts] for a, ts in self.out.items()}

    def out_from(self, account: str, min_ts: int, max_ts: int) -> list[MTx]:
        """Outgoing transactions of `account` with min_ts ≤ ts ≤ max_ts, in order."""
        lst = self.out.get(account)
        if not lst:
            return []
        keys = self._out_ts[account]
        return lst[bisect.bisect_left(keys, min_ts) : bisect.bisect_right(keys, max_ts)]

    def accounts(self) -> list[str]:
        return sorted({a for t in self.txs for a in (t.source, t.destination)})


class Budget:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.used = 0
        self.exhausted = False

    def spend(self) -> bool:
        if self.used >= self.limit:
            self.exhausted = True
            return False
        self.used += 1
        return True


def enumerate_paths(
    index: Index,
    anchor: str,
    max_hops: int,
    budget: Budget,
    next_window: Callable[[list[MTx]], tuple[int, int]],
    closes: bool,
) -> list[list[MTx]]:
    """Transaction sequences starting with an outgoing transaction of `anchor`, each hop leaving the previous
    hop's destination at a non-decreasing timestamp inside `next_window(seq)`, accounts distinct; when `closes`
    a hop may return to `anchor` and the sequence then ends. DFS in transaction order; the budget counts
    candidate hops examined. Returns every sequence reached (1..max_hops hops); callers filter."""
    found: list[list[MTx]] = []
    first_hops = index.out.get(anchor, [])

    def extend(seq: list[MTx], visited: set[str]) -> bool:
        found.append(list(seq))
        last = seq[-1]
        if len(seq) >= max_hops or last.destination == anchor:
            return True
        lo, hi = next_window(seq)
        for t in index.out_from(last.destination, max(lo, last.ts), hi):
            if not budget.spend():
                return False
            if t.destination == t.source:
                continue
            if t.destination in visited and not (closes and t.destination == anchor and len(seq) >= 2):
                continue
            seq.append(t)
            ok = extend(seq, visited | {t.destination})
            seq.pop()
            if not ok:
                return False
        return True

    for t in first_hops:
        if not budget.spend():
            break
        if t.destination == anchor:
            continue
        if not extend([t], {anchor, t.destination}):
            break
    return found


def maximal(sequences: list[tuple[str, ...]]) -> set[tuple[str, ...]]:
    """Sequences that are not a contiguous subsequence of another sequence in the list (§15.9.1 rule 4)."""
    contained: set[tuple[str, ...]] = set()
    unique = set(sequences)
    for s in unique:
        n = len(s)
        for i in range(n):
            for j in range(i + 1, n + 1):
                if j - i < n:
                    contained.add(s[i:j])
    return {s for s in unique if s not in contained}


def order_ambiguous_path(seq: list[MTx]) -> bool:
    return any(a.ts == b.ts for a, b in zip(seq, seq[1:], strict=False))
