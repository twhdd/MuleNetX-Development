"""Burst activity against the trailing 168-bucket hourly baseline (SRS §15.9.6)."""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction

from mulenetx.motifs.common import BURST_ACTIVITY, Index, Instance, MTx
from mulenetx.motifs.confidence import confidence

BUCKET = 3600
BASELINE_BUCKETS = 168
MIN_COUNT = 5
MULTIPLIER = 3


def detect_bursts(index: Index) -> list[Instance]:
    per_account: dict[str, dict[int, list[MTx]]] = defaultdict(lambda: defaultdict(list))
    for t in index.txs:
        per_account[t.source][t.ts // BUCKET].append(t)
        if t.destination != t.source:
            per_account[t.destination][t.ts // BUCKET].append(t)
    out: list[Instance] = []
    for account in sorted(per_account):
        buckets = per_account[account]
        for h in sorted(buckets):
            count = len(buckets[h])
            if count < MIN_COUNT:
                continue
            trailing = sum(len(buckets.get(b, ())) for b in range(h - BASELINE_BUCKETS + 1, h + 1))
            mean = Fraction(trailing, BASELINE_BUCKETS)
            if count < MULTIPLIER * max(mean, Fraction(1)):
                continue
            txs = sorted(buckets[h])
            counterparties = {x for t in txs for x in (t.source, t.destination)} - {account}
            participants = len(counterparties) + 1
            value, components = confidence(BURST_ACTIVITY, count, participants, txs[-1].ts - txs[0].ts)
            components["baseline_mean"] = str(round(float(mean), 7))
            components["bucket_count"] = count
            ambiguous = len({t.ts for t in txs}) < len(txs)
            out.append(Instance(BURST_ACTIVITY, account, txs, BUCKET, components, value, ambiguous))
    return out
