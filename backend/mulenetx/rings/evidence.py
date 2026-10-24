"""Ring evidence (SRS §9A.4): everything needed to reconstruct a ring assessment without AI inference."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from mulenetx.core import ids
from mulenetx.flow.vocabulary import TransactionRef, is_suspicious_account, is_suspicious_transaction
from mulenetx.rings.features import RingFeatures
from mulenetx.rings.inputs import ContextInputs
from mulenetx.rings.membership import Membership
from mulenetx.rings.risk import RingRisk

STATEMENT = (
    "A potential fraud ring is a suspicious-network hypothesis built from community membership, transactions, "
    "risk, graph, temporal and money-flow evidence. It is not a confirmed criminal organisation, and membership "
    "alone is not evidence of wrongdoing."
)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def build(ctx: ContextInputs, m: Membership, f: RingFeatures, r: RingRisk, versions: dict[str, Any]) -> dict[str, Any]:
    snap = ctx.projection.graph_snapshot_id
    members = set(m.members)
    relationships: dict[tuple[str, str], list[str]] = {}
    for u, v, t in m.constituent:
        relationships.setdefault((u, v), []).append(t.transaction_id)
    return {
        "statement": STATEMENT,
        "accounts": [
            {
                "account_id": a,
                "final_score": None if a not in ctx.run.final_scores else format(ctx.run.final_scores[a], "f"),
                "suspicious": is_suspicious_account(a, ctx.run),
                "pagerank_percentile": ctx.pagerank_pct.get(a),
                "betweenness_percentile": ctx.betweenness_pct.get(a),
            }
            for a in m.members
        ],
        "transactions": [
            {
                "transaction_id": t.transaction_id,
                "source_account_id": u,
                "destination_account_id": v,
                "timestamp": _iso(t.timestamp),
                "amount": format(t.amount, "f"),
                "suspicious": is_suspicious_transaction(TransactionRef(snap, u, v), ctx.run),
            }
            for u, v, t in m.constituent
        ],
        "relationships": [
            {"source_account_id": u, "destination_account_id": v, "transaction_ids": txs}
            for (u, v), txs in sorted(relationships.items())
        ],
        "motifs": sorted(
            (
                {
                    "motif_type": x.motif_type,
                    "anchor_account_id": x.anchor,
                    "participating_account_ids": sorted(x.accounts),
                    "transaction_ids": sorted(x.transaction_ids),
                    "all_accounts_in_ring": x.accounts <= members,
                }
                for x in ctx.motifs
                if x.accounts & members
            ),
            key=lambda d: (d["motif_type"], d["anchor_account_id"], d["transaction_ids"]),
        ),
        "paths": [
            {
                "path_id": str(ids.path_id(snap, list(p))),
                "accounts": list(p),
                "path_length": len(p) - 1,
                "suspicious_flow": format(f.path_flows.get(p, Decimal(0)), "f"),
            }
            for p in f.scope.qualifying_paths
        ],
        "scope": {
            "accounts": sorted(f.scope.scope),
            "eligible_path_count": len(f.scope.eligible_paths),
            "qualifying_path_count": len(f.scope.qualifying_paths),
            "eligible_flow": format(f.scope.eligible_flow, "f"),
            "suspicious_flow": format(f.scope.suspicious_flow, "f"),
            "truncated": f.scope.truncated,
            "counters": f.scope.counters,
        },
        "features": {k: format(v, "f") for k, v in f.values.items()},
        "feature_availability": f.availability,
        "components": {k: format(v, "f") for k, v in r.components.items()},
        "component_availability": r.availability,
        "temporal_indicators": r.temporal_indicators,
        "ring_risk_score": format(r.score, "f"),
        "risk_tier": r.tier,
        "versions": versions,
    }
