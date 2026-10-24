"""Graph exploration (SRS §19.2, §19.9, §25.2)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from mulenetx.api.deps import Services, get_db, get_services, require
from mulenetx.api.schemas.responses import NeighborhoodOut, PathDetailOut, PathQueryOut
from mulenetx.auth.service import Principal
from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError, limit_exceeded
from mulenetx.graph.neighborhood import neighborhood

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])

DEFAULT_MAX_NODES = 100  # agent default (OQ-33)
DEFAULT_MAX_EDGES = 500
DEFAULT_PATH_DEPTH = 5  # interactive maximum (§16.7.1)
DEFAULT_PATH_RESULTS = 10  # agent default (OQ-60)


def bounded(name: str, value: int, maximum: int) -> int:
    """Reject (never clamp) out-of-range limits (§19.1)."""
    if value < 1:
        raise AppError(ec.VALIDATION_ERROR, details={"field": name})
    if value > maximum:
        raise limit_exceeded(name, maximum)
    return value


@router.get("/neighborhood", response_model=NeighborhoodOut)
def get_neighborhood(
    account_id: str = Query(...),
    depth: int = Query(default=1),
    max_nodes: int = Query(default=DEFAULT_MAX_NODES),
    max_edges: int = Query(default=DEFAULT_MAX_EDGES),
    graph_snapshot_id: uuid.UUID | None = Query(default=None),
    _p: Principal = Depends(require("graph.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    s = services.runtime.settings
    d = bounded("depth", depth, s.graph_max_depth)
    n = bounded("max_nodes", max_nodes, s.graph_max_nodes)
    e = bounded("max_edges", max_edges, s.graph_max_edges)
    return neighborhood(services.runtime, db, account_id, d, n, e, graph_snapshot_id)


def run_path_query(
    source_account_id: str,
    destination_account_id: str,
    mode: str,
    max_depth: int,
    max_results: int,
    graph_snapshot_id: uuid.UUID | None,
    db: Session,
    services: Services,
) -> dict[str, Any]:
    from mulenetx.flow.service import MoneyFlowService

    s = services.runtime.settings
    if mode not in ("SHORTEST", "ALL"):
        raise AppError(ec.VALIDATION_ERROR, details={"field": "mode"})
    d = bounded("max_depth", max_depth, s.path_max_depth)
    r = bounded("max_results", max_results, s.path_max_results)
    return MoneyFlowService(services.runtime).paths(
        db, source_account_id, destination_account_id, mode, d, r, graph_snapshot_id
    )


@router.get("/path", response_model=PathQueryOut)
def get_path(
    source_account_id: str = Query(...),
    destination_account_id: str = Query(...),
    mode: str = Query(default="SHORTEST"),
    max_depth: int = Query(default=DEFAULT_PATH_DEPTH),
    max_results: int = Query(default=DEFAULT_PATH_RESULTS),
    graph_snapshot_id: uuid.UUID | None = Query(default=None),
    _p: Principal = Depends(require("money_flow.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    return run_path_query(
        source_account_id, destination_account_id, mode, max_depth, max_results, graph_snapshot_id, db, services
    )


@router.get("/paths/{path_id}", response_model=PathDetailOut)
def get_path_by_id(
    path_id: uuid.UUID,
    graph_snapshot_id: uuid.UUID = Query(...),
    accounts: str = Query(..., description="comma-separated ordered account IDs of the path"),
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("money_flow.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    from mulenetx.core.pagination import page_request
    from mulenetx.flow.service import MoneyFlowService

    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    sequence = [a for a in accounts.split(",") if a]
    if len(sequence) > s.path_max_depth + 1:
        raise limit_exceeded("accounts", s.path_max_depth + 1)
    return MoneyFlowService(services.runtime).path_detail(
        db, path_id, graph_snapshot_id, sequence, req.page, req.page_size
    )
