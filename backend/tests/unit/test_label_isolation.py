"""Source labels stay out of analytics (PLAN §12 item 9, SRS §3.5, §6.8, §11.10).

`fraud_label` may appear only where the SRS needs it: the adapter and ingestion (storage, §7.1), the canonical
model and its read repository and API schema (the recorded FACT, §6.2), profiling (label prevalence, §7.9), the
ML target and its builder and leakage checks (§11), and evaluation (§28.7). No other module may mention it,
and nothing at all may read `isFlaggedFraud` or the balance columns outside the adapter's discard list and
the leakage check."""

import re
from pathlib import Path

PKG = Path(__file__).resolve().parents[2] / "mulenetx"

LABEL_ALLOWED = {
    "ingestion/adapters/paysim_v1.py",
    "ingestion/service.py",
    "ingestion/staging.py",
    "db/models/canonical.py",
    "db/repositories/transactions.py",
    "api/schemas/responses.py",
    "profiling/service.py",
    "ml/target.py",
    "ml/dataset_builder.py",
    "ml/leakage.py",
    "evaluation/service.py",
}
DISCARDED_ALLOWED = {"ingestion/adapters/paysim_v1.py", "ml/leakage.py", "ml/target.py"}
DISCARDED = re.compile(r"isFlaggedFraud|oldbalanceOrg|newbalanceOrig|oldbalanceDest|newbalanceDest")


def sources() -> dict[str, str]:
    return {str(p.relative_to(PKG)): p.read_text() for p in PKG.rglob("*.py")}


def test_fraud_label_only_where_the_srs_needs_it() -> None:
    users = {name for name, text in sources().items() if "fraud_label" in text or "isFraud" in text}
    assert users <= LABEL_ALLOWED, sorted(users - LABEL_ALLOWED)


def test_discarded_columns_are_never_read() -> None:
    users = {name for name, text in sources().items() if DISCARDED.search(text)}
    assert users <= DISCARDED_ALLOWED, sorted(users - DISCARDED_ALLOWED)


def test_graph_writer_has_no_label() -> None:
    graph = "".join(text for name, text in sources().items() if name.startswith("graph/"))
    assert "fraud" not in graph.lower()


def test_copilot_context_has_no_label() -> None:
    assert "fraud_label" not in (PKG / "copilot" / "context.py").read_text()
