"""AT-DATA-02: malformed rows are rejected with reason codes; valid rows continue."""

import pytest
from sqlalchemy import select

from mulenetx.api.deps import get_services
from mulenetx.db.models.canonical import Account, Transaction
from tests.apiutil import _Req
from tests.ingestutil import expected, fixture_csv, run_worker, upload

pytestmark = pytest.mark.integration


def test_AT_DATA_02_rejections_with_reason_codes(app, client, users) -> None:
    exp = expected("rejections")
    admin = users("ADMIN")
    body = upload(client, admin, fixture_csv("rejections"), name="rejections").json()
    run_worker(app)
    ing = client.get(f"/api/v1/ingestion/{body['ingestion_run_id']}", headers=admin.headers).json()
    assert ing["status"] == "SUCCEEDED"
    assert ing["records_seen"] == exp["records_seen"]
    assert ing["records_accepted"] == exp["records_accepted"]
    assert ing["records_rejected"] == exp["records_rejected"]
    assert ing["rejection_summary"]["counts"] == exp["counts"]
    assert ing["rejection_summary"]["samples"] == exp["samples"]
    assert "C1" not in str(ing["rejection_summary"])  # no row content copied into metadata

    key = body["dataset_key"]
    rt = get_services(_Req(app)).runtime
    with rt.session_factory() as db:
        txs = {t.source_transaction_ref: t for t in db.execute(select(Transaction)).scalars()}
        accounts = {a.source_account_ref: a.account_type for a in db.execute(select(Account)).scalars()}
    assert sorted(txs) == exp["accepted_refs"]
    assert accounts == exp["accounts"]
    for ref, amount in exp["amounts"].items():
        assert str(txs[ref].amount) == amount
        assert txs[ref].fraud_label is exp["fraud"][ref]
        assert txs[ref].transaction_id == f"{key}:{ref}"
