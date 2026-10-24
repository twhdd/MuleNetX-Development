"""The suspicious-flow vocabulary of SRS §3.5: the only definitions of a suspicious account and a suspicious
transaction in the codebase. Ring features, money-flow quantities, interventions and evaluation call these.

Both are evaluated against exactly one analytical context `(graph_snapshot_id, scoring_run_id)`. Their only
inputs are the scoring run's `final_score` values and the versioned threshold; source fraud labels are never an
input (the functions take no label and the loader reads none).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import Engine, text

from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError


@dataclass(frozen=True)
class ScoringContext:
    """One analytical context: a scoring run, its snapshot, its threshold and its accounts' final scores."""

    scoring_run_id: uuid.UUID
    graph_snapshot_id: uuid.UUID
    threshold: Decimal
    final_scores: dict[str, Decimal] = field(repr=False)

    @property
    def suspicious_accounts(self) -> frozenset[str]:
        return frozenset(a for a, s in self.final_scores.items() if s >= self.threshold)


@dataclass(frozen=True)
class TransactionRef:
    """The fields of a transaction the vocabulary may look at."""

    graph_snapshot_id: uuid.UUID
    source_account_id: str
    destination_account_id: str


def is_suspicious_account(account_id: str, run: ScoringContext) -> bool:
    """TRUE iff the account has an assessment in the run with `final_score ≥ suspicious_threshold`."""
    score = run.final_scores.get(account_id)
    return score is not None and score >= run.threshold


def is_suspicious_transaction(t: TransactionRef, run: ScoringContext) -> bool:
    """TRUE iff `t` is in the run's snapshot and its source or destination is a suspicious account."""
    if t.graph_snapshot_id != run.graph_snapshot_id:
        return False
    return is_suspicious_account(t.source_account_id, run) or is_suspicious_account(t.destination_account_id, run)


def load_context(engine: Engine, scoring_run_id: uuid.UUID) -> ScoringContext:
    """Final scores of a SUCCEEDED scoring run and the threshold recorded in its risk logic version."""
    with engine.connect() as conn:
        run = conn.execute(
            text(
                """
                SELECT s.graph_snapshot_id, s.status,
                       r.configuration->>'suspicious_threshold' AS threshold
                FROM scoring_runs s JOIN risk_logic_versions r USING (risk_logic_version)
                WHERE s.scoring_run_id = :r
                """
            ),
            {"r": scoring_run_id},
        ).one_or_none()
        if run is None or run.status != "SUCCEEDED":
            raise AppError(ec.RISK_NOT_AVAILABLE, details={"scoring_run_id": str(scoring_run_id)})
        scores = {
            r.account_id: r.final_score
            for r in conn.execute(
                text("SELECT account_id, final_score FROM risk_assessments WHERE scoring_run_id = :r"),
                {"r": scoring_run_id},
            )
        }
    return ScoringContext(scoring_run_id, run.graph_snapshot_id, Decimal(run.threshold), scores)
