"""SRS §11.9: retraining with identical inputs reproduces test-split predictions to 1e-9."""

import pytest
from sqlalchemy import select

from mulenetx.api.deps import get_services
from mulenetx.db.models.datasets import Dataset
from mulenetx.ml.train import TrainingService
from tests.apiutil import _Req
from tests.seed import seed_dataset
from tests.synth import generate

pytestmark = pytest.mark.integration


def test_retrain_predictions_identical(app) -> None:
    rt = get_services(_Req(app)).runtime
    edges, fraud, types = generate(customers=200, mules=20, steps=50)
    ds = seed_dataset(rt, edges, key="rep", fraud=fraud, types=types)
    with rt.session_factory() as db:
        resolution = db.execute(select(Dataset.timestamp_resolution_seconds)).scalar_one()
    first = TrainingService(rt).train(ds.dataset_id, ds.ingestion_run_id, resolution)
    second = TrainingService(rt).train(ds.dataset_id, ds.ingestion_run_id, resolution)
    assert first.model_version and second.model_version
    assert first.test_predictions.keys() == second.test_predictions.keys() and first.test_predictions
    for account, p in first.test_predictions.items():
        assert abs(p - second.test_predictions[account]) <= 1e-9
    from mulenetx.db.models.lineage import RiskLogicVersion

    with rt.session_factory() as db:
        a = db.get(RiskLogicVersion, first.risk_logic_version).normalization_reference
        b = db.get(RiskLogicVersion, second.risk_logic_version).normalization_reference
    strip = lambda ref: {k: v for k, v in ref.items() if k != "model_version"}  # noqa: E731
    assert strip(a) == strip(b)  # identical normalization reference; each model links its own version
