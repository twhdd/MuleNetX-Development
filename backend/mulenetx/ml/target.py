"""Account-level target: retrospective detection (SRS §11.2, DEC-05).

This module and `mulenetx.evaluation` are the only readers of source fraud labels (PLAN §12 item 9).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Final

TARGET_DEFINITION_ID: Final[str] = "retrospective-detection-v1"
POSITIVE: Final[int] = 1
NEGATIVE: Final[int] = 0
EXCLUDED_ACCOUNT_TYPES: Final[frozenset[str]] = frozenset({"MERCHANT"})


def label(window_labels: Iterable[bool | None]) -> int | None:
    """Y(a, W) from the fraud labels of tx(a, W): 1 if any is TRUE; 0 if ≥ 1 transaction, none TRUE and all
    labelled; None (UNLABELLED) otherwise — never converted to 0."""
    labels = list(window_labels)
    if any(x is True for x in labels):
        return POSITIVE
    if labels and all(x is not None for x in labels):
        return NEGATIVE
    return None


def label_from_counts(tx_count: int, fraud_count: int, labelled_count: int) -> int | None:
    if fraud_count >= 1:
        return POSITIVE
    if tx_count >= 1 and labelled_count == tx_count:
        return NEGATIVE
    return None


def target_definition(window_table: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_definition_id": TARGET_DEFINITION_ID,
        "target_semantics": "RETROSPECTIVE_DETECTION",
        "window_table": window_table,
        "positive_rule": "at least one transaction of the account in W carries fraud_label = TRUE",
        "negative_rule": "at least one transaction in W, none labelled fraud, and every one carries a label",
        "unlabelled_rule": "no transaction in W, or some transaction in W lacks a label; dropped, never negative",
        "exclusion_rules": [
            "account_type MERCHANT",
            "invalid data quality",
            "account assigned to an earlier split (§11.5)",
            "synthetic-injection dataset (§7.10)",
        ],
        "label_source": "transactions.fraud_label (PaySim isFraud); isFlaggedFraud is never stored",
        "forward_horizon": None,
    }
