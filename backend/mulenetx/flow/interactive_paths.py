"""Interactive bounded path queries over TRANSFERRED_TO (SRS §16.1–§16.8).

SHORTEST: breadth-first by hop count (all paths of the minimum length). ALL: depth-first enumeration of simple
paths (neighbours in ascending account_id). Both run on the subgraph pruned by forward distance from the
source plus backward distance to the destination (≤ max_depth). Results are ordered by §16.5 and cut to
`max_results`; exceeding the time budget returns 408 with no partial result.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.core.runtime import Runtime
from mulenetx.graph import cypher
from mulenetx.graph.neighborhood import _Deadline, _run

Edge = tuple[str, str]


@dataclass
class Subgraph:
    out: dict[str, list[str]]
    micros: dict[Edge, int]
    tx_count: dict[Edge, int]
    dist_from_source: dict[str, int]
    dist_to_destination: dict[str, int]


def _bfs(
    rt: Runtime,
    deadline: _Deadline,
    sid: str,
    start: str,
    depth: int,
    forward: bool,
    edges: dict[Edge, tuple[int, int]],
) -> dict[str, int]:
    dist = {start: 0}
    frontier = [start]
    query = cypher.OUT_NEIGHBORS if forward else cypher.IN_NEIGHBORS
    for d in range(1, depth + 1):
        if not frontier:
            break
        rows = _run(rt, deadline, query, {"ids": sorted(frontier), "sid": sid})
        nxt: set[str] = set()
        for r in rows:
            edges[(r["src"], r["dst"])] = (int(r["micros"]), int(r["tx_count"]))
            other = r["dst"] if forward else r["src"]
            if other not in dist:
                dist[other] = d
                nxt.add(other)
        frontier = sorted(nxt)
    return dist


def pruned_subgraph(
    rt: Runtime, deadline: _Deadline, sid: str, source: str, destination: str, max_depth: int
) -> Subgraph:
    edges: dict[Edge, tuple[int, int]] = {}
    df = _bfs(rt, deadline, sid, source, max_depth, True, edges)
    db = _bfs(rt, deadline, sid, destination, max_depth, False, edges)
    keep = {n for n in df if n in db and df[n] + db[n] <= max_depth}
    out: dict[str, list[str]] = {}
    micros: dict[Edge, int] = {}
    counts: dict[Edge, int] = {}
    for (u, v), (m, n) in edges.items():
        if u in keep and v in keep and u != v:
            out.setdefault(u, []).append(v)
            micros[(u, v)] = m
            counts[(u, v)] = n
    for u in out:
        out[u].sort()
    return Subgraph(out, micros, counts, df, db)


def shortest_paths(g: Subgraph, source: str, destination: str, check: Callable[[], None]) -> list[list[str]]:
    if destination not in g.dist_from_source or destination not in g.dist_to_destination:
        return []
    length = g.dist_from_source[destination]
    paths: list[list[str]] = []
    stack: list[list[str]] = [[source]]
    while stack:
        check()
        path = stack.pop()
        node = path[-1]
        if node == destination:
            paths.append(path)
            continue
        for nb in reversed(g.out.get(node, [])):
            if g.dist_from_source.get(nb) == len(path) and g.dist_to_destination.get(nb, 99) == length - len(path):
                stack.append([*path, nb])
    return paths


def all_paths(g: Subgraph, source: str, destination: str, max_depth: int, check: Callable[[], None]) -> list[list[str]]:
    paths: list[list[str]] = []
    path = [source]
    on_path = {source}
    iters = [iter(g.out.get(source, []))]
    while iters:
        check()
        nb = next(iters[-1], None)
        if nb is None:
            iters.pop()
            on_path.discard(path.pop())
            continue
        if nb in on_path:
            continue
        hops = len(path)
        if nb == destination:
            paths.append([*path, nb])
            continue
        if hops + g.dist_to_destination.get(nb, max_depth + 1) > max_depth:
            continue
        path.append(nb)
        on_path.add(nb)
        iters.append(iter(g.out.get(nb, [])))
    return paths


class Budget:
    def __init__(self, seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self.end = clock() + seconds
        self.clock = clock
        self.n = 0

    def __call__(self) -> None:
        self.n += 1
        if self.n % 256 == 0 and self.clock() > self.end:
            raise AppError(ec.QUERY_TIMEOUT)
