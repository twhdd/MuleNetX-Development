"""Transaction keyset pagination (SRS §19.6, §19.11)."""

import pytest

from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration


def _edges() -> list[tuple[str, str, float, int]]:
    out = []
    for i in range(25):
        out.append(("CA", "CB", float(i + 1), i))  # CA → CB at steps 0..24
    out.append(("CB", "CA", 7.0, 3))  # one incoming
    out.append(("CA", "CB", 99.0, 24))  # same timestamp as another row: tie broken by transaction_id
    return out


def test_keyset_pages_desc_with_cursor(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, _edges(), key="ks")
    seen = []
    cursor = None
    pages = 0
    while True:
        params = {"page_size": 10, "direction": "any"}
        if cursor:
            params["cursor"] = cursor
        body = client.get("/api/v1/accounts/ks:CA/transactions", params=params, headers=admin.headers).json()
        seen.extend(body["items"])
        pages += 1
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert pages == 3 and len(seen) == 27
    keys = [(t["timestamp"], t["transaction_id"]) for t in seen]
    assert keys == sorted(keys, reverse=True)
    assert len({t["transaction_id"] for t in seen}) == 27
    assert seen[0]["transaction_id"] == "ks:0000000027" and seen[1]["transaction_id"] == "ks:0000000025"
    incoming = [t for t in seen if t["direction"] == "in"]
    assert [t["transaction_id"] for t in incoming] == ["ks:0000000026"]


def test_filters(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, _edges(), key="kf")
    ins = client.get("/api/v1/accounts/kf:CA/transactions", params={"direction": "in"}, headers=admin.headers).json()
    assert [t["transaction_id"] for t in ins["items"]] == ["kf:0000000026"]
    ranged = client.get(
        "/api/v1/accounts/kf:CA/transactions",
        params={"start": "2020-01-01T00:00:00Z", "end": "2020-01-01T02:00:00Z", "direction": "out"},
        headers=admin.headers,
    ).json()
    assert [t["amount"] for t in ranged["items"]] == ["3.000000", "2.000000", "1.000000"]
    typed = client.get("/api/v1/accounts/kf:CA/transactions", params={"type": "CASH_IN"}, headers=admin.headers)
    assert typed.json()["items"] == []


def test_range_and_cursor_validation(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, _edges(), key="kv")
    url = "/api/v1/accounts/kv:CA/transactions"
    backwards = client.get(
        url, params={"start": "2020-02-01T00:00:00Z", "end": "2020-01-01T00:00:00Z"}, headers=admin.headers
    )
    assert backwards.status_code == 400
    too_long = client.get(
        url, params={"start": "2020-01-01T00:00:00Z", "end": "2020-03-01T00:00:00Z"}, headers=admin.headers
    )
    assert too_long.status_code == 400 and too_long.json()["error"]["code"] == "LIMIT_EXCEEDED"
    assert client.get(url, params={"cursor": "%%%"}, headers=admin.headers).status_code == 400
    assert client.get(url, params={"page_size": 101}, headers=admin.headers).status_code == 400
    assert client.get(url, params={"direction": "sideways"}, headers=admin.headers).status_code == 400
    assert client.get("/api/v1/accounts/kv:NONE/transactions", headers=admin.headers).status_code == 404
