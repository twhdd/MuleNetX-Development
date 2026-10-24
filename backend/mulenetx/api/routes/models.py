"""Model registry read API (SRS §19.2: model.read)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from mulenetx.api.deps import Services, get_db, get_services, require
from mulenetx.api.schemas.responses import ModelOut, PageOf
from mulenetx.auth.service import Principal
from mulenetx.core.pagination import offset_page, page_request
from mulenetx.jobs.service import model_view

router = APIRouter(prefix="/api/v1/models", tags=["models"])


@router.get("", response_model=PageOf[ModelOut])
def list_models(
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("model.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    models, total = services.jobs.list_models(db, req)
    return offset_page([model_view(m) for m in models], req, total, s.pagination_count_cap)


@router.get("/{version}", response_model=ModelOut)
def get_model(
    version: str,
    _p: Principal = Depends(require("model.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    return model_view(services.jobs.get_model(db, version))
