"""Above-limit parameters are rejected with `400 LIMIT_EXCEEDED`, never clamped (SRS §19.4, §27.6), on every
operation of the exported OpenAPI document that takes a limit parameter. Path IDs are placeholders: limits are
checked before any lookup, so an above-limit request never reaches the data."""

import json

import pytest

from mulenetx.core.config import Settings
from tests.endpoints import PLACEHOLDER
from tests.openapiutil import document

pytestmark = pytest.mark.integration

S = Settings.model_construct()
ABOVE = {
    "page_size": S.max_page_size + 1,
    "top_n": S.shap_max_top_n + 1,
    "depth": S.graph_max_depth + 1,
    "max_nodes": S.graph_max_nodes + 1,
    "max_edges": S.graph_max_edges + 1,
    "max_depth": S.path_max_depth + 1,
    "max_results": S.path_max_results + 1,
}
REQUIRED = {
    "account_id": "x:A",
    "source_account_id": "x:A",
    "destination_account_id": "x:B",
    "graph_snapshot_id": PLACEHOLDER,
    "accounts": "x:A,x:B",
}


def cases() -> list[tuple[str, str, int]]:
    out = []
    for path, ops in document()["paths"].items():
        for method, op in ops.items():
            for p in op.get("parameters", []):
                if p["name"] in ABOVE and "integer" in json.dumps(p.get("schema", {})):
                    out.append((method.upper(), path, p["name"]))
    return out


CASES = cases()


def test_every_limit_parameter_is_covered() -> None:
    assert len(CASES) >= 30
    assert {name for _, _, name in CASES} == set(ABOVE)


@pytest.mark.parametrize(("method", "path", "name"), CASES, ids=[f"{m} {p} {n}" for m, p, n in CASES])
def test_above_limit_rejected(client, users, method, path, name) -> None:
    url = path
    for token in (
        "{id}",
        "{account_id}",
        "{ring_id}",
        "{case_id}",
        "{run_id}",
        "{version}",
        "{dataset_id}",
        "{scenario_id}",
        "{ingestion_run_id}",
        "{community_id}",
        "{path_id}",
        "{level}",
    ):
        url = url.replace(token, "x:A" if token == "{account_id}" else ("RING" if token == "{level}" else PLACEHOLDER))
    params = {name: ABOVE[name], **{k: v for k, v in REQUIRED.items() if k != name}}
    resp = client.request(method, url, params=params, headers=users("ADMIN").headers)
    assert resp.status_code == 400, f"{method} {url}: {resp.status_code} {resp.text[:200]}"
    assert resp.json()["error"]["code"] == "LIMIT_EXCEEDED", f"{method} {url}: {resp.text[:300]}"
