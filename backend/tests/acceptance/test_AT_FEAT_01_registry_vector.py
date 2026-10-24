"""AT-FEAT-01: a fixed history gives F01–F42 values and states matching the registry (hand-computed)."""

import math

import pytest
from sqlalchemy import text

from mulenetx.api.deps import get_services
from mulenetx.features.registry import load
from tests.apiutil import _Req
from tests.ingestutil import expected, fixture_csv, run_worker, upload

pytestmark = pytest.mark.integration


def test_AT_FEAT_01_registry_vector(app, client, users) -> None:
    exp = expected("abc_chain")["features_CB_at_T"]["vector"]
    admin = users("ADMIN")
    key = upload(client, admin, fixture_csv("abc_chain"), name="feat one").json()["dataset_key"]
    run_worker(app)
    rt = get_services(_Req(app)).runtime
    with rt.engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT feature_values, feature_states, as_of, feature_version FROM account_feature_values "
                "WHERE account_id = :a"
            ),
            {"a": f"{key}:CB"},
        ).one()
        fv = conn.execute(text("SELECT definition_hash, feature_count FROM feature_versions")).one()
    reg = load()
    assert row.feature_version == "v1" and row.as_of.isoformat() == "2020-01-01T02:00:00+00:00"
    assert (fv.definition_hash, fv.feature_count) == (reg.definition_hash, 42)
    assert len(row.feature_values) == len(row.feature_states) == 42
    for i, fid in enumerate(reg.ids):
        want_value, want_state = exp[fid]
        assert row.feature_states[i] == want_state, fid
        if want_value is None:
            assert math.isnan(row.feature_values[i]), fid
        else:
            tol = 1e-5 if fid == "F14" else 1e-9
            assert row.feature_values[i] == pytest.approx(want_value, abs=tol), fid
