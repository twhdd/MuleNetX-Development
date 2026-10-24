"""AT-SEC-03: SQL and Cypher injection payloads in queries and filters cause no injection or data escape.

These are the targeted cases; tests/security/test_injection_every_parameter.py sends the payloads to every
string parameter of every operation in the OpenAPI document.
"""

import pytest
from sqlalchemy import text

from mulenetx.api.deps import get_services
from tests.apiutil import _Req
from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration

SQL_PAYLOADS = [
    "' OR '1'='1",
    "'; DROP TABLE accounts; --",
    "C\\' UNION SELECT password_hash FROM users --",
    "%' OR 1=1 --",
    '" OR ""="',
]
CYPHER_PAYLOADS = [
    "x' }) MATCH (n) DETACH DELETE n //",
    'x"}) RETURN 1 UNION MATCH (n) RETURN n //',
    "') WITH 1 AS x CALL db.labels() YIELD label RETURN label //",
]


@pytest.fixture
def seeded(app, client, users):
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, [("CA", "CB", 1.0, 1), ("CB", "CC", 2.0, 2)], key="inj")
    return admin


def _intact(app) -> None:
    rt = get_services(_Req(app)).runtime
    with rt.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM accounts")).scalar() == 3
        assert conn.execute(text("SELECT count(*) FROM users")).scalar() >= 1
    assert rt.graph.run("MATCH (a:Account) RETURN count(a) AS n")[0]["n"] == 3


def test_AT_SEC_03_sql_injection_in_filters(app, client, seeded) -> None:
    for payload in SQL_PAYLOADS:
        for params in (
            {"q": payload},
            {"risk_tier": payload},
            {"account_type": payload},
            {"sort": payload},
            {"order": payload},
        ):
            resp = client.get("/api/v1/accounts", params=params, headers=seeded.headers)
            assert resp.status_code in (200, 400), (params, resp.status_code)
            if resp.status_code == 200:
                assert resp.json()["total"] == 0, params  # nothing escapes the parameterized filter
        for path in (f"/api/v1/accounts/{payload}", f"/api/v1/accounts/{payload}/transactions"):
            resp = client.get(path, headers=seeded.headers)
            assert resp.status_code in (400, 404), (path, resp.status_code)
        resp = client.get(
            "/api/v1/accounts/inj:CA/transactions", params={"cursor": payload, "type": payload}, headers=seeded.headers
        )
        assert resp.status_code in (200, 400)
        resp = client.get("/api/v1/pipeline-runs", params={"state": payload}, headers=seeded.headers)
        assert resp.status_code == 400
        resp = client.get("/api/v1/ingestion", params={"status": payload}, headers=seeded.headers)
        assert resp.status_code == 400
    _intact(app)


def test_AT_SEC_03_cypher_injection_in_graph_parameters(app, client, seeded) -> None:
    for payload in CYPHER_PAYLOADS + SQL_PAYLOADS:
        resp = client.get("/api/v1/graph/neighborhood", params={"account_id": payload}, headers=seeded.headers)
        assert resp.status_code == 404, (payload, resp.status_code)
        assert "nodes" not in resp.json()
        bad_snapshot = client.get(
            "/api/v1/graph/neighborhood",
            params={"account_id": "inj:CA", "graph_snapshot_id": payload},
            headers=seeded.headers,
        )
        assert bad_snapshot.status_code == 400
    _intact(app)


def test_AT_SEC_03_errors_leak_nothing(app, client, seeded) -> None:
    resp = client.get("/api/v1/accounts", params={"sort": "'; SELECT 1 --"}, headers=seeded.headers)
    body = resp.text
    for needle in ("SELECT", "Traceback", "psycopg", "sqlalchemy", "neo4j", "/Users/", "password"):
        assert needle not in body
