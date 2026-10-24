"""Dataset profiling (SRS §7.9) on the abc_chain and rejections fixtures; values hand-computed."""

import pytest

from mulenetx.profiling.service import bounded_chains
from tests.ingestutil import expected, fixture_csv, run_worker, upload

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("fixture", ["abc_chain", "rejections"])
def test_profile_matches_hand_computed(app, client, users, fixture: str) -> None:
    admin = users("ADMIN")
    body = upload(client, admin, fixture_csv(fixture), name=fixture).json()
    run_worker(app)
    resp = client.get(f"/api/v1/datasets/{body['dataset_id']}/profile", headers=admin.headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["profile_version"] == "profile-v1"
    assert resp.json()["metrics"] == expected(fixture)["profile"]


def test_profile_404_before_profiling(client, users) -> None:
    analyst = users("ANALYST")
    resp = client.get("/api/v1/datasets/00000000-0000-4000-8000-000000000001/profile", headers=analyst.headers)
    assert resp.status_code == 404


def test_bounded_chains_truncates_deterministically() -> None:
    adjacency = {f"n{i}": [f"n{j}" for j in range(10) if j != i] for i in range(10)}
    a = bounded_chains(adjacency, 10, 500)
    b = bounded_chains(adjacency, 10, 500)
    assert a == b and a[2] is True
    assert bounded_chains({"a": ["b"], "b": ["c"], "c": ["a"]}, 10, 1000) == (2, 3, False)
