"""Residual computation by filtering the baseline set (SRS §16A.7). Removing accounts or edges cannot create
paths, so no traversal happens here."""

from __future__ import annotations

from dataclasses import dataclass

from mulenetx.interventions.baseline import Baseline, BaselinePath
from mulenetx.interventions.pool import Spec


@dataclass(frozen=True)
class Residual:
    residual: list[BaselinePath]
    affected: list[BaselinePath]
    alternative: list[BaselinePath]
    affected_accounts: list[str]


def residual(b: Baseline, spec: Spec) -> Residual:
    accounts, edges = spec.accounts, spec.edges
    kept: list[BaselinePath] = []
    hit: list[BaselinePath] = []
    for p in b.paths:
        touched = any(a in accounts for a in p.accounts) or any(e in edges for e in p.edges)
        (hit if touched else kept).append(p)
    hit_pairs = {p.pair for p in hit}
    return Residual(
        residual=kept,
        affected=hit,
        alternative=[p for p in kept if p.pair in hit_pairs],
        affected_accounts=sorted({a for p in hit for a in p.accounts} - accounts),
    )
