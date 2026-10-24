"""AT-FEAT-02: a transaction and a graph edge after T change nothing in F01–F42 at T."""

import hashlib
import math
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from mulenetx.analytics.service import AnalyticsService
from mulenetx.api.deps import get_services
from mulenetx.db.models.canonical import Account, Transaction
from mulenetx.db.models.lineage import AnalyticsRun, GraphSnapshot
from mulenetx.features.service import FeatureService, GraphContext
from mulenetx.graph.service import GraphService, snapshot_id_for
from tests.apiutil import _Req
from tests.seed import ANCHOR, seed_dataset

pytestmark = pytest.mark.integration


def _same(a: list[float], b: list[float]) -> bool:
    return all((math.isnan(x) and math.isnan(y)) or x == y for x, y in zip(a, b, strict=True))


def test_AT_FEAT_02_future_transactions_and_edges_excluded(app) -> None:
    rt = get_services(_Req(app)).runtime
    edges = [("CA", "CB", 100.0, 1), ("CB", "CC", 50.0, 2), ("CC", "CA", 20.0, 3), ("CA", "CD", 5.0, 10)]
    ds = seed_dataset(rt, edges, key="fut")
    T = ANCHOR + timedelta(hours=5)
    # a TRAINING_SPLIT-style snapshot at T and its analytics run
    graph = GraphService(rt)
    prepared = graph.prepare_snapshot(ds.dataset_id, ds.ingestion_run_id, "TRAINING_SPLIT", T)
    assert prepared is not None
    sid = prepared.graph_snapshot_id
    assert sid == snapshot_id_for(ds.dataset_id, "TRAINING_SPLIT", ANCHOR + timedelta(hours=3))
    graph.build_and_validate(sid)
    with rt.session_factory() as db:
        snap = db.get(GraphSnapshot, sid)
        assert snap is not None and snap.data_cutoff == ANCHOR + timedelta(hours=3)  # max included timestamp ≤ T
    run = AnalyticsService(rt).run(sid, ds.dataset_id, snap.data_cutoff)
    with rt.session_factory() as db:
        ctx = GraphContext(db.get(GraphSnapshot, sid), db.get(AnalyticsRun, run.analytics_run_id))
    service = FeatureService(rt)
    accounts = ["fut:CA", "fut:CB", "fut:CC"]
    before = {v.account_id: v for v in service.vectors(ds.dataset_id, T, accounts, ctx)}

    # add a transaction and a brand-new edge after T
    with rt.session_factory() as db:
        db.add(Account(account_id="fut:CZ", dataset_id=ds.dataset_id, source_account_ref="CZ", account_type="CUSTOMER"))
        db.flush()
        db.add(
            Transaction(
                transaction_id="fut:0000000099",
                dataset_id=ds.dataset_id,
                ingestion_run_id=ds.ingestion_run_id,
                source_transaction_ref="0000000099",
                source_account_id="fut:CB",
                destination_account_id="fut:CZ",
                amount=Decimal("999"),
                timestamp=ANCHOR + timedelta(hours=6),
                transaction_type="TRANSFER",
                fraud_label=False,
                source_record_hash=hashlib.sha256(b"99").hexdigest(),
            )
        )
        db.commit()
    after = {v.account_id: v for v in service.vectors(ds.dataset_id, T, accounts, ctx)}
    for acc in accounts:
        assert _same(before[acc].values, after[acc].values), acc
        assert before[acc].states == after[acc].states, acc
    # the graph features (F11–F18) come from the snapshot at T, not from later edges
    assert after["fut:CB"].values[10] == 2  # degree of CB at T: CA and CC only
    assert uuid.UUID(str(sid))
    assert datetime(2020, 1, 1, 5, tzinfo=UTC) == T
