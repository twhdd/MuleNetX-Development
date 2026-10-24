"""Liveness and readiness (SRS §26.3)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from mulenetx.api.schemas.responses import HealthOut, ReadyOut
from mulenetx.core.runtime import Runtime
from mulenetx.db.schema_version import code_head, database_revision

router = APIRouter()
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ready")


@router.get("/health", response_model=HealthOut)
def health() -> dict[str, str]:
    return {"status": "UP"}


def _postgres(rt: Runtime) -> tuple[str, dict[str, Any]]:
    try:
        revision = database_revision(rt.engine)
    except Exception:  # noqa: BLE001 - readiness reports, never raises
        return "DOWN", {"reason": "unreachable or schema missing"}
    expected = code_head()
    if revision != expected:
        return "DEGRADED", {"reason": "schema version mismatch", "database": revision, "expected": expected}
    return "UP", {"schema_version": revision}


def _neo4j(rt: Runtime) -> str:
    return "UP" if rt.graph.ping() else "DOWN"


def _ollama(rt: Runtime) -> str:
    try:
        resp = httpx.get(f"{rt.settings.ollama_url.rstrip('/')}/api/tags", timeout=1.0)
    except httpx.HTTPError:
        return "DOWN"
    return "UP" if resp.status_code == 200 else "DEGRADED"


def _worker_and_context(rt: Runtime) -> tuple[str, str]:
    try:
        with rt.engine.connect() as conn:
            running = conn.execute(
                text(
                    "SELECT count(*) AS n, count(*) FILTER (WHERE lease_expires_at > now()) AS live "
                    "FROM jobs WHERE status = 'RUNNING'"
                )
            ).one()
            ctx = conn.execute(text("SELECT dataset_id, scoring_run_id FROM active_context")).first()
    except Exception:  # noqa: BLE001
        return "DOWN", "DOWN"
    if running.n == 0:
        worker = "IDLE"
    else:
        worker = "UP" if running.live > 0 else "DOWN"
    context = "IDLE" if ctx is None or ctx.dataset_id is None else "UP"
    return worker, context


@router.get("/ready", response_model=ReadyOut, responses={503: {"model": ReadyOut}})
def ready(request: Request) -> JSONResponse:
    rt: Runtime = request.app.state.runtime
    pg_future = _POOL.submit(_postgres, rt)
    neo_future = _POOL.submit(_neo4j, rt)
    ollama_future = _POOL.submit(_ollama, rt)
    pg_state, pg_detail = pg_future.result()
    worker, context = _worker_and_context(rt) if pg_state != "DOWN" else ("DOWN", "DOWN")
    body = {
        "status": "READY" if pg_state == "UP" else "NOT_READY",
        "components": {
            "postgres": pg_state,
            "neo4j": neo_future.result(),
            "ollama": ollama_future.result(),
            "worker": worker,
            "active_context": context,
        },
        "details": {"postgres": pg_detail},
    }
    return JSONResponse(status_code=200 if pg_state == "UP" else 503, content=body)
