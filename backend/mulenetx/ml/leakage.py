"""The seven leakage checks of SRS §11.6. Any failure blocks model registration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from mulenetx.features.encoding import State
from mulenetx.features.registry import RISK_DERIVED, Registry
from mulenetx.ml.dataset_builder import TrainingData

FORBIDDEN_FEATURE_INPUTS = (
    "fraud_label",
    "isFraud",
    "isFlaggedFraud",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
)
FEATURE_SOURCE_DIR = Path(__file__).resolve().parents[1] / "features"


@dataclass(frozen=True)
class CheckResult:
    check: str
    passed: bool
    detail: str


def check_1_feature_event_time(data: TrainingData) -> CheckResult:
    bad = [
        (s.split, a)
        for s in data.splits.values()
        for a, as_of in zip(s.accounts, s.feature_as_of, strict=True)
        if as_of != s.cutoff
    ]
    return CheckResult(
        "1_feature_event_time",
        not bad,
        "every feature vector is computed at its observation's T_end" if not bad else f"{bad[:5]}",
    )


def check_2_graph_snapshot_cutoff(data: TrainingData) -> CheckResult:
    bad = [s.split for s in data.splits.values() if s.snapshot_cutoff > s.cutoff]
    return CheckResult(
        "2_graph_snapshot_cutoff",
        not bad,
        "all graph features from snapshots with data_cutoff <= T" if not bad else f"splits {bad}",
    )


def check_3_entity_separation(data: TrainingData) -> CheckResult:
    seen: dict[str, str] = {}
    dup = []
    for s in data.splits.values():
        for a in s.accounts:
            if a in seen:
                dup.append((a, seen[a], s.split))
            seen[a] = s.split
    return CheckResult("3_entity_separation", not dup, "no account in more than one split" if not dup else f"{dup[:5]}")


def check_4_no_label_columns(reg: Registry, source_dir: Path = FEATURE_SOURCE_DIR) -> CheckResult:
    pattern = re.compile("|".join(FORBIDDEN_FEATURE_INPUTS))
    hits = [f.id for f in reg.features if pattern.search(f.definition) or pattern.search(f.name)]
    for path in sorted(source_dir.glob("*.py")):
        for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if pattern.search(line) and "FORBIDDEN" not in line:
                hits.append(f"{path.name}:{no}")
    return CheckResult(
        "4_no_label_or_balance_columns",
        not hits,
        "fraud_label, isFlaggedFraud and balance columns absent" if not hits else f"{hits[:5]}",
    )


def check_5_regime(data: TrainingData, reg: Registry) -> CheckResult:
    idx = [reg.index(fid) for fid in RISK_DERIVED]
    bad = [
        (s.split, fid)
        for s in data.splits.values()
        for col, fid in zip(idx, RISK_DERIVED, strict=True)
        if len(s.states) and not (s.states[:, col] == State.UNAVAILABLE).all()
    ]
    return CheckResult(
        "5_regime_risk_features_unavailable",
        not bad,
        "F19, F31, F33, F36, F37 UNAVAILABLE everywhere" if not bad else f"{bad}",
    )


def check_6_test_not_used(train_rows: set[str], early_stopping_rows: set[str], data: TrainingData) -> CheckResult:
    test = set(data.splits["test"].accounts)
    leaked = (train_rows | early_stopping_rows) & test
    return CheckResult(
        "6_test_split_unused",
        not leaked,
        "test rows used for neither fitting nor early stopping" if not leaked else f"{sorted(leaked)[:5]}",
    )


def check_7_label_window(data: TrainingData, label_tx_outside: dict[str, int]) -> CheckResult:
    bad = {k: v for k, v in label_tx_outside.items() if v}
    return CheckResult(
        "7_label_window_containment", not bad, "every label uses only transactions in its W_k" if not bad else f"{bad}"
    )


def all_checks(
    data: TrainingData,
    reg: Registry,
    train_rows: set[str],
    early_stopping_rows: set[str],
    label_tx_outside: dict[str, int],
) -> list[CheckResult]:
    return [
        check_1_feature_event_time(data),
        check_2_graph_snapshot_cutoff(data),
        check_3_entity_separation(data),
        check_4_no_label_columns(reg),
        check_5_regime(data, reg),
        check_6_test_not_used(train_rows, early_stopping_rows, data),
        check_7_label_window(data, label_tx_outside),
    ]
