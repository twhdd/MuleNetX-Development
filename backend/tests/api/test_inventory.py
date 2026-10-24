"""Endpoint inventory (PLAN T24): the OpenAPI document matches the SRS §19.2 contract matrix.

`NOT_YET` lists the §19.2 endpoints of later phases; each later task removes its rows and T42 asserts it is
empty. An endpoint in `NOT_YET` must not exist yet, so the set cannot go stale.
"""

import json

import pytest

from tests.openapiutil import SRS, document, norm, operations, srs_aliases, srs_rows

NOT_YET: set[tuple[str, str]] = set()
NOT_YET_ALIASES: set[tuple[str, str]] = set()


def test_srs_matrix_parsed() -> None:
    rows = srs_rows()
    assert len(rows) == 64  # every row of the §19.2 tables
    assert len(srs_aliases()) == 6
    assert {(r.method, norm(r.path)) for r in rows} >= {(m, norm(p)) for m, p in NOT_YET}
    assert set(srs_aliases()) >= {(m, norm(p)) for m, p in NOT_YET_ALIASES}


def test_every_implemented_endpoint_has_srs_permission_and_status() -> None:
    ops = operations()
    pending = {(m, norm(p)) for m, p in NOT_YET}
    for row in srs_rows():
        key = (row.method, norm(row.path))
        if key in pending:
            assert key not in ops, f"{key} is implemented: remove it from NOT_YET"
            continue
        assert key in ops, f"{row.method} {row.path} is missing from the OpenAPI document"
        assert ops[key]["x-permission"] == row.permission, (key, ops[key]["x-permission"], row.permission)
        assert str(row.success) in ops[key]["responses"], (key, row.success, list(ops[key]["responses"]))
        assert "default" in ops[key]["responses"]  # error envelope documented


def test_no_undocumented_endpoint() -> None:
    srs = {(r.method, norm(r.path)) for r in srs_rows()}
    aliases = srs_aliases()
    pending_aliases = {(m, norm(p)) for m, p in NOT_YET_ALIASES}
    ops = operations()
    for key, op in ops.items():
        if key in srs:
            continue
        assert key in aliases, f"{key} is neither a §19.2 row nor a §19.2.1 alias"
        assert op.get("deprecated") is True, key
        target = aliases[key]
        if target in ops:
            assert op["x-permission"] == ops[target]["x-permission"], key
    for key in aliases:
        assert (key in ops) != (key in pending_aliases), f"alias {key}: implemented XOR pending"


def test_exported_document_is_current() -> None:
    exported = SRS.parent / "openapi.json"
    assert exported.exists(), "run `make openapi`"
    on_disk = json.loads(exported.read_text(encoding="utf-8"))
    assert on_disk == json.loads(json.dumps(document())), "docs/openapi.json is stale: run `make openapi`"


@pytest.mark.parametrize("path", ["/openapi.json", "/docs", "/redoc"])
def test_no_unauthenticated_schema_routes(client, path) -> None:
    assert client.get(path).status_code == 404  # only /health, /ready and login are public (§22)


def test_validator_rejects_drift() -> None:
    from tests.openapiutil import validate

    good = {"status": "UP"}
    validate("GET", "/health", 200, good)
    with pytest.raises(AssertionError):
        validate("GET", "/health", 200, {"status": "UP", "extra": 1})
    with pytest.raises(AssertionError):
        validate("GET", "/api/v1/cases/{id}", 200, {"case_id": "x"})
