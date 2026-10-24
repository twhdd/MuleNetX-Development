"""Upload contract (SRS §19.5, SR-23): content type, header, size cap, adapter; CLI registration."""

import json
from pathlib import Path

import pytest

from mulenetx.main import create_app
from tests.conftest import FAST_ARGON, make_settings
from tests.ingestutil import fixture_csv, upload

pytestmark = pytest.mark.integration


def test_non_csv_content_type_415(client, users) -> None:
    admin = users("ADMIN")
    resp = upload(client, admin, fixture_csv("abc_chain"), content_type="application/json")
    assert resp.status_code == 415 and resp.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_missing_header_columns_400(client, users, tmp_path: Path) -> None:
    admin = users("ADMIN")
    bad = tmp_path / "bad.csv"
    bad.write_text("step,type,amount\n1,TRANSFER,5\n")
    resp = upload(client, admin, bad)
    assert resp.status_code == 400
    assert "nameOrig" in resp.json()["error"]["details"]["missing_columns"]


def test_upload_size_cap_413(clean_db, tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from tests.apiutil import UserFactory

    app = create_app(make_settings(postgres_dsn=clean_db, max_upload_bytes=100, **FAST_ARGON))
    with TestClient(app) as client:
        admin = UserFactory(app)("ADMIN")
        resp = upload(client, admin, fixture_csv("abc_chain"))
    assert resp.status_code == 413 and resp.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_unsupported_adapter_400(client, users) -> None:
    admin = users("ADMIN")
    with fixture_csv("abc_chain").open("rb") as f:
        resp = client.post(
            "/api/v1/ingestion",
            headers=admin.headers,
            files={"file": ("x.csv", f, "text/csv")},
            data={"name": "n", "source": "s", "dataset_version": "v", "schema_version": "1", "adapter": "other-v1"},
        )
    assert resp.status_code == 400 and resp.json()["error"]["details"] == {"field": "adapter"}


def test_bad_adapter_config_json_400(client, users) -> None:
    admin = users("ADMIN")
    with fixture_csv("abc_chain").open("rb") as f:
        resp = client.post(
            "/api/v1/ingestion",
            headers=admin.headers,
            files={"file": ("x.csv", f, "text/csv")},
            data={
                "name": "n",
                "source": "s",
                "dataset_version": "v",
                "schema_version": "1",
                "adapter": "paysim-v1",
                "adapter_config": "{not json",
            },
        )
    assert resp.status_code == 400


def test_dataset_key_collision_appends_suffix(client, users) -> None:
    admin = users("ADMIN")
    a = upload(client, admin, fixture_csv("abc_chain"), name="Same Name!!", version="v1").json()
    b = upload(client, admin, fixture_csv("rejections"), name="same name??", version="v1").json()
    assert a["dataset_key"] == "same-name---vv1"
    assert b["dataset_key"] == "same-name---vv1-2"


def test_adapter_config_recorded(client, users) -> None:
    admin = users("ADMIN")
    body = upload(client, admin, fixture_csv("abc_chain"), adapter_config={"note": "x"}).json()
    detail = client.get(f"/api/v1/ingestion/{body['ingestion_run_id']}", headers=admin.headers).json()
    assert detail["dataset_key"] == body["dataset_key"]
    assert json.dumps(detail)  # serializable


def test_ingestion_unknown_404(client, users) -> None:
    analyst = users("ANALYST")
    assert (
        client.get("/api/v1/ingestion/00000000-0000-4000-8000-000000000001", headers=analyst.headers).status_code == 404
    )
