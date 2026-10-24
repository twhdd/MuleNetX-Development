"""ProfilingService (SRS §7.9): the dataset profile recorded before analytics. Informational only."""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy import Engine, text

PROFILE_VERSION = "profile-v1"
QUANTILES = (0.0, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0)  # agent default (OQ-28)
MAX_CHAIN_DEPTH = 10


def _r7(x: float) -> float:
    return round(x, 7)


def quantiles(values: list[int]) -> dict[str, float]:
    """Linear-interpolation quantiles of a sorted copy of `values` (keys p0, p25, ...)."""
    if not values:
        return {f"p{int(q * 100)}": 0.0 for q in QUANTILES}
    v = sorted(values)
    n = len(v)
    out: dict[str, float] = {}
    for q in QUANTILES:
        pos = q * (n - 1)
        lo = int(pos)
        hi = min(lo + 1, n - 1)
        out[f"p{int(q * 100)}"] = _r7(v[lo] + (v[hi] - v[lo]) * (pos - lo))
    return out


def median(values: list[int]) -> float:
    if not values:
        return 0.0
    v = sorted(values)
    n = len(v)
    mid = n // 2
    return float(v[mid]) if n % 2 else (v[mid - 1] + v[mid]) / 2


def bounded_chains(adjacency: dict[str, list[str]], max_depth: int, budget: int) -> tuple[int, int, bool]:
    """(max simple directed path length ≤ max_depth, simple paths with ≥ 2 hops, truncated).

    Deterministic DFS: start nodes and neighbors in account_id order; one expansion = extending a path by
    one edge. Stops when `budget` expansions are used (`truncated`)."""
    longest = 0
    paths_ge2 = 0
    expansions = 0
    for start in sorted(adjacency):
        stack: list[tuple[str, int, frozenset[str], int]] = [(start, 0, frozenset({start}), 0)]
        while stack:
            node, depth, visited, _ = stack.pop()
            if depth >= max_depth:
                continue
            nexts = adjacency.get(node, [])
            for nb in reversed(nexts):  # reversed push → ascending pop order
                if nb in visited:
                    continue
                if expansions >= budget:
                    return longest, paths_ge2, True
                expansions += 1
                d = depth + 1
                longest = max(longest, d)
                if d >= 2:
                    paths_ge2 += 1
                stack.append((nb, d, visited | {nb}, 0))
    return longest, paths_ge2, False


def _components(edges: list[tuple[str, str]]) -> list[int]:
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    sizes: dict[str, int] = defaultdict(int)
    for node in list(parent):
        sizes[find(node)] += 1
    return sorted(sizes.values())


def compute_profile(engine: Engine, dataset_id: uuid.UUID, ingestion: dict[str, Any], budget: int) -> dict[str, Any]:
    p = {"d": dataset_id}
    with engine.connect() as conn:
        by_type = {
            r.account_type: r.n
            for r in conn.execute(
                text(
                    "SELECT account_type, count(*) AS n FROM accounts WHERE dataset_id=:d GROUP BY account_type "
                    "ORDER BY account_type"
                ),
                p,
            )
        }
        per_ts = [
            r.n
            for r in conn.execute(
                text('SELECT count(*) AS n FROM transactions WHERE dataset_id=:d GROUP BY "timestamp"'), p
            )
        ]
        both = conn.execute(
            text(
                "SELECT count(*) FROM (SELECT DISTINCT source_account_id FROM transactions WHERE dataset_id=:d "
                "INTERSECT SELECT DISTINCT destination_account_id FROM transactions WHERE dataset_id=:d) x"
            ),
            p,
        ).scalar_one()
        total_accounts = sum(by_type.values())
        pairs = [
            (r.src, r.dst)
            for r in conn.execute(
                text(
                    "SELECT DISTINCT source_account_id AS src, destination_account_id AS dst FROM transactions "
                    "WHERE dataset_id=:d ORDER BY 1, 2"
                ),
                p,
            )
        ]
        account_ids = [
            r[0]
            for r in conn.execute(text("SELECT account_id FROM accounts WHERE dataset_id=:d ORDER BY account_id"), p)
        ]
        fraud_by_type = {
            r.transaction_type: {"transactions": r.n, "fraud": r.f, "prevalence": _r7(r.f / r.n)}
            for r in conn.execute(
                text(
                    "SELECT transaction_type, count(*) AS n, count(*) FILTER (WHERE fraud_label) AS f "
                    "FROM transactions WHERE dataset_id=:d GROUP BY transaction_type ORDER BY 1"
                ),
                p,
            )
        }
        fraud_edges = [
            (r.src, r.dst)
            for r in conn.execute(
                text(
                    "SELECT DISTINCT source_account_id AS src, destination_account_id AS dst FROM transactions "
                    "WHERE dataset_id=:d AND fraud_label ORDER BY 1, 2"
                ),
                p,
            )
        ]
        active7 = conn.execute(
            text(
                "SELECT count(*) FROM (SELECT account_id FROM ("
                "  SELECT source_account_id AS account_id, date_trunc('day', \"timestamp\" AT TIME ZONE 'UTC') AS day "
                "  FROM transactions WHERE dataset_id=:d "
                "  UNION SELECT destination_account_id, date_trunc('day', \"timestamp\" AT TIME ZONE 'UTC') "
                "  FROM transactions WHERE dataset_id=:d) u GROUP BY account_id HAVING count(DISTINCT day) >= 7) a"
            ),
            p,
        ).scalar_one()

    out_deg: dict[str, int] = dict.fromkeys(account_ids, 0)
    in_deg: dict[str, int] = dict.fromkeys(account_ids, 0)
    adjacency: dict[str, list[str]] = defaultdict(list)
    for s, t in pairs:
        out_deg[s] += 1
        in_deg[t] += 1
        adjacency[s].append(t)
    longest, paths_ge2, truncated = bounded_chains(dict(adjacency), MAX_CHAIN_DEPTH, budget)
    sizes = _components(fraud_edges)
    histogram: dict[str, int] = defaultdict(int)
    for size in sizes:
        histogram[str(size)] += 1

    return {
        "row_counts": {
            "seen": ingestion["records_seen"],
            "accepted": ingestion["records_accepted"],
            "rejected": ingestion["records_rejected"],
            "rejected_by_reason": ingestion["rejection_summary"].get("counts", {}),
            "duplicate": ingestion["records_duplicate"],
        },
        "distinct_accounts_by_type": by_type,
        "distinct_timestamps": len(per_ts),
        "rows_per_timestamp": {"min": min(per_ts, default=0), "median": median(per_ts), "max": max(per_ts, default=0)},
        "fraction_accounts_sender_and_receiver": _r7(both / total_accounts) if total_accounts else 0.0,
        "out_degree_quantiles": quantiles(list(out_deg.values())),
        "in_degree_quantiles": quantiles(list(in_deg.values())),
        "max_directed_chain_length": longest,
        "max_directed_chain_length_bound": MAX_CHAIN_DEPTH,
        "directed_simple_paths_length_ge_2": paths_ge2,
        "path_enumeration": {"max_depth": MAX_CHAIN_DEPTH, "expansion_budget": budget, "truncated": truncated},
        "fraud_label_prevalence_by_type": fraud_by_type,
        "fraud_component_size_histogram": dict(sorted(histogram.items(), key=lambda kv: int(kv[0]))),
        "accounts_with_7_active_days": active7,
    }
