"""Community signals and the deterministic candidate score (SRS §9.2, §9.3)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from mulenetx.core.decimal import round7
from mulenetx.flow.analytic_paths import qualifying_paths_from
from mulenetx.flow.vocabulary import TransactionRef, is_suspicious_account, is_suspicious_transaction
from mulenetx.rings.inputs import ContextInputs

WEIGHTS = {
    "H": Decimal("0.35"),
    "D": Decimal("0.25"),
    "C": Decimal("0.15"),
    "community_temporal_density": Decimal("0.15"),
    "M": Decimal("0.10"),
}
SUSPICIOUS_COMMUNITY = "SUSPICIOUS_COMMUNITY"
POTENTIAL_FRAUD_RING_CANDIDATE = "POTENTIAL_FRAUD_RING_CANDIDATE"
MIN_COMMUNITY_SIZE = 3
DENSITY_WINDOW_SECONDS = 3600
DENSITY_MIN_TRANSACTIONS = 3


def ratio(numerator: Decimal, denominator: Decimal) -> tuple[Decimal, bool]:
    """(value, available): a zero denominator gives 0 and unavailable."""
    if denominator == 0:
        return Decimal(0), False
    return round7(numerator / denominator), True


@dataclass(frozen=True)
class CandidateScore:
    score: Decimal
    candidate_class: str
    signals: dict[str, Any]


def classify(score: Decimal) -> str:
    if score >= Decimal("0.70"):
        return POTENTIAL_FRAUD_RING_CANDIDATE
    if score >= Decimal("0.50"):
        return SUSPICIOUS_COMMUNITY
    return "NOT_SUSPICIOUS"


def temporal_density(timestamps: list[float]) -> tuple[Decimal, bool]:
    """Share of internal transactions inside ≥ 1 window [t, t + 3600 s) (t = an internal timestamp) holding ≥ 3."""
    n = len(timestamps)
    if n == 0:
        return Decimal(0), False
    ts = sorted(timestamps)
    covered = [False] * n
    j = 0
    for i in range(n):
        j = max(j, i)
        while j < n and ts[j] < ts[i] + DENSITY_WINDOW_SECONDS:
            j += 1
        if j - i >= DENSITY_MIN_TRANSACTIONS:
            for k in range(i, j):
                covered[k] = True
    return ratio(Decimal(sum(covered)), Decimal(n))


def score_community(ctx: ContextInputs, members_list: list[str]) -> CandidateScore:
    run = ctx.run
    members = set(members_list)
    n = len(members)
    h = round7(Decimal(sum(1 for a in members if is_suspicious_account(a, run))) / Decimal(n))

    internal = ctx.internal(members)
    total = sum((t.amount for _u, _v, t in internal), Decimal(0))
    suspicious = sum(
        (
            t.amount
            for u, v, t in internal
            if is_suspicious_transaction(TransactionRef(ctx.projection.graph_snapshot_id, u, v), run)
        ),
        Decimal(0),
    )
    d, d_ok = ratio(suspicious, total)

    def best(pct: dict[str, float]) -> Decimal:
        return Decimal(repr(max((pct.get(a, 0.0) for a in members), default=0.0)))

    c = round7((best(ctx.pagerank_pct) + best(ctx.betweenness_pct)) / 2)
    density, density_ok = temporal_density([t.timestamp.timestamp() for _u, _v, t in internal])

    paths, truncated = qualifying_paths_from(ctx.projection, members, run, ctx.budget)
    supporting: dict[str, Decimal] = {}
    for p in paths:
        for u, _v, t in ctx.projection.supporting(p):
            if u in members:
                supporting[t.transaction_id] = t.amount
    outgoing = sum((t.amount for (u, _v), txs in ctx.projection.hops.items() if u in members for t in txs), Decimal(0))
    m, m_ok = ratio(sum(supporting.values(), Decimal(0)), outgoing)

    values = {"H": h, "D": d, "C": c, "community_temporal_density": density, "M": m}
    raw = sum((WEIGHTS[k] * v for k, v in values.items()), Decimal(0))
    score = round7(min(Decimal(1), max(Decimal(0), raw)))
    signals: dict[str, Any] = {
        k: {"value": format(v, "f"), "available": ok, "weight": format(WEIGHTS[k], "f")}
        for (k, v), ok in zip(values.items(), (True, d_ok, True, density_ok, m_ok), strict=True)
    }
    signals["member_count"] = n
    signals["M_paths_truncated"] = truncated
    signals["formula"] = "clamp(0.35·H + 0.25·D + 0.15·C + 0.15·community_temporal_density + 0.10·M, 0, 1)"
    return CandidateScore(score, classify(score), signals)


def score_communities(ctx: ContextInputs) -> dict[str, CandidateScore]:
    """Every community of at least MIN_COMMUNITY_SIZE members, in community_id order."""
    return {
        cid: score_community(ctx, members)
        for cid, members in sorted(ctx.communities.items())
        if len(members) >= MIN_COMMUNITY_SIZE
    }
