"""Ring features (SRS §9A.2). Every value is in [0, 1], rounded half-even to 7 dp, with availability."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from mulenetx.core.decimal import round7
from mulenetx.flow.analytic_paths import Path, ScopeResult, enumerate_ring_scope
from mulenetx.flow.vocabulary import TransactionRef, is_suspicious_transaction
from mulenetx.rings.candidates import ratio
from mulenetx.rings.inputs import ContextInputs
from mulenetx.rings.membership import Membership

RING_FEATURE_VERSION = "ring-features-v1"
MFC_TOP_K = 3
NAMES = ("RSD", "RC", "TC", "MFC", "CS", "FI", "FO", "CP", "SPD")


@dataclass
class RingFeatures:
    values: dict[str, Decimal]
    availability: dict[str, str]
    scope: ScopeResult
    path_flows: dict[Path, Decimal] = field(default_factory=dict)

    @property
    def paths_truncated(self) -> bool:
        return self.scope.truncated


def _path_flow(ctx: ContextInputs, path: Path) -> tuple[Decimal, dict[str, Decimal]]:
    """Sum of the unique suspicious supporting transactions of one path, and those transactions."""
    txs: dict[str, Decimal] = {}
    for u, v, t in ctx.projection.supporting(path):
        if is_suspicious_transaction(TransactionRef(ctx.projection.graph_snapshot_id, u, v), ctx.run):
            txs[t.transaction_id] = t.amount
    return sum(txs.values(), Decimal(0)), txs


def _path_order(ctx: ContextInputs, path: Path) -> tuple[int, Decimal, tuple[str, ...], tuple[str, ...]]:
    """§16.5: length, total supporting amount (desc), account sequence, first supporting transaction per hop."""
    hops = list(zip(path, path[1:], strict=False))
    total = sum((t.amount for h in hops for t in ctx.projection.hops[h]), Decimal(0))
    return (len(hops), -total, path, tuple(ctx.projection.hops[h][0].transaction_id for h in hops))


def compute(ctx: ContextInputs, m: Membership) -> RingFeatures:
    members = set(m.members)
    snapshot = ctx.projection.graph_snapshot_id
    values: dict[str, Decimal] = {}
    avail: dict[str, str] = {}

    def put(name: str, value: Decimal, available: bool = True) -> None:
        values[name] = value
        avail[name] = "AVAILABLE" if available else "UNAVAILABLE"

    n_tx = Decimal(len(m.constituent))
    suspicious_tx = sum(
        1 for u, v, _t in m.constituent if is_suspicious_transaction(TransactionRef(snapshot, u, v), ctx.run)
    )
    put("RSD", *ratio(Decimal(suspicious_tx), n_tx))

    ranked = sorted(m.members, key=lambda a: (-ctx.run.final_scores.get(a, Decimal(0)), a))
    k = min(3, len(ranked))
    top = sum((ctx.run.final_scores.get(a, Decimal(0)) for a in ranked[:k]), Decimal(0))
    put("RC", *ratio(top, sum((ctx.run.final_scores.get(a, Decimal(0)) for a in ranked), Decimal(0))))

    constituent_ids = {t.transaction_id for _u, _v, t in m.constituent}
    coordinated: set[str] = set()
    for motif in ctx.motifs:
        if motif.transaction_ids and motif.transaction_ids <= constituent_ids:
            coordinated |= motif.transaction_ids
    put("TC", *ratio(Decimal(len(coordinated)), n_tx))

    scope = enumerate_ring_scope(ctx.projection, m.members, ctx.run, ctx.budget)
    flows = {p: _path_flow(ctx, p) for p in scope.qualifying_paths}
    ranked_paths = sorted(scope.qualifying_paths, key=lambda p: (-flows[p][0], _path_order(ctx, p)))
    top_txs: dict[str, Decimal] = {}
    for p in ranked_paths[:MFC_TOP_K]:
        top_txs.update(flows[p][1])
    put("MFC", *ratio(sum(top_txs.values(), Decimal(0)), scope.suspicious_flow))

    def mean_pct(pct: dict[str, float]) -> Decimal:
        return sum((Decimal(repr(pct.get(a, 0.0))) for a in m.members), Decimal(0)) / len(m.members)

    put("CS", round7((mean_pct(ctx.pagerank_pct) + mean_pct(ctx.betweenness_pct)) / 2))
    fan_in = {x.anchor for x in ctx.motifs if x.motif_type == "FAN_IN" and x.anchor in members}
    fan_out = {x.anchor for x in ctx.motifs if x.motif_type == "FAN_OUT" and x.anchor in members}
    put("FI", round7(Decimal(len(fan_in)) / len(m.members)))
    put("FO", round7(Decimal(len(fan_out)) / len(m.members)))
    cycle = any(x.motif_type == "CIRCULAR_FLOW" and x.accounts <= members for x in ctx.motifs)
    put("CP", Decimal(1 if cycle else 0))
    put("SPD", *ratio(Decimal(len(scope.qualifying_paths)), Decimal(len(scope.eligible_paths))))

    if scope.truncated:  # §9A.2: computed on the enumerated set, lower confidence
        for name in ("MFC", "SPD"):
            if avail[name] == "AVAILABLE":
                avail[name] = "LOWER_BOUND_TRUNCATED"
    return RingFeatures(values, avail, scope, {p: f for p, (f, _t) in flows.items()})


def as_columns(f: RingFeatures) -> dict[str, Any]:
    return {
        "suspicious_transaction_density": f.values["RSD"],
        "risk_concentration": f.values["RC"],
        "temporal_coordination": f.values["TC"],
        "money_flow_concentration": f.values["MFC"],
        "centrality_signal": f.values["CS"],
        "fan_in_signal": f.values["FI"],
        "fan_out_signal": f.values["FO"],
        "cycle_presence": f.values["CP"],
        "suspicious_path_density": f.values["SPD"],
        "eligible_path_count": len(f.scope.eligible_paths),
        "qualifying_path_count": len(f.scope.qualifying_paths),
        "paths_truncated": f.scope.truncated,
    }
