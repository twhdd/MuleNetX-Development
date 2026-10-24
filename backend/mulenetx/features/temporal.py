"""Temporal features F27–F30 (SRS §15.3, §15.5, §15.6, §15.7)."""

from __future__ import annotations

from dataclasses import dataclass

from mulenetx.features.encoding import UNAVAILABLE, Value, observed, zero
from mulenetx.features.events import Event, in_window
from mulenetx.features.registry import Registry


def dormancy_to_activity(events: list[Event], cutoff: int, reg: Registry) -> Value:
    """§15.5: activity_24h / max(count in (T−31d, T−24h] / 30, 1); UNAVAILABLE unless that prior period has at
    least 7 distinct active UTC days."""
    p = reg.parameters
    recent = int(p["dormancy_recent_seconds"])
    prior_span = int(p["dormancy_prior_seconds"]) - recent
    activity_24h = len(in_window(events, cutoff, recent))
    prior = in_window(events, cutoff - recent, prior_span)
    active_days = {e.ts // 86400 for e in prior}
    if len(active_days) < int(p["dormancy_min_active_days"]):
        return UNAVAILABLE
    mean_daily = len(prior) / float(p["dormancy_prior_days"])
    return observed(activity_24h / max(mean_daily, 1.0), True)


def rapid_in_out_ratio(events: list[Event], cutoff: int, reg: Registry) -> Value:
    """§15.3: each inbound event (in (timestamp, id) order) is matched to the earliest unmatched outbound event
    in [t, t + 3600 s]; each outbound matches at most once. Matched inbound events in the 24 h window divided by
    max(inbound count in the window, 1)."""
    follow = int(reg.parameters["rapid_follow_seconds"])
    window = reg.window("F28")
    inbound = [e for e in events if e.incoming and e.ts <= cutoff]
    outbound = [e for e in events if e.outgoing and e.ts <= cutoff]
    used: set[int] = set()
    start = 0
    matched_in_window = 0
    lo = cutoff - window
    for inc in inbound:
        while start < len(outbound) and outbound[start].ts < inc.ts:
            start += 1
        for j in range(start, len(outbound)):
            out = outbound[j]
            if out.ts > inc.ts + follow:
                break
            if j in used or out.tx_id == inc.tx_id:
                continue
            used.add(j)
            if lo < inc.ts <= cutoff:
                matched_in_window += 1
            break
    inbound_in_window = sum(1 for e in inbound if lo < e.ts <= cutoff)
    return observed(matched_in_window / max(inbound_in_window, 1), inbound_in_window > 0)


def short_lived_activity_score(events: list[Event], cutoff: int, reg: Registry) -> Value:
    """§15.7: periods split by gaps ≥ 24 h; completed if such a gap follows before T; short-lived if ≤ 72 h."""
    gap = int(reg.parameters["inactivity_gap_seconds"])
    max_short = int(reg.parameters["short_lived_max_seconds"])
    times = [e.ts for e in events if e.ts <= cutoff]
    if not times:
        return zero()
    periods: list[tuple[int, int, bool]] = []
    start = prev = times[0]
    for t in times[1:]:
        if t - prev >= gap:
            periods.append((start, prev, True))
            start = t
        prev = t
    periods.append((start, prev, cutoff - prev >= gap))
    completed = [p for p in periods if p[2]]
    short = sum(1 for s, e, _ in completed if e - s <= max_short)
    return observed(short / max(len(completed), 1), bool(completed))


@dataclass(frozen=True)
class OutTx:
    ts: int
    tx_id: str
    destination: str


OutIndex = dict[str, list[OutTx]]


def build_out_index(rows: list[tuple[int, str, str, str]], cutoff: int, window: int) -> OutIndex:
    """rows: (ts, tx_id, source, destination) sorted by (ts, tx_id); keeps transactions in (T − window, T]."""
    index: OutIndex = {}
    lo = cutoff - window
    for ts, tx_id, src, dst in rows:
        if lo < ts <= cutoff and src != dst:
            index.setdefault(src, []).append(OutTx(ts, tx_id, dst))
    return index


def cycle_events(
    account: str, index: OutIndex, cutoff: int, reg: Registry, max_expansions: int
) -> tuple[set[str], bool]:
    """§15.6: transactions involving `account` that lie on a time-ordered directed simple cycle starting and
    ending at the account, 2..5 hops, non-decreasing timestamps, total span ≤ 24 h, inside the 7-day window.
    Returns (cycle transaction IDs touching the account, truncated)."""
    p = reg.parameters
    min_hops, max_hops, max_span = int(p["cycle_min_hops"]), int(p["cycle_max_hops"]), int(p["cycle_max_span_seconds"])
    found: set[str] = set()
    expansions = 0
    for first in index.get(account, []):
        stack: list[tuple[str, int, int, frozenset[str]]] = [
            (first.destination, first.ts, 1, frozenset({account, first.destination}))
        ]
        while stack:
            node, last_ts, hops, visited = stack.pop()
            for nxt in reversed(index.get(node, [])):
                if nxt.ts < last_ts or nxt.ts - first.ts > max_span:
                    continue
                expansions += 1
                if expansions > max_expansions:
                    return found, True
                if nxt.destination == account:
                    if min_hops <= hops + 1 <= max_hops:
                        found.add(first.tx_id)
                        found.add(nxt.tx_id)
                    continue
                if nxt.destination in visited or hops + 1 >= max_hops:
                    continue
                stack.append((nxt.destination, nxt.ts, hops + 1, visited | {nxt.destination}))
    return found, False


def cyclic_activity_score(
    account: str, events: list[Event], index: OutIndex, cutoff: int, reg: Registry, max_expansions: int
) -> Value:
    window_events = in_window(events, cutoff, reg.window("F29"))
    if not window_events:
        return zero()
    found, _truncated = cycle_events(account, index, cutoff, reg, max_expansions)
    return observed(len(found) / max(len(window_events), 1), True)
