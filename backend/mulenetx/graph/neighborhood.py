"""Bounded neighborhood over the TRANSFERRED_TO projection (SRS §19.2, §19.9, §25.2).

Breadth-first by hop; within a hop, accounts are taken by (total_amount descending, account_id); accounts
count toward `max_nodes`, aggregated edges toward `max_edges`. Reaching a limit truncates the response in
that order and sets `truncated = true`. A 5 s budget covers the whole request (`408 QUERY_TIMEOUT`).
"""

from __future__ import annotations

import time
import uuid
from decimal import Decimal
from typing import Any

from neo4j.exceptions import ClientError, TransientError
from sqlalchemy import select
from sqlalchemy.orm import Session

from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.core.lineage import Lineage, lineage_envelope
from mulenetx.core.runtime import Runtime
from mulenetx.core.timeutil import utcnow
from mulenetx.db.models.canonical import Account
from mulenetx.db.models.lineage import GraphSnapshot
from mulenetx.db.repositories.context import active, active_lineage
from mulenetx.graph import cypher
from mulenetx.graph.build import snapshot_key


def _node(account_id: str, hop: int, a: Account | None) -> dict[str, Any]:
    return {
        "account_id": account_id,
        "source_account_ref": None if a is None else a.source_account_ref,
        "account_type": None if a is None else a.account_type,
        "risk_score": None if a is None or a.risk_score is None else float(a.risk_score),
        "risk_tier": None if a is None else a.risk_tier,
        "community_id": None if a is None else a.community_id,
        "hop": hop,
    }


def resolve_snapshot(db: Session, snapshot_id: uuid.UUID | None) -> GraphSnapshot:
    """The requested (or active) snapshot: 404 if unknown or not READY, 410 if RETIRED (§6.8.6)."""
    sid = snapshot_id if snapshot_id is not None else active(db).graph_snapshot_id
    if sid is None:
        raise AppError(ec.NOT_FOUND, "No active graph snapshot.", {"resource": "graph_snapshot"})
    snap = db.get(GraphSnapshot, sid)
    if snap is None:
        raise AppError(ec.NOT_FOUND, details={"resource": "graph_snapshot"})
    if snap.status == "RETIRED":
        raise AppError(ec.SNAPSHOT_RETIRED)
    if snap.status != "READY":
        raise AppError(ec.NOT_FOUND, details={"resource": "graph_snapshot"})
    return snap


class _Deadline:
    def __init__(self, seconds: float) -> None:
        self.end = time.monotonic() + seconds

    def remaining(self) -> float:
        left = self.end - time.monotonic()
        if left <= 0:
            raise AppError(ec.QUERY_TIMEOUT)
        return left


def _run(rt: Runtime, deadline: _Deadline, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        return rt.graph.run(query, params, timeout=deadline.remaining())
    except (ClientError, TransientError) as exc:
        if "Timeout" in (exc.code or "") or "Terminated" in (exc.code or ""):
            raise AppError(ec.QUERY_TIMEOUT) from exc
        raise


def neighborhood(
    rt: Runtime,
    db: Session,
    account_id: str,
    depth: int,
    max_nodes: int,
    max_edges: int,
    snapshot_id: uuid.UUID | None,
) -> dict[str, Any]:
    snap = resolve_snapshot(db, snapshot_id)
    if db.get(Account, account_id) is None:
        raise AppError(ec.NOT_FOUND, details={"resource": "account"})
    deadline = _Deadline(rt.settings.graph_query_timeout_seconds)
    sid = str(snap.graph_snapshot_id)
    if not _run(rt, deadline, cypher.ACCOUNT_IN_SNAPSHOT, {"key": snapshot_key(snap.graph_snapshot_id, account_id)}):
        raise AppError(ec.NOT_FOUND, "The account is not part of this graph snapshot.", {"resource": "account"})

    hops: dict[str, int] = {account_id: 0}
    order: list[str] = [account_id]
    truncated = False
    frontier = [account_id]
    for hop in range(1, depth + 1):
        if not frontier:
            break
        room = max_nodes - len(order)
        if room <= 0:
            truncated = truncated or bool(
                _run(
                    rt,
                    deadline,
                    cypher.NEIGHBOR_CANDIDATES,
                    {"frontier": frontier, "sid": sid, "visited": order, "limit": 1},
                )
            )
            break
        rows = _run(
            rt,
            deadline,
            cypher.NEIGHBOR_CANDIDATES,
            {"frontier": frontier, "sid": sid, "visited": order, "limit": room + 1},
        )
        if len(rows) > room:
            truncated = True
            rows = rows[:room]
        frontier = [r["nb"] for r in rows]
        for nb in frontier:
            hops[nb] = hop
            order.append(nb)

    keys = [snapshot_key(snap.graph_snapshot_id, a) for a in order]
    edges_raw = _run(rt, deadline, cypher.EDGES_AMONG, {"keys": keys, "sid": sid, "ids": order})
    edges_raw.sort(key=lambda e: (max(hops[e["src"]], hops[e["dst"]]), -int(e["micros"]), e["src"], e["dst"]))
    if len(edges_raw) > max_edges:
        truncated = True
        edges_raw = edges_raw[:max_edges]

    accounts = {a.account_id: a for a in db.execute(select(Account).where(Account.account_id.in_(order))).scalars()}
    nodes = [_node(a, hops[a], accounts.get(a)) for a in order]
    edges = [
        {
            "source_account_id": e["src"],
            "destination_account_id": e["dst"],
            "tx_count": int(e["tx_count"]),
            "total_amount": format((Decimal(int(e["micros"])) / Decimal(1_000_000)).quantize(Decimal("0.000001")), "f"),
            "first_ts": e["first_ts"].to_native().isoformat().replace("+00:00", "Z"),
            "last_ts": e["last_ts"].to_native().isoformat().replace("+00:00", "Z"),
        }
        for e in edges_raw
    ]
    lineage = Lineage(graph_snapshot_id=sid)
    return {
        "account_id": account_id,
        "graph_snapshot_id": sid,
        "depth": depth,
        "nodes": nodes,
        "edges": edges,
        "truncated": truncated,
        "applied_limits": {
            "depth": depth,
            "max_nodes": max_nodes,
            "max_edges": max_edges,
            "query_timeout_seconds": rt.settings.graph_query_timeout_seconds,
        },
        **lineage_envelope(lineage, active_lineage(db), utcnow()),
    }
