"""AI investigation copilot (SRS §19.2: copilot.use; §21)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from mulenetx.api.deps import Services, get_db, get_services, require
from mulenetx.api.schemas.responses import CopilotResponse
from mulenetx.auth.service import Principal
from mulenetx.core.errors import limit_exceeded

router = APIRouter(prefix="/api/v1/copilot", tags=["copilot"])
MAX_QUESTION = 4000


class CopilotQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1)
    account_id: str | None = Field(default=None, max_length=160)
    case_id: str | None = Field(default=None, max_length=64)
    ring_id: str | None = Field(default=None, max_length=64)
    context_options: dict[str, bool] | None = None


@router.post("/query", response_model=CopilotResponse)
def query(
    body: CopilotQuery,
    request: Request,
    principal: Principal = Depends(require("copilot.use")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    if len(body.question) > MAX_QUESTION:
        raise limit_exceeded("question", MAX_QUESTION)
    return services.copilot.query(
        db,
        principal,
        body.question,
        body.account_id,
        body.case_id,
        body.ring_id,
        request.headers.get("X-Request-ID"),
        body.context_options,
    )
