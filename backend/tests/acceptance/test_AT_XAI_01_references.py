"""AT-XAI-01: SHAP for a compatible assessment references the exact model, feature version and assessment, is
labelled as explaining the ML component only, and is additive in log-odds."""

import math

import pytest
from sqlalchemy import select

from mulenetx.api.deps import get_services
from mulenetx.db.models.account_analytics import RiskAssessment, ShapExplanation
from tests.apiutil import _Req
from tests.ingestutil import seed_synth_and_activate

pytestmark = pytest.mark.integration


def test_AT_XAI_01_references(app, client, users) -> None:
    admin = users("ADMIN")
    seed_synth_and_activate(app, client, admin, key="xai")
    account = "xai:C90000"
    rt = get_services(_Req(app)).runtime
    risk = client.get(f"/api/v1/accounts/{account}/risk", headers=admin.headers).json()
    resp = client.get(f"/api/v1/accounts/{account}/shap", params={"top_n": 42}, headers=admin.headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["assessment_id"] == risk["assessment_id"]
    assert body["model_version"] == risk["model_version"] and body["feature_version"] == "v1"
    assert body["explains"] == "ML_COMPONENT_ONLY" and "ML component" in body["statement"]
    assert body["output_space"] == "LOG_ODDS" and body["explainer"] == "tree_shap_path_dependent"
    assert len(body["contributions"]) == 42
    total = body["base_value"] + sum(c["shap"] for c in body["contributions"])
    ml = body["ml_score"]
    assert total == pytest.approx(math.log(ml / (1 - ml)), abs=1e-3)  # TreeSHAP additivity
    assert sum(c["relative_importance"] for c in body["contributions"]) == pytest.approx(1.0, abs=1e-9)
    risk_unavailable = [c for c in body["contributions"] if c["feature_id"] in ("F19", "F31", "F33", "F36", "F37")]
    assert all(c["state"] == "UNAVAILABLE" and c["value"] is None and c["shap"] == 0 for c in risk_unavailable)
    with rt.session_factory() as db:
        cached = db.get(ShapExplanation, __import__("uuid").UUID(body["assessment_id"]))
        assert cached is not None and cached.model_version == body["model_version"]
        ra = db.execute(select(RiskAssessment).where(RiskAssessment.account_id == account)).scalar_one()
        assert str(ra.assessment_id) == body["assessment_id"]
    again = client.get(f"/api/v1/accounts/{account}/shap", params={"top_n": 42}, headers=admin.headers).json()
    assert again["contributions"] == body["contributions"]  # served from the immutable cache
