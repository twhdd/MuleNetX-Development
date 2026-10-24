"""AT-DATA-01: a valid fixture is ingested; canonical rows and counts persist; a profile is recorded."""

import pytest
from sqlalchemy import select

from mulenetx.api.deps import get_services
from mulenetx.db.models.canonical import Account, Transaction
from mulenetx.db.models.datasets import DatasetProfile
from tests.apiutil import _Req
from tests.ingestutil import expected, fixture_csv, run_worker, upload

pytestmark = pytest.mark.integration


def test_AT_DATA_01_ingest_valid_fixture(app, client, users) -> None:
    exp = expected("abc_chain")
    admin = users("ADMIN")
    resp = upload(client, admin, fixture_csv("abc_chain"), name="ABC Chain")
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert {"dataset_id", "ingestion_run_id", "pipeline_run_id", "status"} <= set(body)
    key = body["dataset_key"]
    assert key == "abc-chain-vv1"

    run_worker(app)

    ing = client.get(f"/api/v1/ingestion/{body['ingestion_run_id']}", headers=admin.headers).json()
    for field, value in exp["ingestion"].items():
        assert ing[field] == value, field
    assert ing["status"] == "SUCCEEDED" and ing["pipeline_run_id"] == body["pipeline_run_id"]
    pipeline = client.get(f"/api/v1/pipeline-runs/{body['pipeline_run_id']}", headers=admin.headers).json()
    assert pipeline["current_state"] == "READY"
    assert pipeline["metrics"]["records_accepted"] == 2

    rt = get_services(_Req(app)).runtime
    with rt.session_factory() as db:
        accounts = db.execute(select(Account).order_by(Account.account_id)).scalars().all()
        txs = db.execute(select(Transaction).order_by(Transaction.transaction_id)).scalars().all()
        profile = db.get(DatasetProfile, accounts[0].dataset_id)
    assert [a.account_id for a in accounts] == [f"{key}:{r}" for r in exp["accounts"]]
    assert all(a.account_type == "CUSTOMER" for a in accounts)
    assert all(a.risk_tier in ("LOW", "MEDIUM", "HIGH", "CRITICAL") for a in accounts)  # projection set at READY
    for tx, e in zip(txs, exp["transactions"], strict=True):
        assert tx.transaction_id == f"{key}:{e['ref']}"
        assert tx.source_account_id == f"{key}:{e['source']}"
        assert tx.destination_account_id == f"{key}:{e['destination']}"
        assert str(tx.amount) == e["amount"]
        assert tx.timestamp.isoformat().replace("+00:00", "Z") == e["timestamp"]
        assert tx.fraud_label is e["fraud_label"]
    assert profile is not None


def test_AT_DATA_01_list_ingestions(app, client, users) -> None:
    admin = users("ADMIN")
    upload(client, admin, fixture_csv("abc_chain"), name="listing")
    analyst = users("ANALYST")
    listed = client.get("/api/v1/ingestion", headers=analyst.headers).json()
    assert listed["total"] == 1 and listed["items"][0]["status"] in ("CREATED", "RUNNING", "SUCCEEDED")
