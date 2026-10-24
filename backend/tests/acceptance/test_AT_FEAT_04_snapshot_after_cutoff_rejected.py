"""AT-FEAT-04: generating features at T with a snapshot whose data_cutoff > T is rejected (service and DB)."""

import hashlib
from datetime import timedelta

import psycopg
import pytest

from mulenetx.api.deps import get_services
from mulenetx.features.service import FeatureService, SnapshotAfterCutoffError, usable_graph_context
from tests import dbutil
from tests.apiutil import _Req
from tests.ingestutil import seed_and_activate
from tests.seed import ANCHOR

pytestmark = pytest.mark.integration


def test_AT_FEAT_04_snapshot_after_cutoff_rejected(app, client, users) -> None:
    admin = users("ADMIN")
    ds = seed_and_activate(app, client, admin, [("CA", "CB", 10.0, 1), ("CB", "CC", 5.0, 9)], key="late")
    rt = get_services(_Req(app)).runtime
    with rt.session_factory() as db:
        ctx = usable_graph_context(db, ds.dataset_id, ANCHOR + timedelta(hours=9))
    assert ctx is not None and ctx.snapshot.data_cutoff == ANCHOR + timedelta(hours=9)
    T = ANCHOR + timedelta(hours=5)
    service = FeatureService(rt)
    with pytest.raises(SnapshotAfterCutoffError):
        list(service.vectors(ds.dataset_id, T, ["late:CA"], ctx))
    with pytest.raises(SnapshotAfterCutoffError):
        service.generate(ds.dataset_id, T, ctx)
    # the database refuses it as well
    with psycopg.connect(dbutil.app_dsn(driver=False)) as conn, pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO account_feature_values VALUES (gen_random_uuid(), 'late:CA', %s, 'v1', %s, %s, "
            "ARRAY[1.0]::float8[], ARRAY[0]::smallint[], now())",
            (T, ctx.snapshot.graph_snapshot_id, ctx.analytics_run.analytics_run_id),
        )
    assert hashlib.sha256(b"x").hexdigest()
