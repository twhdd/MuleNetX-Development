"""SRS §3.5 vocabulary: suspicion depends only on the scoring run's final scores and threshold."""

import inspect
import uuid

from mulenetx.flow import vocabulary
from mulenetx.flow.vocabulary import TransactionRef, is_suspicious_account, is_suspicious_transaction
from tests.flowutil import SNAPSHOT, context


def test_signatures_take_no_label() -> None:
    for fn in (is_suspicious_account, is_suspicious_transaction):
        params = set(inspect.signature(fn).parameters)
        assert not any("label" in p or "fraud" in p for p in params), params
    loader = inspect.getsource(vocabulary.load_context)
    assert "fraud" not in loader and "label" not in loader  # the context never reads source labels


def test_threshold_is_inclusive_and_unscored_is_not_suspicious() -> None:
    run = context({"A": "0.5000000", "B": "0.4999999", "C": "0.9"})
    assert is_suspicious_account("A", run)
    assert not is_suspicious_account("B", run)
    assert is_suspicious_account("C", run)
    assert not is_suspicious_account("UNSCORED", run)
    assert run.suspicious_accounts == frozenset({"A", "C"})


def test_transaction_rule_and_context_mixing() -> None:
    run = context({"A": "0.8", "B": "0.1", "C": "0.2"})
    assert is_suspicious_transaction(TransactionRef(SNAPSHOT, "A", "B"), run)
    assert is_suspicious_transaction(TransactionRef(SNAPSHOT, "B", "A"), run)
    assert not is_suspicious_transaction(TransactionRef(SNAPSHOT, "B", "C"), run)
    other_snapshot = uuid.UUID("00000000-0000-5000-8000-0000000000cc")
    assert not is_suspicious_transaction(TransactionRef(other_snapshot, "A", "B"), run)


def test_threshold_follows_the_run() -> None:
    run = context({"A": "0.30"}, threshold="0.25")
    assert is_suspicious_account("A", run)
