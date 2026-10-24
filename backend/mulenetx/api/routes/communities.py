"""Graph metrics and communities (SRS §19.2: graph.analytics.read, community.read)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from mulenetx.api.deps import Services, get_db, get_services, require
from mulenetx.api.schemas.responses import AccountCommunityOut, CommunityDetailOut, CommunityPage, GraphMetricsOut
from mulenetx.auth.service import Principal
from mulenetx.core.pagination import page_request
from mulenetx.db.repositories import accounts as account_repo
from mulenetx.db.repositories import communities as repo

router = APIRouter(prefix="/api/v1", tags=["communities"])


@router.get("/graph/metrics", response_model=GraphMetricsOut)
def graph_metrics(
    account_id: str = Query(...),
    analytics_run_id: uuid.UUID | None = Query(default=None),
    _p: Principal = Depends(require("graph.analytics.read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    account_repo.require(db, account_id)
    return repo.metrics(db, account_id, analytics_run_id)


@router.get("/communities", response_model=CommunityPage)
def list_communities(
    analytics_run_id: uuid.UUID | None = Query(default=None),
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("community.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    return repo.list_communities(db, analytics_run_id, req, s.pagination_count_cap)


@router.get("/communities/{community_id}", response_model=CommunityDetailOut)
def get_community(
    community_id: str,
    analytics_run_id: uuid.UUID | None = Query(default=None),
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("community.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    return repo.community_detail(db, community_id, analytics_run_id, req, s.pagination_count_cap)


@router.get("/accounts/{account_id}/community", response_model=AccountCommunityOut)
def account_community(
    account_id: str,
    analytics_run_id: uuid.UUID | None = Query(default=None),
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("community.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    account_repo.require(db, account_id)
    return repo.account_community(db, account_id, analytics_run_id, req, s.pagination_count_cap)
