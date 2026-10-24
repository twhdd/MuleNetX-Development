"""AT-SEC-03 over the whole API (SRS §27.6): SQL and Cypher injection payloads in every path and query string
parameter of every GET operation in the exported OpenAPI document, plus the free-text bodies.

For every request: no 5xx, errors in the §19.3 envelope, and nothing in the body that leaks SQL, Cypher, stack
traces, driver names or filesystem paths. Afterwards the canonical tables and the graph are unchanged."""

import json
from typing import Any

import pytest
from sqlalchemy import text

from mulenetx.api.deps import get_services
from tests.apiutil import _Req
from tests.copilotutil import install
from tests.ingestutil import seed_and_activate
from tests.openapiutil import document

pytestmark = pytest.mark.integration

PAYLOADS = [
    "' OR '1'='1",
    "'; DROP TABLE accounts; --",
    "x' UNION SELECT password_hash FROM users --",
    "x' }) MATCH (n) DETACH DELETE n //",
    "') CALL db.labels() YIELD label RETURN label //",
    "../../../../etc/passwd",
]
LEAKS = (
    "Traceback",
    "SELECT ",
    "psycopg",
    "sqlalchemy",
    "neo4j.exceptions",
    "MATCH (",
    "/Users/",
    "/app/",
    "site-packages",
    "password_hash",
    "CypherSyntaxError",
)
SKIP = {("GET", "/health"), ("GET", "/ready")}


def get_operations() -> list[tuple[str, list[dict[str, Any]]]]:
    out = []
    for path, ops in document()["paths"].items():
        op = ops.get("get")
        if op is None or ("GET", path) in SKIP:
            continue
        params = [p for p in op.get("parameters", []) if "string" in json.dumps(p.get("schema", {}))]
        if params:
            out.append((path, params))
    return out


def counts(app: Any) -> tuple[int, int, int, int]:
    rt = get_services(_Req(app)).runtime
    with rt.engine.connect() as conn:
        accounts = conn.execute(text("SELECT count(*) FROM accounts")).scalar_one()
        txs = conn.execute(text("SELECT count(*) FROM transactions")).scalar_one()
        users = conn.execute(text("SELECT count(*) FROM users")).scalar_one()
    nodes = rt.graph.run("MATCH (n) RETURN count(n) AS n")[0]["n"]
    return accounts, txs, users, nodes


def check(resp: Any, where: str, payload: str) -> None:
    assert resp.status_code < 500, f"{where}: {resp.status_code} {resp.text[:200]}"
    # stored free text is echoed back verbatim (as data); anything else matching is a leak
    body = resp.text.replace(json.dumps(payload)[1:-1], "")
    for needle in LEAKS:
        assert needle not in body, f"{where}: leaks {needle!r}"
    if resp.status_code >= 400:
        assert set(resp.json()["error"]) == {"code", "message", "request_id", "details"}, where


def test_AT_SEC_03_every_string_parameter(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, [("CA", "CB", 1.0, 1), ("CB", "CC", 2.0, 2)], key="fz")
    install(app)
    before = counts(app)
    ops = get_operations()
    assert len(ops) >= 40
    sent = 0
    for path, params in ops:
        valid = {p["name"]: "fz:CA" for p in params if p["in"] == "path"}
        for param in params:
            for payload in PAYLOADS:
                url = path
                query: dict[str, str] = {}
                if param["in"] == "path":
                    for name in valid:
                        url = url.replace("{" + name + "}", payload if name == param["name"] else valid[name])
                else:
                    for name in valid:
                        url = url.replace("{" + name + "}", valid[name])
                    query[param["name"]] = payload
                    if param["name"] != "account_id" and any(
                        p["name"] == "account_id" and p.get("required") for p in params
                    ):
                        query["account_id"] = "fz:CA"
                resp = client.get(url, params=query, headers=admin.headers)
                check(resp, f"GET {path} {param['name']}={payload!r}", payload)
                sent += 1
    # free-text bodies: stored as data, returned verbatim, never interpreted
    for payload in PAYLOADS:
        case = client.post("/api/v1/cases", json={"title": payload, "priority": "LOW"}, headers=admin.headers)
        check(case, "POST /cases", payload)
        assert case.json()["title"] == payload
        note = {"type": "NOTE", "description": payload, "source": payload}
        check(
            client.post(f"/api/v1/cases/{case.json()['case_id']}/findings", json=note, headers=admin.headers),
            "POST findings",
            payload,
        )
        sub = {"subject_type": "ACCOUNT", "subject_id": payload}
        check(
            client.post(f"/api/v1/cases/{case.json()['case_id']}/subjects", json=sub, headers=admin.headers),
            "POST subjects",
            payload,
        )
        check(
            client.post(
                "/api/v1/copilot/query", json={"question": payload, "account_id": "fz:CA"}, headers=admin.headers
            ),
            "POST copilot",
            payload,
        )
        check(client.post("/api/v1/auth/login", json={"username": payload, "password": payload}), "POST login", payload)
        sent += 6
    assert sent > 500
    assert counts(app) == before
