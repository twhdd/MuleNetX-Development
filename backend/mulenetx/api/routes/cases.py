"""Cases, subjects and findings (SRS §19.2, §19.10, §17, §22.2)."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from mulenetx.api.deps import Services, deny, get_db, get_services, require
from mulenetx.api.schemas.responses import CaseOut, FindingOut, PageOf, SubjectOut
from mulenetx.auth.service import Principal
from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.core.pagination import offset_page, page_request
from mulenetx.investigation.cases import STATUSES
from mulenetx.investigation.service import case_view, finding_view, subject_view

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])

Priority = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
Status = Literal["OPEN", "IN_REVIEW", "ESCALATED", "RESOLVED", "FALSE_POSITIVE", "CLOSED"]


class CaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=250)
    priority: Priority
    assigned_to: uuid.UUID | None = None


class CasePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int
    status: Status | None = None
    title: str | None = Field(default=None, min_length=1, max_length=250)
    priority: Priority | None = None
    assigned_to: uuid.UUID | None = None


class SubjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_type: Literal["ACCOUNT", "TRANSACTION", "RING", "SCENARIO"]
    subject_id: str = Field(min_length=1, max_length=160)


class FindingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1)
    evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    source: str = Field(min_length=1, max_length=100)


def _denier(services: Services, principal: Principal, request: Request):  # type: ignore[no-untyped-def]
    def make(permission: str, resource_id: str | None) -> AppError:
        return deny(services, principal, permission, request, resource_id)

    return make


@router.get("", response_model=PageOf[CaseOut])
def list_cases(
    status: str | None = Query(default=None),
    assigned_to: uuid.UUID | None = Query(default=None),
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("case.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    if status is not None and status not in STATUSES:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "status"})
    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    rows, total = services.investigation.list_cases(db, req, status, assigned_to)
    return offset_page([case_view(c) for c in rows], req, total, s.pagination_count_cap)


@router.post("", status_code=201, response_model=CaseOut)
def create_case(
    body: CaseCreate,
    request: Request,
    principal: Principal = Depends(require("case.create")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> JSONResponse:
    case = services.investigation.create(
        db, principal, body.title, body.priority, body.assigned_to, _denier(services, principal, request)
    )
    return JSONResponse(status_code=201, content=case_view(case))


@router.get("/{case_id}", response_model=CaseOut)
def get_case(
    case_id: uuid.UUID,
    _p: Principal = Depends(require("case.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    return case_view(services.investigation.get(db, case_id))


@router.patch("/{case_id}", response_model=CaseOut)
def patch_case(
    case_id: uuid.UUID,
    body: CasePatch,
    request: Request,
    principal: Principal = Depends(require("case.update")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    changes = {k: getattr(body, k) for k in body.model_fields_set if k != "version"}
    case = services.investigation.patch(
        db, principal, case_id, body.version, changes, _denier(services, principal, request)
    )
    return case_view(case)


@router.get("/{case_id}/subjects", response_model=PageOf[SubjectOut])
def list_subjects(
    case_id: uuid.UUID,
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("case.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    services.investigation.get(db, case_id)
    rows, total = services.investigation.subjects(db, case_id, req)
    return offset_page([subject_view(x) for x in rows], req, total, s.pagination_count_cap)


@router.post("/{case_id}/subjects", status_code=201, response_model=SubjectOut)
def add_subject(
    case_id: uuid.UUID,
    body: SubjectCreate,
    request: Request,
    principal: Principal = Depends(require("case_subject.manage")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> JSONResponse:
    subject = services.investigation.add_subject(
        db, principal, case_id, body.subject_type, body.subject_id, _denier(services, principal, request)
    )
    return JSONResponse(status_code=201, content=subject_view(subject))


@router.delete("/{case_id}/subjects/{subject_type}/{subject_id}", status_code=204, response_class=Response)
def remove_subject(
    case_id: uuid.UUID,
    subject_type: str,
    subject_id: str,
    request: Request,
    principal: Principal = Depends(require("case_subject.manage")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> Response:
    services.investigation.remove_subject(
        db, principal, case_id, subject_type, subject_id, _denier(services, principal, request)
    )
    return Response(status_code=204)


@router.post("/{case_id}/findings", status_code=201, response_model=FindingOut)
def add_finding(
    case_id: uuid.UUID,
    body: FindingCreate,
    request: Request,
    principal: Principal = Depends(require("finding.create")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> JSONResponse:
    finding = services.investigation.add_finding(
        db,
        principal,
        case_id,
        body.type,
        body.description,
        body.evidence,
        body.source,
        _denier(services, principal, request),
    )
    return JSONResponse(status_code=201, content=finding_view(finding))


@router.get("/{case_id}/findings", response_model=PageOf[FindingOut])
def list_findings(
    case_id: uuid.UUID,
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("case.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    services.investigation.get(db, case_id)
    rows, total = services.investigation.findings(db, case_id, req)
    return offset_page([finding_view(f) for f in rows], req, total, s.pagination_count_cap)
