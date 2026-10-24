"""Baseline of a scenario (SRS §16A.5): the in-scope qualifying path set P of the target ring and its metrics."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from mulenetx.core import ids
from mulenetx.flow.analytic_paths import AnalyticProjection, Path, ScopeResult
from mulenetx.flow.vocabulary import ScoringContext, TransactionRef, is_suspicious_account, is_suspicious_transaction

Edge = tuple[str, str]


def edge_id(edge: Edge) -> str:
    return f"{edge[0]}>{edge[1]}"


@dataclass(frozen=True)
class BaselinePath:
    accounts: Path
    path_id: str
    suspicious_txs: dict[str, Decimal]  # unique suspicious supporting transactions → amount

    @property
    def edges(self) -> list[Edge]:
        return list(zip(self.accounts, self.accounts[1:], strict=False))

    @property
    def pair(self) -> tuple[str, str]:
        return self.accounts[0], self.accounts[-1]


@dataclass
class Baseline:
    snapshot_id: uuid.UUID
    run: ScoringContext
    paths: list[BaselinePath]
    truncated: bool
    suspicious_flow: Decimal = field(init=False)
    risk_mass: Decimal = field(init=False)
    pairs: set[tuple[str, str]] = field(init=False)

    def __post_init__(self) -> None:
        self.suspicious_flow = flow(self.paths)
        self.pairs = {p.pair for p in self.paths}
        self.risk_mass = risk_mass(self.paths, self.run, frozenset())

    def score(self, account: str) -> Decimal:
        """`final_score` in the run, unavailable as 0 (§16A.4.3)."""
        return self.run.final_scores.get(account, Decimal(0))


def flow(paths: list[BaselinePath]) -> Decimal:
    seen: dict[str, Decimal] = {}
    for p in paths:
        seen.update(p.suspicious_txs)
    return sum(seen.values(), Decimal(0))


def risk_mass(paths: list[BaselinePath], run: ScoringContext, removed: frozenset[str]) -> Decimal:
    """Σ final_score over suspicious accounts not removed that lie on ≥ 1 of `paths` (§16A.5, §16A.12)."""
    accounts = {a for p in paths for a in p.accounts if a not in removed and is_suspicious_account(a, run)}
    return sum((run.final_scores[a] for a in accounts), Decimal(0))


def build(proj: AnalyticProjection, run: ScoringContext, scope: ScopeResult) -> Baseline:
    paths = []
    for accounts in scope.qualifying_paths:
        txs: dict[str, Decimal] = {}
        for u, v, t in proj.supporting(accounts):
            if is_suspicious_transaction(TransactionRef(proj.graph_snapshot_id, u, v), run):
                txs[t.transaction_id] = t.amount
        paths.append(BaselinePath(accounts, str(ids.path_id(proj.graph_snapshot_id, list(accounts))), txs))
    return Baseline(proj.graph_snapshot_id, run, paths, scope.truncated)
