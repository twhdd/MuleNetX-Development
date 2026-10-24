"""Active context (SRS §6.9, §19.2: account.read)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from mulenetx.api.deps import Services, get_db, get_services, require
from mulenetx.api.schemas.responses import ContextOut
from mulenetx.auth.service import Principal

router = APIRouter(prefix="/api/v1/context", tags=["context"])


@router.get("", response_model=ContextOut)
def get_context(
    _p: Principal = Depends(require("account.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    return services.jobs.active_context(db)
