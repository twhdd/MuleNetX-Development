"""Every stored assessment is reproducible from its own stored components (SRS §12.4), and stored ML scores equal
the model's prediction on the persisted feature vector (§10.7, §11.3)."""

from decimal import Decimal

import numpy as np
import pytest
from sqlalchemy import text

from mulenetx.api.deps import get_services
from mulenetx.core.decimal import D, round7
from mulenetx.db.models.lineage import ModelVersion
from mulenetx.ml.inference import ScoringRequest, load_model
from mulenetx.risk.compose import Components, compose
from tests.apiutil import _Req
from tests.ingestutil import seed_synth_and_activate
from tests.riskutil import THRESHOLDS, WEIGHTS

pytestmark = pytest.mark.integration


def test_assessments_reproducible_and_ml_scores_match_model(app, client, users) -> None:
    admin = users("ADMIN")
    _ds, run = seed_synth_and_activate(app, client, admin, key="integ")
    rt = get_services(_Req(app)).runtime
    with rt.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT r.*, a.feature_values FROM risk_assessments r JOIN account_feature_values a "
                "ON a.feature_snapshot_id = r.feature_snapshot_id AND a.account_id = r.account_id "
                "WHERE r.scoring_run_id = :s ORDER BY r.account_id"
            ),
            {"s": run["scoring_run_id"]},
        ).all()
    assert len(rows) > 100
    for r in rows:
        c = Components(r.ml_score, r.graph_signal_score, True, r.behavioral_signal_score, True, r.rule_signal_score)
        result = compose(c, r.propagated_risk, WEIGHTS, THRESHOLDS)
        assert result.pre_propagation_score == r.pre_propagation_score, r.account_id
        assert result.final_score == r.final_score and result.risk_tier == r.risk_tier, r.account_id
    assert len({r.ml_score for r in rows}) > 10
    with rt.session_factory() as db:
        model = load_model(db.get(ModelVersion, run["model_version"]), ScoringRequest(feature_version="v1"))
    preds = model.predict(np.array([r.feature_values for r in rows], dtype=np.float64))
    for r, p in zip(rows, preds, strict=True):
        assert r.ml_score == round7(D(float(p))), r.account_id
    assert isinstance(rows[0].final_score, Decimal)
