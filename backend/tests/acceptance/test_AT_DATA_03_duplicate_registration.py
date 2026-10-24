"""AT-DATA-03: the same checksum and dataset version twice → 409 DATASET_ALREADY_REGISTERED; no duplicates."""

import pytest
from sqlalchemy import func, select

from mulenetx.api.deps import get_services
from mulenetx.db.models.canonical import Transaction
from mulenetx.db.models.datasets import Dataset
from tests.apiutil import _Req
from tests.ingestutil import fixture_csv, run_worker, upload

pytestmark = pytest.mark.integration


def test_AT_DATA_03_duplicate_registration(app, client, users) -> None:
    admin = users("ADMIN")
    first = upload(client, admin, fixture_csv("abc_chain"), name="dup", version="v1")
    assert first.status_code == 202
    run_worker(app)
    second = upload(client, admin, fixture_csv("abc_chain"), name="dup", version="v1")
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "DATASET_ALREADY_REGISTERED"
    third = upload(client, admin, fixture_csv("abc_chain"), name="another name", version="v1")
    assert third.status_code == 409 and third.json()["error"]["code"] == "DATASET_ALREADY_REGISTERED"
    rt = get_services(_Req(app)).runtime
    with rt.session_factory() as db:
        assert db.execute(select(func.count()).select_from(Dataset)).scalar_one() == 1
        assert db.execute(select(func.count()).select_from(Transaction)).scalar_one() == 2
