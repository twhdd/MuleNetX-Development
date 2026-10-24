"""Multi-level evaluation (SRS §19.2 evaluation rows, §19.16, §28.7)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mulenetx.api.deps import Services, get_db, get_services, require
from mulenetx.api.schemas.responses import (
    EvaluationAccepted,
    EvaluationLevelOut,
    EvaluationPage,
    EvaluationSummaryOut,
)
from mulenetx.auth.service import Principal
from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.core.pagination import offset_page, page_request
from mulenetx.db.models.evaluation import EvaluationRun
from mulenetx.evaluation import service

router = APIRouter(prefix="/api/v1/evaluation", tags=["evaluation"])


class EvaluationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_version: str | None = Field(default=None, max_length=100)
    configuration: dict[str, Any] | None = None


@router.post("/runs", status_code=202, response_model=EvaluationAccepted)
def start(
    request: Request,
    body: EvaluationBody | None = None,
    principal: Principal = Depends(require("pipeline.control")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> JSONResponse:
    body = body or EvaluationBody()
    run = service.submit(
        db,
        services.runtime.settings,
        services.audit,
        principal,
        body.model_version,
        body.configuration,
        request.headers.get("X-Request-ID"),
    )
    return JSONResponse(status_code=202, content={"evaluation_run_id": str(run.evaluation_run_id), "status": "QUEUED"})


@router.get("/runs", response_model=EvaluationPage)
def list_runs(
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("evaluation.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    total = int(db.execute(select(func.count()).select_from(EvaluationRun)).scalar_one())
    rows = db.execute(
        select(EvaluationRun)
        .order_by(EvaluationRun.created_at.desc(), EvaluationRun.evaluation_run_id)
        .offset(req.offset)
        .limit(req.page_size)
    ).scalars()
    return offset_page([service.run_view(db, r) for r in rows], req, total, s.pagination_count_cap)


def get_run(db: Session, run_id: uuid.UUID) -> EvaluationRun:
    run = db.get(EvaluationRun, run_id)
    if run is None:
        raise AppError(ec.NOT_FOUND, details={"resource": "evaluation_run"})
    return run


def latest_completed(db: Session) -> EvaluationRun:
    run = db.execute(
        select(EvaluationRun)
        .where(EvaluationRun.status == "COMPLETED")
        .order_by(EvaluationRun.completed_at.desc(), EvaluationRun.evaluation_run_id)
        .limit(1)
    ).scalar_one_or_none()
    if run is None:
        raise AppError(ec.EVALUATION_NOT_AVAILABLE)
    return run


def level_body(db: Session, run: EvaluationRun, level: str) -> dict[str, Any]:
    if level not in service.LEVELS:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "level", "allowed": list(service.LEVELS)})
    if run.status != "COMPLETED":
        raise AppError(ec.CONFLICT, "The evaluation run has not completed.", {"status": run.status})
    return {
        "evaluation_run_id": str(run.evaluation_run_id),
        "level": level,
        "metrics": [service.metric_view(m) for m in service.metrics_of(db, run.evaluation_run_id, level)],
        "limitation": service.LIMITATION,
    }


@router.get("/runs/{run_id}", response_model=EvaluationSummaryOut)
def get_summary(
    run_id: uuid.UUID, _p: Principal = Depends(require("evaluation.read")), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return service.summary(db, get_run(db, run_id))


@router.get("/runs/{run_id}/{level}", response_model=EvaluationLevelOut)
def get_level(
    run_id: uuid.UUID, level: str, _p: Principal = Depends(require("evaluation.read")), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return level_body(db, get_run(db, run_id), level.upper())
