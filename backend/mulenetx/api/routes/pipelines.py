"""Pipeline runs (SRS §19.2: pipeline.read / pipeline.control; §7.6–§7.7)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from mulenetx.api.deps import Services, get_db, get_services, require
from mulenetx.api.schemas.responses import PageOf, PipelineAccepted, PipelineRunOut
from mulenetx.auth.service import Principal
from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.core.pagination import offset_page, page_request
from mulenetx.jobs.pipeline_state import STATES
from mulenetx.jobs.service import run_view

router = APIRouter(prefix="/api/v1/pipeline-runs", tags=["pipelines"])


class StartPipeline(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_id: uuid.UUID


def _rid(request: Request) -> str | None:
    rid = request.scope.get("state", {}).get("request_id")
    return rid if isinstance(rid, str) else None


@router.get("", response_model=PageOf[PipelineRunOut])
def list_runs(
    dataset_id: uuid.UUID | None = Query(default=None),
    state: str | None = Query(default=None),
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("pipeline.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    s = services.runtime.settings
    if state is not None and state not in STATES:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "state"})
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    runs, total = services.jobs.list_runs(db, req, dataset_id, state)
    return offset_page([run_view(r) for r in runs], req, total, s.pagination_count_cap)


@router.get("/{run_id}", response_model=PipelineRunOut)
def get_run(
    run_id: uuid.UUID,
    _p: Principal = Depends(require("pipeline.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    run = services.jobs.get_run(db, run_id)
    return run_view(run, services.jobs.metrics(db, run))


@router.post("", status_code=202, response_model=PipelineAccepted)
def start(
    body: StartPipeline,
    request: Request,
    principal: Principal = Depends(require("pipeline.control")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> JSONResponse:
    run = services.jobs.start_pipeline(db, principal, body.dataset_id, _rid(request))
    return JSONResponse(
        status_code=202, content={"pipeline_run_id": str(run.pipeline_run_id), "status": run.current_state}
    )


def retry_run(
    run_id: uuid.UUID, request: Request, principal: Principal, db: Session, services: Services
) -> JSONResponse:
    run = services.jobs.retry(db, principal, run_id, _rid(request))
    return JSONResponse(
        status_code=202, content={"pipeline_run_id": str(run.pipeline_run_id), "status": run.current_state}
    )


@router.post("/{run_id}/retry", status_code=202, response_model=PipelineAccepted)
def retry(
    run_id: uuid.UUID,
    request: Request,
    principal: Principal = Depends(require("pipeline.control")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> JSONResponse:
    return retry_run(run_id, request, principal, db, services)
