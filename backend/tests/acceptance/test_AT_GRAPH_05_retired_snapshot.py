"""AT-GRAPH-05: a neighborhood request naming a retired snapshot returns 410 SNAPSHOT_RETIRED."""

import pytest
from sqlalchemy import select

from mulenetx.api.deps import get_services
from mulenetx.db.models.lineage import ActiveContext, GraphSnapshot
from tests.apiutil import _Req
from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration


def test_AT_GRAPH_05_retired_snapshot(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, [("CA", "CB", 1.0, 1)], key="g5a")
    rt = get_services(_Req(app)).runtime
    with rt.session_factory() as db:
        first = db.execute(select(ActiveContext)).scalar_one().graph_snapshot_id
    # activating another dataset version queues retirement of the previous operational snapshot (§6.8.6)
    seed_and_activate(app, client, admin, [("CA", "CB", 2.0, 1)], key="g5b")
    with rt.session_factory() as db:
        assert db.get(GraphSnapshot, first).status == "RETIRED"
    left = rt.graph.run("MATCH (n {snapshot_id:$s}) RETURN count(n) AS n", {"s": str(first)})[0]["n"]
    assert left == 0
    retired = client.get(
        "/api/v1/graph/neighborhood",
        params={"account_id": "g5a:CA", "graph_snapshot_id": str(first)},
        headers=admin.headers,
    )
    assert retired.status_code == 410 and retired.json()["error"]["code"] == "SNAPSHOT_RETIRED"
    current = client.get("/api/v1/graph/neighborhood", params={"account_id": "g5b:CA"}, headers=admin.headers)
    assert current.status_code == 200 and current.json()["graph_snapshot_id"] != str(first)
