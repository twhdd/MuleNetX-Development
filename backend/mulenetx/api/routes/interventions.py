"""Network intervention simulation (SRS §19.2 intervention rows, §19.15). Simulation only (§16A.1)."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mulenetx.api.deps import Services, get_db, get_services, require
from mulenetx.api.schemas.responses import (
    InterventionCandidatePage,
    ScenarioAccepted,
    ScenarioOut,
    ScenarioPage,
)
from mulenetx.auth.service import Principal
from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.core.pagination import offset_page, page_request
from mulenetx.db.models.interventions import InterventionCandidate, InterventionScenario
from mulenetx.interventions.service import Submission, candidate_view, ring_candidate, scenario_view

router = APIRouter(prefix="/api/v1", tags=["interventions"])


class SimulateBody(BaseModel):
    # only analytical fields exist: nothing here can map to a real blocking or freezing action (§19.15)
    model_config = ConfigDict(extra="forbid")
    mode: Literal["RANK", "EVALUATE"]
    intervention_type: (
        Literal["ACCOUNT_REMOVAL", "INTERMEDIARY_REMOVAL", "ACCOUNT_SET_REMOVAL", "EDGE_REMOVAL"] | None
    ) = None
    target_ids: list[str] | None = Field(default=None, max_length=10)


@router.post("/rings/{ring_id}/interventions/simulate", status_code=202, response_model=ScenarioAccepted)
def simulate(
    ring_id: uuid.UUID,
    body: SimulateBody,
    request: Request,
    principal: Principal = Depends(require("intervention.simulate")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> JSONResponse:
    scenario = services.interventions.submit(
        db,
        services.runtime.engine,
        principal,
        ring_id,
        Submission(body.mode, body.intervention_type, body.target_ids),
        request.headers.get("X-Request-ID"),
    )
    return JSONResponse(
        status_code=202,
        content={"scenario_id": str(scenario.scenario_id), "status": "QUEUED", "hypothetical": True},
    )


@router.get("/rings/{ring_id}/interventions", response_model=ScenarioPage)
def ring_interventions(
    ring_id: uuid.UUID,
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("ring.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    ring_candidate(db, ring_id)
    q = select(InterventionScenario).where(InterventionScenario.target_ring_id == ring_id)
    total = int(db.execute(select(func.count()).select_from(q.subquery())).scalar_one())
    rows = db.execute(
        q.order_by(InterventionScenario.created_at.desc(), InterventionScenario.scenario_id)
        .offset(req.offset)
        .limit(req.page_size)
    ).scalars()
    return {**offset_page([scenario_view(x) for x in rows], req, total, s.pagination_count_cap), "hypothetical": True}


def _scenario(db: Session, scenario_id: uuid.UUID) -> InterventionScenario:
    scenario = db.get(InterventionScenario, scenario_id)
    if scenario is None:
        raise AppError(ec.NOT_FOUND, details={"resource": "intervention_scenario"})
    return scenario


@router.get("/interventions/{scenario_id}", response_model=ScenarioOut)
def get_scenario(
    scenario_id: uuid.UUID, _p: Principal = Depends(require("ring.read")), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return scenario_view(_scenario(db, scenario_id))


@router.get("/interventions/{scenario_id}/candidates", response_model=InterventionCandidatePage)
def scenario_candidates(
    scenario_id: uuid.UUID,
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("ring.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    scenario = _scenario(db, scenario_id)
    if scenario.status != "COMPLETED":
        raise AppError(ec.SCENARIO_NOT_COMPLETED, details={"status": scenario.status})
    q = select(InterventionCandidate).where(InterventionCandidate.scenario_id == scenario_id)
    total = int(db.execute(select(func.count()).select_from(q.subquery())).scalar_one())
    rows = db.execute(q.order_by(InterventionCandidate.rank_position).offset(req.offset).limit(req.page_size)).scalars()
    items = [candidate_view(c, scenario.baseline_paths_truncated) for c in rows]
    return {
        **offset_page(items, req, total, s.pagination_count_cap),
        "hypothetical": True,
        "scenario": scenario_view(scenario),
    }
