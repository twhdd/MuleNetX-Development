"""Transactional features F01–F10, F20–F26, F35, F38–F42 (SRS §10.1, §15.2, §15.4).

Every formula reads its window, cap and ε from the registry; inputs are the account's events with
timestamp ≤ T in (timestamp, transaction_id) order.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict

from mulenetx.features.encoding import Value, observed, zero
from mulenetx.features.events import Event, in_window
from mulenetx.features.registry import Registry


def _median(values: list[float]) -> float:
    v = sorted(values)
    n = len(v)
    mid = n // 2
    return v[mid] if n % 2 else (v[mid - 1] + v[mid]) / 2.0


def _sample_std(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = math.fsum(values) / n
    return math.sqrt(math.fsum((x - mean) ** 2 for x in values) / (n - 1))


def _gaps(events: list[Event]) -> list[int]:
    return [b.ts - a.ts for a, b in zip(events, events[1:], strict=False)]


def lifetime_features(events: list[Event], reg: Registry) -> dict[str, Value]:
    n = len(events)
    incoming = [e for e in events if e.incoming]
    outgoing = [e for e in events if e.outgoing]
    amounts = [e.amount for e in events]
    in_amount = math.fsum(e.amount for e in incoming)
    out_amount = math.fsum(e.amount for e in outgoing)
    out: dict[str, Value] = {
        "F01": observed(n, n > 0),
        "F02": observed(len(incoming), bool(incoming)),
        "F03": observed(len(outgoing), bool(outgoing)),
        "F04": observed(in_amount, bool(incoming)),
        "F05": observed(out_amount, bool(outgoing)),
        "F06": observed(math.fsum(amounts) / n, True) if n else zero(),
        "F07": observed(_median(amounts), True) if n else zero(),
        "F08": observed(_sample_std(amounts), True) if n >= 2 else zero(),
    }
    if in_amount == 0:
        out["F09"] = observed(0.0, bool(incoming))
    else:
        out["F09"] = observed(min(in_amount / max(out_amount, reg.epsilon), reg.cap("F09")), True)
    if n:
        counts = Counter(e.tx_type for e in events)
        entropy = -math.fsum((c / n) * math.log2(c / n) for c in counts.values())
        out["F10"] = observed(entropy + 0.0, True)
    else:
        out["F10"] = zero()
    gaps = _gaps(events)
    out["F24"] = observed(math.fsum(gaps) / len(gaps), True) if gaps else zero()
    out["F42"] = observed((events[-1].ts - events[0].ts) / 3600.0, True) if n else zero()
    return out


def window_features(events: list[Event], cutoff: int, reg: Registry) -> dict[str, Value]:
    out: dict[str, Value] = {}
    # F20 transaction_concentration (7 d)
    w20 = in_window(events, cutoff, reg.window("F20"))
    total20 = math.fsum(e.amount for e in w20)
    if w20 and total20 > 0:
        per_cp: dict[str, float] = defaultdict(float)
        for e in w20:
            per_cp[e.counterparty] += e.amount
        out["F20"] = observed(max(per_cp.values()) / total20, True)
    else:
        out["F20"] = observed(0.0, bool(w20))
    # F21 velocity_24h, F22 velocity_7d
    w21 = in_window(events, cutoff, reg.window("F21"))
    out["F21"] = observed(len(w21), bool(w21))
    w22 = in_window(events, cutoff, reg.window("F22"))
    out["F22"] = observed(len(w22) / 7.0, bool(w22))
    # F23 volume_change_7d: current (T−7d, T], previous (T−14d, T−7d]
    half = reg.window("F23") // 2
    v_cur = math.fsum(e.amount for e in in_window(events, cutoff, half))
    v_prev = math.fsum(e.amount for e in in_window(events, cutoff - half, half))
    cap23 = reg.cap("F23")
    if v_cur == 0 and v_prev == 0:
        out["F23"] = zero()
    elif v_prev == 0:
        out["F23"] = observed(cap23, True)
    else:
        out["F23"] = observed(min((v_cur - v_prev) / v_prev, cap23), True)
    # F25 short_interval_ratio (7 d)
    w25 = in_window(events, cutoff, reg.window("F25"))
    gaps = _gaps(w25)
    short = sum(1 for g in gaps if g <= reg.parameters["short_interval_seconds"])
    out["F25"] = observed(short / max(len(gaps), 1), bool(gaps))
    # F26 burst_score: 168 UTC hour buckets ending with the bucket containing T, empty buckets included (§15.4)
    buckets = int(reg.parameters["burst_buckets"])
    last_bucket = cutoff - cutoff % 3600
    first_bucket = last_bucket - (buckets - 1) * 3600
    counts: Counter[int] = Counter()
    for e in events:
        if first_bucket <= e.ts <= cutoff:
            counts[(e.ts - first_bucket) // 3600] += 1
    if counts:
        mean = sum(counts.values()) / buckets
        out["F26"] = observed(max(counts.values()) / max(mean, 1.0), True)
    else:
        out["F26"] = zero()
    # F35 flow_concentration (7 d, outgoing)
    w35 = [e for e in in_window(events, cutoff, reg.window("F35")) if e.outgoing]
    out_total = math.fsum(e.amount for e in w35)
    if out_total > 0:
        per_dst: dict[str, float] = defaultdict(float)
        for e in w35:
            per_dst[e.counterparty] += e.amount
        out["F35"] = observed(max(per_dst.values()) / out_total, True)
    else:
        out["F35"] = observed(0.0, bool(w35))
    # F38 unique_counterparty_count, F39 counterparty_turnover_ratio (7 d)
    w38 = in_window(events, cutoff, reg.window("F38"))
    distinct = len({e.counterparty for e in w38})
    out["F38"] = observed(distinct, bool(w38))
    w39 = in_window(events, cutoff, reg.window("F39"))
    out["F39"] = observed(len({e.counterparty for e in w39}) / max(len(w39), 1), bool(w39))
    # F40 incoming_outgoing_velocity_ratio (24 h)
    w40 = in_window(events, cutoff, reg.window("F40"))
    n_in = sum(1 for e in w40 if e.incoming)
    n_out = sum(1 for e in w40 if e.outgoing)
    out["F40"] = observed(n_in / max(n_out, 1), n_in > 0)
    # F41 amount_to_count_ratio (7 d)
    w41 = in_window(events, cutoff, reg.window("F41"))
    out["F41"] = observed(math.fsum(e.amount for e in w41) / max(len(w41), 1), bool(w41))
    return out


def compute(events: list[Event], cutoff: int, reg: Registry) -> dict[str, Value]:
    return {**lifetime_features(events, reg), **window_features(events, cutoff, reg)}
