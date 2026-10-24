"""Dataset ingestion (SRS §19.2, §19.5): upload, list, detail, dataset profile."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from mulenetx.api.deps import Services, get_db, get_services, require
from mulenetx.api.schemas.responses import IngestionAccepted, IngestionRunOut, PageOf, ProfileOut
from mulenetx.auth.service import Principal
from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.core.pagination import offset_page, page_request
from mulenetx.ingestion import staging
from mulenetx.ingestion.service import parse_adapter_config

router = APIRouter(prefix="/api/v1", tags=["ingestion"])
CSV_TYPES = {"text/csv"}


def _rid(request: Request) -> str | None:
    rid = request.scope.get("state", {}).get("request_id")
    return rid if isinstance(rid, str) else None


@router.post("/ingestion", status_code=202, response_model=IngestionAccepted)
def submit(
    request: Request,
    file: UploadFile = File(...),
    name: str = Form(...),
    source: str = Form(...),
    dataset_version: str = Form(...),
    schema_version: str = Form(...),
    adapter: str = Form(...),
    adapter_config: str | None = Form(default=None),
    principal: Principal = Depends(require("ingestion.create")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> JSONResponse:
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in CSV_TYPES:
        raise AppError(ec.UNSUPPORTED_MEDIA_TYPE, details={"accepted": sorted(CSV_TYPES)})
    cfg = parse_adapter_config(adapter_config)
    s = services.runtime.settings
    path, checksum, _size = staging.stream_to_staging(file.file, s.staging_dir, s.max_upload_bytes)
    try:
        missing = services.ingestion.check_header(path)
        if missing:
            raise AppError(
                ec.VALIDATION_ERROR, "The file header is missing required columns.", {"missing_columns": missing}
            )
        reg = services.ingestion.register(
            db,
            principal,
            name=name,
            source=source,
            dataset_version=dataset_version,
            schema_version=schema_version,
            adapter=adapter,
            adapter_config=cfg,
            staged_path=path,
            checksum=checksum,
            request_id=_rid(request),
        )
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return JSONResponse(
        status_code=202,
        content={
            "dataset_id": str(reg.dataset.dataset_id),
            "dataset_key": reg.dataset.dataset_key,
            "ingestion_run_id": str(reg.ingestion_run.ingestion_run_id),
            "pipeline_run_id": str(reg.pipeline_run.pipeline_run_id),
            "status": reg.ingestion_run.status,
        },
    )


@router.get("/ingestion", response_model=PageOf[IngestionRunOut])
def list_ingestions(
    dataset_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("ingestion.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    s = services.runtime.settings
    if status is not None and status not in ("CREATED", "RUNNING", "SUCCEEDED", "FAILED"):
        raise AppError(ec.VALIDATION_ERROR, details={"field": "status"})
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    items, total = services.ingestion.list(db, req, dataset_id, status)
    return offset_page(items, req, total, s.pagination_count_cap)


@router.get("/ingestion/{ingestion_run_id}", response_model=IngestionRunOut)
def get_ingestion(
    ingestion_run_id: uuid.UUID,
    _p: Principal = Depends(require("ingestion.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    return services.ingestion.get(db, ingestion_run_id)


@router.get("/datasets/{dataset_id}/profile", response_model=ProfileOut)
def get_profile(
    dataset_id: uuid.UUID,
    _p: Principal = Depends(require("ingestion.read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from mulenetx.db.models.datasets import DatasetProfile

    profile = db.get(DatasetProfile, dataset_id)
    if profile is None:
        raise AppError(ec.NOT_FOUND, details={"resource": "dataset_profile"})
    return {
        "dataset_id": str(profile.dataset_id),
        "profile_version": profile.profile_version,
        "metrics": profile.metrics,
        "created_at": profile.created_at.isoformat(),
    }
