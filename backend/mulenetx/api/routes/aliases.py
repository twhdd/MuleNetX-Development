"""Compatibility aliases of SRS §19.2.1. Each alias has its target's permission, parameters, response and
errors, and adds `Deprecation: true` and a `Link` header naming the target."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from mulenetx.api.deps import Services, get_db, get_services, require
from mulenetx.api.routes.pipelines import retry_run
from mulenetx.api.schemas.responses import (
    EvaluationLevelOut,
    EvaluationSummaryOut,
    PathQueryOut,
    PipelineAccepted,
    RingOut,
    RingPage,
)
from mulenetx.auth.service import Principal
from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.db.models.pipeline import PipelineRun

router = APIRouter(prefix="/api/v1", tags=["aliases"])


def deprecate(response: JSONResponse, target: str) -> JSONResponse:
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = f'<{target}>; rel="successor-version"'
    return response


@router.post("/ingestion/{ingestion_run_id}/retry", status_code=202, deprecated=True, response_model=PipelineAccepted)
def ingestion_retry(
    ingestion_run_id: uuid.UUID,
    request: Request,
    principal: Principal = Depends(require("pipeline.control")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> JSONResponse:
    run_id = db.execute(
        select(PipelineRun.pipeline_run_id)
        .where(PipelineRun.ingestion_run_id == ingestion_run_id)
        .order_by(PipelineRun.started_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if run_id is None:
        raise AppError(ec.NOT_FOUND, details={"resource": "ingestion"})
    response = retry_run(run_id, request, principal, db, services)
    return deprecate(response, f"/api/v1/pipeline-runs/{run_id}/retry")


@router.get("/money-flow", deprecated=True, response_model=PathQueryOut)
def money_flow(
    source_account_id: str = Query(...),
    destination_account_id: str = Query(...),
    mode: str = Query(default="SHORTEST"),
    max_depth: int = Query(default=5),
    max_results: int = Query(default=10),
    graph_snapshot_id: uuid.UUID | None = Query(default=None),
    _p: Principal = Depends(require("money_flow.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> JSONResponse:
    from mulenetx.api.routes.graph import run_path_query

    body = run_path_query(
        source_account_id, destination_account_id, mode, max_depth, max_results, graph_snapshot_id, db, services
    )
    return deprecate(JSONResponse(content=body), "/api/v1/graph/path")


@router.get("/fraud-ring-candidates", deprecated=True, response_model=RingPage)
def fraud_ring_candidates(
    candidate_class: str | None = Query(default=None, alias="class"),
    status: str | None = Query(default=None),
    min_score: str | None = Query(default=None),
    scoring_run_id: uuid.UUID | None = Query(default=None),
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("ring.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> JSONResponse:
    from mulenetx.api.routes.rings import list_rings_body

    body = list_rings_body(services, db, candidate_class, status, min_score, scoring_run_id, page, page_size)
    return deprecate(JSONResponse(content=body), "/api/v1/rings")


@router.get("/fraud-ring-candidates/{ring_id}", deprecated=True, response_model=RingOut)
def fraud_ring_candidate(
    ring_id: uuid.UUID, _p: Principal = Depends(require("ring.read")), db: Session = Depends(get_db)
) -> JSONResponse:
    from mulenetx.db.repositories import rings as ring_repo
    from mulenetx.db.repositories.context import active_lineage

    body = ring_repo.ring_view(db, ring_repo.get_candidate(db, ring_id), active_lineage(db))
    return deprecate(JSONResponse(content=body), f"/api/v1/rings/{ring_id}")


@router.get("/evaluation/summary", deprecated=True, response_model=EvaluationSummaryOut)
def evaluation_summary(
    _p: Principal = Depends(require("evaluation.read")), db: Session = Depends(get_db)
) -> JSONResponse:
    from mulenetx.api.routes.evaluation import latest_completed
    from mulenetx.evaluation import service as evaluation

    run = latest_completed(db)
    body = evaluation.summary(db, run)
    return deprecate(JSONResponse(content=body), f"/api/v1/evaluation/runs/{run.evaluation_run_id}")


@router.get("/evaluation/{level}", deprecated=True, response_model=EvaluationLevelOut)
def evaluation_level(
    level: str, _p: Principal = Depends(require("evaluation.read")), db: Session = Depends(get_db)
) -> JSONResponse:
    from mulenetx.api.routes.evaluation import latest_completed, level_body

    run = latest_completed(db)
    body = level_body(db, run, level.upper())
    return deprecate(JSONResponse(content=body), f"/api/v1/evaluation/runs/{run.evaluation_run_id}/{level.upper()}")
