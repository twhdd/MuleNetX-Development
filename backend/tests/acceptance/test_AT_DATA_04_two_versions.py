"""AT-DATA-04: the same PaySim file as v1 and v2 (overlapping source IDs) → both succeed, disjoint IDs."""

import pytest
from sqlalchemy import select

from mulenetx.api.deps import get_services
from mulenetx.db.models.canonical import Account, Transaction
from tests.apiutil import _Req
from tests.ingestutil import fixture_csv, run_worker, upload

pytestmark = pytest.mark.integration


def test_AT_DATA_04_two_versions_disjoint_ids(app, client, users) -> None:
    admin = users("ADMIN")
    v1 = upload(client, admin, fixture_csv("abc_chain"), name="paysim", version="v1").json()
    run_worker(app)
    v2 = upload(client, admin, fixture_csv("abc_chain"), name="paysim", version="v2").json()
    run_worker(app)
    assert v1["dataset_key"] != v2["dataset_key"]
    rt = get_services(_Req(app)).runtime
    with rt.session_factory() as db:
        accounts = db.execute(select(Account)).scalars().all()
        txs = db.execute(select(Transaction)).scalars().all()
    by_ds = {v1["dataset_id"]: set(), v2["dataset_id"]: set()}
    for a in accounts:
        by_ds[str(a.dataset_id)].add(a.account_id)
    assert len(by_ds[v1["dataset_id"]]) == len(by_ds[v2["dataset_id"]]) == 3
    assert not (by_ds[v1["dataset_id"]] & by_ds[v2["dataset_id"]])
    assert len({t.transaction_id for t in txs}) == 4
    refs = {(str(t.dataset_id), t.source_transaction_ref) for t in txs}
    assert len(refs) == 4
    for t in txs:
        assert str(t.dataset_id) in (v1["dataset_id"], v2["dataset_id"])
        prefix = v1["dataset_key"] if str(t.dataset_id) == v1["dataset_id"] else v2["dataset_key"]
        assert t.transaction_id.startswith(prefix + ":")
        assert t.source_account_id.startswith(prefix + ":")
