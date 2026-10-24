"""Bounded risk propagation (SRS §13.2–§13.4).

Sources: accounts with pre_propagation_score ≥ the source threshold in the same scoring run. One bounded BFS
per source over the undirected account projection (depth ≤ maximum_distance); contribution(source, d) =
min(s / (1 + d), maximum_contribution). Each receiver keeps its contributions ranked by contribution
descending, then smaller d, then smaller source_account_id; rank 1 determines propagated_risk (max
aggregation, no additive amplification). An account is never its own source. The result is independent of
the order in which accounts or edges are supplied.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from mulenetx.core.decimal import ZERO, D, round7


@dataclass(frozen=True)
class Contribution:
    source_account_id: str
    distance: int
    source_score: Decimal
    decay_value: Decimal
    contribution: Decimal


def undirected_adjacency(pairs: list[tuple[str, str]]) -> dict[str, list[str]]:
    adj: dict[str, set[str]] = {}
    for a, b in pairs:
        if a == b:
            continue
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    return {k: sorted(v) for k, v in adj.items()}


def propagate(
    adjacency: Mapping[str, list[str]],
    pre_scores: Mapping[str, Decimal],
    source_threshold: Decimal,
    max_distance: int,
    max_contribution: Decimal,
    top_n: int,
) -> dict[str, list[Contribution]]:
    """receiver → its top-N contributions in rank order."""
    received: dict[str, list[Contribution]] = {}
    for source in sorted(a for a, s in pre_scores.items() if s >= source_threshold):
        s = pre_scores[source]
        seen = {source: 0}
        queue = deque([source])
        while queue:
            node = queue.popleft()
            d = seen[node]
            if d >= max_distance:
                continue
            for nb in sorted(adjacency.get(node, ())):
                if nb in seen:
                    continue
                seen[nb] = d + 1
                queue.append(nb)
        for receiver, d in seen.items():
            if receiver == source:
                continue
            decay = Decimal(1) / Decimal(1 + d)
            value = round7(min(D(s) * decay, max_contribution))
            received.setdefault(receiver, []).append(Contribution(source, d, round7(D(s)), round7(decay), value))
    for receiver, items in received.items():
        items.sort(key=lambda c: (-c.contribution, c.distance, c.source_account_id))
        received[receiver] = items[:top_n]
    return received


def propagated_risk(contributions: list[Contribution] | None) -> Decimal:
    return contributions[0].contribution if contributions else round7(ZERO)
