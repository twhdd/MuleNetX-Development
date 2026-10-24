"""User administration (SRS §19.2, §22.2): `user.read`, `user.manage`, `role.manage`."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from mulenetx.api.deps import Services, deny, get_db, get_services, require
from mulenetx.api.schemas.auth import UserCreate, UserOut, UserPage, UserPatch
from mulenetx.auth.permissions import is_allowed
from mulenetx.auth.service import Principal, user_view
from mulenetx.core.pagination import offset_page, page_request

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=UserPage)
def list_users(
    request: Request,
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    principal: Principal = Depends(require("user.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> UserPage:
    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    users, total = services.auth.list_users(db, req)
    body = offset_page([user_view(u) for u in users], req, total, s.pagination_count_cap)
    return UserPage(**body)


@router.post("", status_code=201, response_model=UserOut)
def create_user(
    body: UserCreate,
    principal: Principal = Depends(require("user.manage")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> UserOut:
    user = services.auth.create_user(db, principal, body.username, body.role, body.password)
    return UserOut(**user_view(user))


@router.patch("/{user_id}", response_model=UserOut, openapi_extra={"x-permission": "user.manage / role.manage"})
def update_user(
    user_id: uuid.UUID,
    body: UserPatch,
    request: Request,
    principal: Principal = Depends(require("user.manage")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> UserOut:
    if body.role is not None and not is_allowed(principal.role, "role.manage"):
        raise deny(services, principal, "role.manage", request, str(user_id))
    user = services.auth.update_user(
        db, principal, user_id, role=body.role, is_active=body.is_active, password=body.password
    )
    return UserOut(**user_view(user))
