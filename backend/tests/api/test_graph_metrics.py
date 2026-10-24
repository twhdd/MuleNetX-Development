"""GET /graph/metrics (SRS §19.2)."""

import pytest

from tests.ingestutil import expected, fixture_csv, run_worker, upload

pytestmark = pytest.mark.integration


def test_graph_metrics_abc(app, client, users) -> None:
    admin = users("ADMIN")
    key = upload(client, admin, fixture_csv("abc_chain"), name="metrics abc").json()["dataset_key"]
    run_worker(app)
    exp = expected("abc_chain")["analytics"]
    body = client.get("/api/v1/graph/metrics", params={"account_id": f"{key}:CB"}, headers=admin.headers).json()
    assert [body["degree"], body["in_degree"], body["out_degree"]] == exp["degree"]["CB"]
    assert body["betweenness_raw"] == exp["betweenness"]["CB"]
    assert body["pagerank_raw"] == pytest.approx(exp["pagerank"]["CB"], abs=1e-6)
    assert body["component_id"] == f"{key}:CA" and body["component_size"] == 3
    assert body["engine"] == "NETWORKX" and body["is_stale"] is False
    assert body["lineage"]["analytics_run_id"] == body["analytics_run_id"]
    assert (
        client.get("/api/v1/graph/metrics", params={"account_id": f"{key}:ZZ"}, headers=admin.headers).status_code
        == 404
    )
