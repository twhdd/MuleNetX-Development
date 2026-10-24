"""OpenAPI and SRS §19.2 helpers for the inventory and AT-API tests."""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SRS = Path(__file__).resolve().parents[2] / "docs" / "SRS.md"
ROW = re.compile(r"^\| (GET|POST|PATCH|DELETE|PUT) \| `([^`]+)` \| ([^|]+) \|(?: [^|]* \|)? (\d{3}) \|")
ALIAS = re.compile(r"^\| `(GET|POST|PATCH|DELETE) (/api/v1/[^`]+)` \| `(GET|POST|PATCH|DELETE) (/api/v1/[^`]+)`")


@dataclass(frozen=True)
class SrsRow:
    method: str
    path: str
    permission: str
    success: int


def norm(path: str) -> str:
    """Path template with every parameter name erased: `/cases/{case_id}` and `/cases/{id}` compare equal."""
    return re.sub(r"\{[^}]+\}", "{}", path)


def _section() -> list[str]:
    lines = SRS.read_text(encoding="utf-8").splitlines()
    start = lines.index("## 19.2 Endpoint Contract Matrix")
    end = lines.index("## 19.3 Standard Error Envelope")
    return lines[start:end]


@functools.cache
def srs_rows() -> tuple[SrsRow, ...]:
    rows = []
    for line in _section():
        m = ROW.match(line)
        if m is None:
            continue
        method, path, permission, success = m.groups()
        permission = re.sub(r"\s*\(\+.*\)$", "", permission.strip())
        rows.append(SrsRow(method, path, permission, int(success)))
    return tuple(rows)


@functools.cache
def srs_aliases() -> dict[tuple[str, str], tuple[str, str]]:
    out = {}
    for line in _section():
        m = ALIAS.match(line)
        if m is not None:
            out[(m.group(1), norm(m.group(2)))] = (m.group(3), norm(m.group(4)))
    return out


@functools.cache
def document() -> dict[str, Any]:
    from mulenetx.openapi import openapi_document

    return openapi_document()


def operations() -> dict[tuple[str, str], dict[str, Any]]:
    return {(method.upper(), norm(path)): op for path, ops in document()["paths"].items() for method, op in ops.items()}


def validate(method: str, template: str, status: int, body: Any) -> None:
    """Validate a JSON body against the operation's documented schema for `status` (or the default)."""
    op = operations()[(method, norm(template))]
    responses = op["responses"]
    assert str(status) in responses or status >= 400, f"{method} {template}: status {status} is not documented"
    spec = responses.get(str(status)) or responses["default"]
    schema = spec.get("content", {}).get("application/json", {}).get("schema")
    assert schema, f"{method} {template} {status}: no documented JSON schema"
    root = {**schema, "components": document()["components"]}
    errors = sorted(Draft202012Validator(root).iter_errors(body), key=lambda e: list(e.path))
    assert not errors, f"{method} {template} {status}: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errors[:5])
