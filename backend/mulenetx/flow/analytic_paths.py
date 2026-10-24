"""Analytical path enumeration over one snapshot's account projection (SRS §3.5, §16.2–§16.5, §16.7.2).

The single implementation used by rings, interventions and evaluation. Enumeration is bounded only by the
deterministic counters `analytic_max_depth`, `analytic_max_paths` and `analytic_max_expansions`, never by
wall-clock time; exhausting a counter stops at a fixed point of the enumeration order and sets `truncated`.

Algorithm for a ring scope [PLAN DEFAULT, derived from §3.5]:
1. forward DFS from each ring member and backward DFS into each member (members and neighbours in ascending
   `account_id` order) collecting simple paths of length 1..max_depth whose endpoints are both suspicious;
2. ring scope = members ∪ accounts on those paths;
3. eligible paths = simple paths of length 1..max_depth with ≥ 1 endpoint in the ring, enumerated the same way
   inside the scope subgraph;
4. in-scope qualifying paths = eligible paths whose endpoints are both suspicious.
Paths found from both directions are deduplicated by account sequence. Each of the two enumerations (steps 1
and 3) has its own counters at the configured limits (OQ-74).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Engine, text

from mulenetx.flow.vocabulary import ScoringContext, TransactionRef, is_suspicious_account, is_suspicious_transaction

Path = tuple[str, ...]


@dataclass(frozen=True)
class Tx:
    transaction_id: str
    timestamp: datetime
    amount: Decimal


@dataclass(frozen=True)
class Budget:
    max_depth: int = 5
    max_paths: int = 10_000
    max_expansions: int = 1_000_000


class AnalyticProjection:
    """Directed simple graph of one snapshot: ordered adjacency plus supporting transactions per hop."""

    def __init__(self, graph_snapshot_id: uuid.UUID, hops: dict[tuple[str, str], list[Tx]]) -> None:
        self.graph_snapshot_id = graph_snapshot_id
        ordered = {k: sorted(v, key=lambda t: (t.timestamp, t.transaction_id)) for k, v in hops.items()}
        self.hops = {k: v for k, v in ordered.items() if k[0] != k[1]}
        # self-transfers take no part in paths but are still transactions between members (§9.3)
        self.loops = {k[0]: v for k, v in ordered.items() if k[0] == k[1]}
        out: dict[str, list[str]] = {}
        inn: dict[str, list[str]] = {}
        for src, dst in self.hops:
            out.setdefault(src, []).append(dst)
            inn.setdefault(dst, []).append(src)
        self.out = {k: sorted(v) for k, v in out.items()}
        self.inn = {k: sorted(v) for k, v in inn.items()}

    def supporting(self, path: Path) -> Iterator[tuple[str, str, Tx]]:
        for u, v in zip(path, path[1:], strict=False):
            for t in self.hops[(u, v)]:
                yield u, v, t


def load_projection(
    engine: Engine, graph_snapshot_id: uuid.UUID, dataset_id: uuid.UUID, data_cutoff: datetime
) -> AnalyticProjection:
    """The snapshot's transactions (timestamp ≤ data_cutoff) grouped per ordered account pair."""
    hops: dict[tuple[str, str], list[Tx]] = {}
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT source_account_id AS src, destination_account_id AS dst, transaction_id, "timestamp", amount
                FROM transactions
                WHERE dataset_id = :d AND "timestamp" <= :c
                ORDER BY source_account_id, destination_account_id, "timestamp", transaction_id
                """
            ),
            {"d": dataset_id, "c": data_cutoff},
        )
        for r in rows:
            hops.setdefault((r.src, r.dst), []).append(Tx(r.transaction_id, r.timestamp, r.amount))
    return AnalyticProjection(graph_snapshot_id, hops)


class _Counter:
    def __init__(self, budget: Budget) -> None:
        self.budget = budget
        self.paths = 0
        self.expansions = 0
        self.truncated = False

    def expand(self) -> bool:
        if self.expansions >= self.budget.max_expansions:
            self.truncated = True
            return False
        self.expansions += 1
        return True

    def take_path(self) -> bool:
        if self.paths >= self.budget.max_paths:
            self.truncated = True
            return False
        self.paths += 1
        return True


def _enumerate(
    proj: AnalyticProjection,
    members: list[str],
    allowed: Callable[[str], bool],
    accept: Callable[[Path], bool],
    counter: _Counter,
) -> dict[Path, None]:
    """Simple paths of length 1..max_depth starting (forward) or ending (backward) at a member, restricted to
    `allowed` accounts, kept when `accept(path)`. Insertion order is the deterministic enumeration order."""
    found: dict[Path, None] = {}
    max_depth = counter.budget.max_depth

    def dfs(start: str, adjacency: dict[str, list[str]], forward: bool) -> bool:
        stack: list[tuple[str, int]] = [(start, 0)]
        seq: list[str] = [start]
        on_path = {start}
        while stack:
            node, i = stack[-1]
            neighbours = adjacency.get(node, [])
            if i >= len(neighbours) or len(seq) > max_depth:
                stack.pop()
                on_path.discard(seq.pop())
                continue
            stack[-1] = (node, i + 1)
            nxt = neighbours[i]
            if nxt in on_path or not allowed(nxt):
                continue
            if not counter.expand():
                return False
            seq.append(nxt)
            on_path.add(nxt)
            stack.append((nxt, 0))
            path: Path = tuple(seq) if forward else tuple(reversed(seq))
            if path not in found and accept(path):
                if not counter.take_path():
                    return False
                found[path] = None
        return True

    for m in members:
        if not dfs(m, proj.out, True):
            break
        if not dfs(m, proj.inn, False):
            break
    return found


@dataclass
class ScopeResult:
    members: frozenset[str]
    scope: frozenset[str]
    eligible_paths: list[Path]
    qualifying_paths: list[Path]
    eligible_flow: Decimal
    suspicious_flow: Decimal
    suspicious_accounts: frozenset[str]
    reachable_pairs: frozenset[tuple[str, str]]
    truncated: bool
    counters: dict[str, int] = field(default_factory=dict)


def enumerate_ring_scope(
    proj: AnalyticProjection, members: Iterable[str], run: ScoringContext, budget: Budget
) -> ScopeResult:
    """Ring scope and its path sets and flows (§3.5) in the analytical context (snapshot, scoring run)."""
    if proj.graph_snapshot_id != run.graph_snapshot_id:
        raise ValueError("projection and scoring run belong to different snapshots (mixing contexts, §3.5)")

    def suspicious(a: str) -> bool:
        return is_suspicious_account(a, run)

    ring = sorted(set(members))
    ring_set = frozenset(ring)

    def qualifying(p: Path) -> bool:
        return suspicious(p[0]) and suspicious(p[-1])

    discovery = _Counter(budget)
    candidates = _enumerate(proj, ring, lambda _a: True, qualifying, discovery)
    scope = frozenset(ring_set.union(*candidates)) if candidates else ring_set

    eligible_counter = _Counter(budget)
    eligible = list(_enumerate(proj, ring, scope.__contains__, lambda _p: True, eligible_counter))
    in_scope_qualifying = [p for p in eligible if qualifying(p)]

    def flow(paths: list[Path], keep: Callable[[str, str], bool]) -> Decimal:
        seen: dict[str, Decimal] = {}
        for p in paths:
            for u, v, t in proj.supporting(p):
                if keep(u, v):
                    seen[t.transaction_id] = t.amount
        return sum(seen.values(), Decimal(0))

    suspicious_accounts = frozenset(a for p in in_scope_qualifying for a in p if suspicious(a))
    return ScopeResult(
        members=ring_set,
        scope=scope,
        eligible_paths=eligible,
        qualifying_paths=in_scope_qualifying,
        eligible_flow=flow(eligible, lambda _u, _v: True),
        suspicious_flow=flow(
            in_scope_qualifying,
            lambda u, v: is_suspicious_transaction(TransactionRef(proj.graph_snapshot_id, u, v), run),
        ),
        suspicious_accounts=suspicious_accounts,
        reachable_pairs=frozenset((p[0], p[-1]) for p in in_scope_qualifying),
        truncated=discovery.truncated or eligible_counter.truncated,
        counters={
            "discovery_paths": discovery.paths,
            "discovery_expansions": discovery.expansions,
            "eligible_paths": eligible_counter.paths,
            "eligible_expansions": eligible_counter.expansions,
        },
    )


def qualifying_paths_from(
    proj: AnalyticProjection, sources: Iterable[str], run: ScoringContext, budget: Budget
) -> tuple[list[Path], bool]:
    """Qualifying paths (§3.5) whose source is one of `sources`, by forward DFS in the §16.2 order."""
    starts = sorted(a for a in set(sources) if is_suspicious_account(a, run))
    counter = _Counter(budget)
    found: dict[Path, None] = {}
    for start in starts:
        stack: list[tuple[str, int]] = [(start, 0)]
        seq = [start]
        on_path = {start}
        while stack:
            node, i = stack[-1]
            nbrs = proj.out.get(node, [])
            if i >= len(nbrs) or len(seq) > budget.max_depth:
                stack.pop()
                on_path.discard(seq.pop())
                continue
            stack[-1] = (node, i + 1)
            nxt = nbrs[i]
            if nxt in on_path:
                continue
            if not counter.expand():
                return list(found), True
            seq.append(nxt)
            on_path.add(nxt)
            stack.append((nxt, 0))
            if is_suspicious_account(nxt, run):
                if not counter.take_path():
                    return list(found), True
                found[tuple(seq)] = None
    return list(found), counter.truncated
