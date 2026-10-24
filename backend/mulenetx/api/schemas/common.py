"""Shared response shapes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Page(BaseModel):
    items: list[dict[str, Any]]
    page: int
    page_size: int
    total: int
    total_is_capped: bool


class Accepted(BaseModel):
    status: str
    pipeline_run_id: str | None = None
