"""MoneyFlowService (SRS §16): interactive path queries and path evidence."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from mulenetx.core import error_codes as ec
from mulenetx.core import ids
from mulenetx.core.errors import AppError
from mulenetx.core.lineage import Lineage, lineage_envelope
from mulenetx.core.runtime import Runtime
from mulenetx.core.timeutil import isoformat_utc, utcnow
from mulenetx.db.models.canonical import Account
from mulenetx.db.models.lineage import GraphSnapshot
from mulenetx.db.repositories.context import active_lineage
from mulenetx.flow.interactive_paths import Budget, all_paths, pruned_subgraph, shortest_paths
from mulenetx.flow.ordering import Edge, path_sort_key
from mulenetx.graph import cypher
from mulenetx.graph.build import snapshot_key
from mulenetx.graph.neighborhood import _Deadline, _run, resolve_snapshot

ALGORITHM_VERSION = "paths-v1"
SEMANTICS = (
    "A path establishes topological connectivity only. Hops are not required to be time-ordered, so a "
    "path does not by itself establish that funds moved along it, nor criminal intent, fraud, mule status "
    "or collusion."
)
MICROS = Decimal(1_000_000)


def hop_evidence(
    db: Session, snapshot: GraphSnapshot, edges: list[Edge], limit: int, offset: int = 0
) -> dict[Edge, dict[str, Any]]:
    """Supporting transactions per hop in (timestamp, transaction_id) order, `limit` per hop, with totals."""
    if not edges:
        return {}
    rows = db.execute(
        text(
            """
            SELECT * FROM (
                SELECT t.source_account_id AS src, t.destination_account_id AS dst, t.transaction_id,
                       t."timestamp" AS ts,
                       t.amount, t.transaction_type,
                       row_number() OVER (PARTITION BY t.source_account_id, t.destination_account_id
                                          ORDER BY t."timestamp", t.transaction_id) AS rn,
                       count(*) OVER (PARTITION BY t.source_account_id, t.destination_account_id) AS total
                FROM transactions t
                JOIN unnest(CAST(:srcs AS varchar[]), CAST(:dsts AS varchar[])) AS e(s, d)
                  ON t.source_account_id = e.s AND t.destination_account_id = e.d
                WHERE t.dataset_id = :ds AND t."timestamp" <= :cutoff
            ) x WHERE rn > :off AND rn <= :off + :lim ORDER BY src, dst, rn
            """
        ),
        {
            "srcs": [e[0] for e in edges],
            "dsts": [e[1] for e in edges],
            "ds": snapshot.dataset_id,
            "cutoff": snapshot.data_cutoff,
            "off": offset,
            "lim": limit,
        },
    ).all()
    out: dict[Edge, dict[str, Any]] = {
        e: {"transactions": [], "timestamps": [], "amounts": [], "transaction_types": [], "total": 0} for e in edges
    }
    for r in rows:
        hop = out[(r.src, r.dst)]
        hop["transactions"].append(r.transaction_id)
        hop["timestamps"].append(isoformat_utc(r.ts))
        hop["amounts"].append(format(r.amount, "f"))
        hop["transaction_types"].append(r.transaction_type)
        hop["total"] = int(r.total)
    return out


def _path_view(
    sid: str,
    accounts: list[str],
    micros: dict[Edge, int],
    counts: dict[Edge, int],
    evidence: dict[Edge, dict[str, Any]],
    max_hop_evidence: int,
) -> dict[str, Any]:
    hops = list(zip(accounts, accounts[1:], strict=False))
    hop_views = []
    for h in hops:
        ev = evidence.get(h, {"transactions": [], "timestamps": [], "amounts": [], "transaction_types": [], "total": 0})
        hop_views.append(
            {
                "source_account_id": h[0],
                "destination_account_id": h[1],
                "tx_count": counts.get(h, ev["total"]),
                "total_amount": format((Decimal(micros[h]) / MICROS).quantize(Decimal("0.000001")), "f"),
                "transactions": ev["transactions"][:max_hop_evidence],
                "timestamps": ev["timestamps"][:max_hop_evidence],
                "amounts": ev["amounts"][:max_hop_evidence],
                "transaction_types": ev["transaction_types"][:max_hop_evidence],
                "transactions_total": ev["total"],
                "evidence_truncated": ev["total"] > max_hop_evidence,
            }
        )
    total = sum(micros[h] for h in hops)
    return {
        "path_id": str(ids.path_id(sid, accounts)),
        "source_account_id": accounts[0],
        "destination_account_id": accounts[-1],
        "path_length": len(hops),
        "accounts": accounts,
        "total_amount": format((Decimal(total) / MICROS).quantize(Decimal("0.000001")), "f"),
        "hops": hop_views,
    }


class MoneyFlowService:
    def __init__(self, runtime: Runtime) -> None:
        self.rt = runtime

    def paths(
        self,
        db: Session,
        source: str,
        destination: str,
        mode: str,
        max_depth: int,
        max_results: int,
        snapshot_id: uuid.UUID | None,
    ) -> dict[str, Any]:
        if source == destination:
            raise AppError(ec.INVALID_PATH_REQUEST)
        s = self.rt.settings
        snapshot = resolve_snapshot(db, snapshot_id)
        for acc in (source, destination):
            if db.get(Account, acc) is None:
                raise AppError(ec.NOT_FOUND, details={"resource": "account"})
        sid = str(snapshot.graph_snapshot_id)
        deadline = _Deadline(s.path_query_timeout_seconds)
        for acc in (source, destination):
            if not _run(
                self.rt, deadline, cypher.ACCOUNT_IN_SNAPSHOT, {"key": snapshot_key(snapshot.graph_snapshot_id, acc)}
            ):
                raise AppError(ec.NOT_FOUND, "The account is not part of this graph snapshot.", {"resource": "account"})
        g = pruned_subgraph(self.rt, deadline, sid, source, destination, max_depth)
        budget = Budget(deadline.remaining())
        found = (
            shortest_paths(g, source, destination, budget)
            if mode == "SHORTEST"
            else all_paths(g, source, destination, max_depth, budget)
        )
        edges = sorted({h for p in found for h in zip(p, p[1:], strict=False)})
        deadline.remaining()
        first = hop_evidence(db, snapshot, edges, 1)
        first_tx = {e: (v["transactions"][0] if v["transactions"] else "") for e, v in first.items()}
        found.sort(key=lambda p: path_sort_key(p, g.micros, first_tx))
        total_found = len(found)
        selected = found[:max_results]
        used = sorted({h for p in selected for h in zip(p, p[1:], strict=False)})
        evidence = hop_evidence(db, snapshot, used, s.max_hop_evidence)
        deadline.remaining()
        lineage = Lineage(graph_snapshot_id=sid)
        return {
            "source_account_id": source,
            "destination_account_id": destination,
            "mode": mode,
            "graph_snapshot_id": sid,
            "algorithm_version": ALGORITHM_VERSION,
            "paths": [_path_view(sid, p, g.micros, g.tx_count, evidence, s.max_hop_evidence) for p in selected],
            "paths_found": total_found,
            "truncated": total_found > max_results,
            "applied_limits": {
                "max_depth": max_depth,
                "max_results": max_results,
                "query_timeout_seconds": s.path_query_timeout_seconds,
                "max_hop_evidence": s.max_hop_evidence,
            },
            "statement": SEMANTICS,
            **lineage_envelope(lineage, active_lineage(db), utcnow()),
        }

    def path_detail(
        self, db: Session, path_id: uuid.UUID, snapshot_id: uuid.UUID, accounts: list[str], page: int, page_size: int
    ) -> dict[str, Any]:
        """Recompute a path's evidence from its account sequence in the given snapshot (OQ-60)."""
        snapshot = resolve_snapshot(db, snapshot_id)
        sid = str(snapshot.graph_snapshot_id)
        if len(accounts) < 2 or len(set(accounts)) != len(accounts) or ids.path_id(sid, accounts) != path_id:
            raise AppError(ec.NOT_FOUND, details={"resource": "path"})
        hops = list(zip(accounts, accounts[1:], strict=False))
        deadline = _Deadline(self.rt.settings.path_query_timeout_seconds)
        rows = _run(self.rt, deadline, cypher.OUT_NEIGHBORS, {"ids": sorted(set(accounts[:-1])), "sid": sid})
        present = {(r["src"], r["dst"]): (int(r["micros"]), int(r["tx_count"])) for r in rows}
        if any(h not in present for h in hops):
            raise AppError(ec.NOT_FOUND, details={"resource": "path"})
        micros = {h: present[h][0] for h in hops}
        counts = {h: present[h][1] for h in hops}
        evidence = hop_evidence(db, snapshot, hops, page_size, (page - 1) * page_size)
        view = _path_view(sid, accounts, micros, counts, evidence, page_size)
        return {
            **view,
            "graph_snapshot_id": sid,
            "algorithm_version": ALGORITHM_VERSION,
            "evidence_page": {"page": page, "page_size": page_size},
            "statement": SEMANTICS,
            **lineage_envelope(Lineage(graph_snapshot_id=sid), active_lineage(db), utcnow()),
        }
