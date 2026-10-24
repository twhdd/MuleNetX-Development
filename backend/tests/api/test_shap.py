"""SHAP endpoint errors (SRS §14.2–§14.3, §19.8)."""

from pathlib import Path

import pytest

from mulenetx.api.deps import get_services
from mulenetx.db.models.lineage import ModelVersion
from tests.apiutil import _Req
from tests.ingestutil import seed_and_activate, seed_synth_and_activate

pytestmark = pytest.mark.integration


def test_shap_limits_and_missing_artifact(app, client, users) -> None:
    admin = users("ADMIN")
    _ds, run = seed_synth_and_activate(app, client, admin, key="sh")
    url = "/api/v1/accounts/sh:C90001/shap"
    assert client.get(url, params={"top_n": 51}, headers=admin.headers).json()["error"]["code"] == "LIMIT_EXCEEDED"
    assert client.get(url, params={"top_n": 0}, headers=admin.headers).status_code == 400
    default = client.get(url, headers=admin.headers).json()
    assert len(default["contributions"]) == 10
    rt = get_services(_Req(app)).runtime
    with rt.session_factory() as db:
        artifact = Path(db.get(ModelVersion, run["model_version"]).artifact_reference)
    hidden = artifact.with_suffix(".hidden")
    artifact.rename(hidden)
    try:
        resp = client.get("/api/v1/accounts/sh:C90002/shap", headers=admin.headers)
        assert resp.status_code == 503 and resp.json()["error"]["code"] == "MODEL_UNAVAILABLE"
    finally:
        hidden.rename(artifact)
    wrong = client.get(url, params={"assessment_id": "00000000-0000-4000-8000-000000000001"}, headers=admin.headers)
    assert wrong.status_code == 404


def test_shap_without_ml_score(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, [(f"C{i}", f"C{i + 1}", 1.0, i) for i in range(10)], key="shn")
    resp = client.get("/api/v1/accounts/shn:C1/shap", headers=admin.headers)
    assert resp.status_code == 404 and resp.json()["error"]["code"] == "EXPLANATION_NOT_AVAILABLE"
