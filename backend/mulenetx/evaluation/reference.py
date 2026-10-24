"""Reference construction (SRS §28.7): reference rings are the weakly connected components of the subgraph
induced by reference-positive test transactions with at least 3 reference-positive accounts."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from mulenetx.core import ids

REFERENCE_CONSTRUCTION_VERSION = "reference-v1"
MIN_RING_ACCOUNTS = 3


@dataclass(frozen=True)
class ReferenceRing:
    ring_id: str
    members: frozenset[str]


def reference_rings(positive_edges: Iterable[tuple[str, str]]) -> list[ReferenceRing]:
    parent: dict[str, str] = {}

    def find(a: str) -> str:
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for u, v in positive_edges:
        ru, rv = find(u), find(v)
        if ru != rv:
            parent[max(ru, rv)] = min(ru, rv)
    groups: dict[str, set[str]] = {}
    for a in list(parent):
        groups.setdefault(find(a), set()).add(a)
    rings = [
        ReferenceRing(str(ids.reference_ring_id(REFERENCE_CONSTRUCTION_VERSION, sorted(m))), frozenset(m))
        for m in groups.values()
        if len(m) >= MIN_RING_ACCOUNTS
    ]
    return sorted(rings, key=lambda r: r.ring_id)
