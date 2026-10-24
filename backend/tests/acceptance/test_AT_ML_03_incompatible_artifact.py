"""AT-ML-03: an artifact with an incompatible feature version or regime (or a changed file) is rejected
with MODEL_INCOMPATIBLE."""

from pathlib import Path

import pytest

from mulenetx.api.deps import get_services
from mulenetx.db.models.lineage import ModelVersion
from mulenetx.ml.inference import ModelIncompatibleError, ScoringRequest, load_model
from tests.apiutil import _Req
from tests.ingestutil import seed_synth_and_activate

pytestmark = pytest.mark.integration


def test_AT_ML_03_incompatible_artifact(app, client, users) -> None:
    admin = users("ADMIN")
    _ds, run = seed_synth_and_activate(app, client, admin, key="ml3")
    rt = get_services(_Req(app)).runtime
    with rt.session_factory() as db:
        mv = db.get(ModelVersion, run["model_version"])
    assert mv is not None
    assert load_model(mv, ScoringRequest(feature_version="v1")) is not None
    with pytest.raises(ModelIncompatibleError, match="feature_version"):
        load_model(mv, ScoringRequest(feature_version="v2"))
    with pytest.raises(ModelIncompatibleError, match="feature_regime"):
        load_model(mv, ScoringRequest(feature_version="v1", feature_regime="PRIOR_RUN"))
    with pytest.raises(ModelIncompatibleError, match="target"):
        load_model(mv, ScoringRequest(feature_version="v1", target_definition_id="forward-v2"))
    path = Path(mv.artifact_reference)
    original = path.read_bytes()
    try:
        path.write_bytes(original + b" ")
        with pytest.raises(ModelIncompatibleError, match="checksum"):
            load_model(mv, ScoringRequest(feature_version="v1"))
    finally:
        path.write_bytes(original)
