"""Flow features F32 and F34 (SRS §10.1): bounded directed simple outgoing paths of length 1..5 in the
§16.2 enumeration order (depth-first, neighbours in ascending account_id)."""

from __future__ import annotations

from mulenetx.analytics.projection import Projection
from mulenetx.features.encoding import UNAVAILABLE, Value, observed

Adjacency = dict[str, list[str]]


def adjacency(projection: Projection) -> Adjacency:
    adj: Adjacency = {}
    for p in projection.pairs:  # pairs are in (source, destination) order
        if p.source != p.destination:
            adj.setdefault(p.source, []).append(p.destination)
    return adj


def bounded_paths(adj: Adjacency, start: str, max_depth: int, max_paths: int) -> tuple[int, set[str]]:
    """Count simple outgoing paths of length 1..max_depth in depth-first pre-order (stop at `max_paths`);
    return the count and the distinct accounts strictly inside the counted paths."""
    count = 0
    inside: set[str] = set()
    path = [start]
    on_path = {start}
    iters = [iter(adj.get(start, []))]
    while iters:
        nb = next(iters[-1], None)
        if nb is None:
            iters.pop()
            on_path.discard(path.pop())
            continue
        if nb in on_path:
            continue
        count += 1
        inside.update(path[1:])
        if count >= max_paths:
            return count, inside
        if len(path) < max_depth:
            path.append(nb)
            on_path.add(nb)
            iters.append(iter(adj.get(nb, [])))
    return count, inside


def flow_features(adj: Adjacency, account: str, in_snapshot: bool, max_depth: int, cap: int) -> dict[str, Value]:
    if not in_snapshot:
        return {"F32": UNAVAILABLE, "F34": UNAVAILABLE}
    count, inside = bounded_paths(adj, account, max_depth, cap)
    return {"F32": observed(min(count, cap), count > 0), "F34": observed(len(inside), bool(inside))}
