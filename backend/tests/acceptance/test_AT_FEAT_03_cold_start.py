"""AT-FEAT-03: a cold-start account (no history at T) gets only the documented ZERO/UNAVAILABLE states."""

import math
from datetime import timedelta

import pytest

from mulenetx.api.deps import get_services
from mulenetx.db.models.lineage import AnalyticsRun, GraphSnapshot
from mulenetx.features.encoding import State
from mulenetx.features.registry import load
from mulenetx.features.service import FeatureService, usable_graph_context
from tests.apiutil import _Req
from tests.ingestutil import seed_and_activate
from tests.seed import ANCHOR

pytestmark = pytest.mark.integration


def test_AT_FEAT_03_cold_start_states(app, client, users) -> None:
    admin = users("ADMIN")
    ds = seed_and_activate(app, client, admin, [("CA", "CB", 10.0, 1), ("CC", "CD", 5.0, 9)], key="cold")
    rt = get_services(_Req(app)).runtime
    reg = load()
    T = ANCHOR + timedelta(hours=9)
    with rt.session_factory() as db:
        ctx = usable_graph_context(db, ds.dataset_id, T)
    assert ctx is not None
    # CC and CD only transact at step 9 = T, so at T − 1 h they have no history (cold start); with the
    # operational snapshot (cutoff step 9) unusable at T − 1 h, graph features are UNAVAILABLE too.
    earlier = T - timedelta(hours=1)
    with rt.session_factory() as db:
        assert usable_graph_context(db, ds.dataset_id, earlier) is None
    [vec] = list(FeatureService(rt).vectors(ds.dataset_id, earlier, ["cold:CC"], None))
    for i, fd in enumerate(reg.features):
        state = vec.states[i]
        if fd.cold_start == "UNAVAILABLE":
            assert state == State.UNAVAILABLE and math.isnan(vec.values[i]), fd.id
        else:
            assert state == State.ZERO and vec.values[i] == 0.0, fd.id
    with rt.session_factory() as db:
        snap = db.get(GraphSnapshot, ctx.snapshot.graph_snapshot_id)
        run = db.get(AnalyticsRun, ctx.analytics_run.analytics_run_id)
    assert snap is not None and run is not None
