"""OpenAPI export (PLAN T24). The document depends only on the code, never on the environment, so the app is
built with placeholder settings that open no connection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from mulenetx.core.config import Settings

_PLACEHOLDER = {
    "postgres_dsn": "postgresql+psycopg://openapi:openapi@127.0.0.1:1/openapi",
    "postgres_owner_dsn": "postgresql+psycopg://openapi:openapi@127.0.0.1:1/openapi",
    "neo4j_uri": "bolt://127.0.0.1:1",
    "neo4j_user": "openapi",
    "neo4j_password": "openapi-placeholder",
    "cors_allowed_origins": ["http://localhost:8080"],
    "artifact_dir": "/nonexistent/artifacts",
    "staging_dir": "/nonexistent/staging",
}


def _permissions(dep: Dependant, out: list[str], flags: set[str]) -> None:
    from mulenetx.api.deps import current_principal

    for sub in dep.dependencies:
        if sub.call is current_principal:
            flags.add("authenticated")
        permission = getattr(sub.call, "permission", None)
        if permission is not None and permission not in out:
            out.append(permission)
        _permissions(sub, out, flags)


def _error_envelope(doc: dict[str, Any]) -> None:
    from mulenetx.api.schemas.responses import ErrorEnvelope

    schema = ErrorEnvelope.model_json_schema(ref_template="#/components/schemas/{model}")
    schemas = doc.setdefault("components", {}).setdefault("schemas", {})
    schemas.update(schema.pop("$defs", {}))
    schemas["ErrorEnvelope"] = schema
    schemas.pop("HTTPValidationError", None)
    schemas.pop("ValidationError", None)


def install(app: FastAPI) -> None:
    """Annotate every operation with `x-permission` (the SRS §19.2 permission column): the permissions its
    dependencies check, else `authenticated` or `public`. A route that checks a permission in its body
    declares the column text itself through `openapi_extra`."""
    base = app.openapi

    def annotated() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema
        doc = base()
        _error_envelope(doc)
        for route in app.routes:
            if not isinstance(route, APIRoute) or not route.include_in_schema:
                continue
            perms: list[str] = []
            flags: set[str] = set()
            _permissions(route.dependant, perms, flags)
            label = " / ".join(perms) or ("authenticated" if flags else "public")
            for method in route.methods:
                op = doc["paths"][route.path_format][method.lower()]
                op.setdefault("x-permission", label)
                # request validation errors are 400 VALIDATION_ERROR envelopes (§19.3), never 422
                op["responses"].pop("422", None)
                op["responses"]["default"] = {
                    "description": "Error envelope (SRS §19.3)",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorEnvelope"}}},
                }
        app.openapi_schema = doc
        return doc

    app.openapi = annotated  # type: ignore[method-assign]


def openapi_document() -> dict[str, Any]:
    from mulenetx.main import create_app

    app = create_app(Settings(**_PLACEHOLDER))  # type: ignore[arg-type]
    try:
        return app.openapi()
    finally:
        app.state.runtime.close()


def write_openapi(path: str) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(openapi_document(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out
