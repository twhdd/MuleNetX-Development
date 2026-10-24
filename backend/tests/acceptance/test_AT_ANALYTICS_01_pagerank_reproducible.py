"""AT-ANALYTICS-01: PageRank on a fixed graph is reproducible to 1e-9 (two independent analytics runs)."""

import random

import pytest
from sqlalchemy import text

from mulenetx.analytics.service import AnalyticsService
from mulenetx.api.deps import get_services
from mulenetx.db.models.lineage import GraphSnapshot
from tests.apiutil import _Req
from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration


def _fixed_graph(n: int = 60, m: int = 240) -> list[tuple[str, str, float, int]]:
    rng = random.Random(7)
    edges = []
    for i in range(m):
        a, b = rng.randrange(n), rng.randrange(n)
        if a != b:
            edges.append((f"C{a:03d}", f"C{b:03d}", round(rng.uniform(1, 1000), 2), i % 48))
    return edges


def test_AT_ANALYTICS_01_pagerank_reproducible(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, _fixed_graph(), key="an1")
    rt = get_services(_Req(app)).runtime
    with rt.session_factory() as db:
        snap = db.query(GraphSnapshot).filter(GraphSnapshot.purpose == "OPERATIONAL").one()
    second = AnalyticsService(rt).run(snap.graph_snapshot_id, snap.dataset_id, snap.data_cutoff)
    with rt.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT m.analytics_run_id, m.account_id, m.pagerank_raw, m.pagerank_norm, m.betweenness_raw "
                "FROM account_graph_metrics m JOIN analytics_runs r USING (analytics_run_id) "
                "WHERE r.graph_snapshot_id = :s ORDER BY m.account_id, m.analytics_run_id"
            ),
            {"s": snap.graph_snapshot_id},
        ).all()
        config = conn.execute(
            text("SELECT algorithm_configuration, analytics_version FROM analytics_runs WHERE graph_snapshot_id = :s"),
            {"s": snap.graph_snapshot_id},
        ).all()
    runs = sorted({r.analytics_run_id for r in rows})
    assert len(runs) == 2 and second.analytics_run_id in runs
    by_run = {run: {r.account_id: r for r in rows if r.analytics_run_id == run} for run in runs}
    a, b = by_run[runs[0]], by_run[runs[1]]
    assert a.keys() == b.keys() and len(a) >= 50
    for acc in a:
        assert abs(a[acc].pagerank_raw - b[acc].pagerank_raw) <= 1e-9
        assert abs(a[acc].betweenness_raw - b[acc].betweenness_raw) <= 1e-9
        assert a[acc].pagerank_norm == b[acc].pagerank_norm
    assert sum(r.pagerank_raw for r in a.values()) == pytest.approx(1.0, abs=1e-9)
    cfg = config[0].algorithm_configuration
    assert cfg["pagerank"]["damping"] == 0.85 and cfg["pagerank"]["max_iterations"] == 100
    assert cfg["pagerank"]["tolerance"] == 1e-6 and cfg["engine"] == "networkx"
    assert cfg["libraries"]["networkx"] and config[0].analytics_version == config[1].analytics_version
