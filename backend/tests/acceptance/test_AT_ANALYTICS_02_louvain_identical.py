"""AT-ANALYTICS-02: with a fixed export order, Louvain twice gives the identical partition and identical
canonical community IDs."""

import pytest
from sqlalchemy import text

from mulenetx.analytics.service import AnalyticsService
from mulenetx.api.deps import get_services
from mulenetx.core import ids
from mulenetx.db.models.lineage import GraphSnapshot
from tests.acceptance.test_AT_ANALYTICS_01_pagerank_reproducible import _fixed_graph
from tests.apiutil import _Req
from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration


def test_AT_ANALYTICS_02_louvain_identical(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, _fixed_graph(), key="an2")
    rt = get_services(_Req(app)).runtime
    with rt.session_factory() as db:
        snap = db.query(GraphSnapshot).filter(GraphSnapshot.purpose == "OPERATIONAL").one()
    AnalyticsService(rt).run(snap.graph_snapshot_id, snap.dataset_id, snap.data_cutoff)
    with rt.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT cm.analytics_run_id, cm.community_id, cm.account_id, ar.analytics_version "
                "FROM community_memberships cm JOIN analytics_runs ar USING (analytics_run_id) "
                "WHERE ar.graph_snapshot_id = :s"
            ),
            {"s": snap.graph_snapshot_id},
        ).all()
    runs = sorted({r.analytics_run_id for r in rows})
    assert len(runs) == 2

    def partition(run):  # type: ignore[no-untyped-def]
        groups: dict[str, set[str]] = {}
        for r in rows:
            if r.analytics_run_id == run:
                groups.setdefault(r.community_id, set()).add(r.account_id)
        return groups

    first, second = partition(runs[0]), partition(runs[1])
    assert first == second and len(first) >= 2
    version = rows[0].analytics_version
    for cid, members in first.items():
        assert cid == ids.community_id(snap.graph_snapshot_id, version, members)
