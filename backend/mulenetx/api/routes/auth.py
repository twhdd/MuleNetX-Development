"""Authentication endpoints (SRS §19.2, §19.4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from mulenetx.api.deps import Services, current_principal, get_db, get_services
from mulenetx.api.schemas.auth import LoginRequest, LoginResponse, LoginUser, UserOut
from mulenetx.auth.service import Principal, user_view
from mulenetx.auth.throttle import client_ip
from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.db.models.auth import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest, request: Request, db: Session = Depends(get_db), services: Services = Depends(get_services)
) -> LoginResponse:
    ip = client_ip(request.client.host if request.client else None, request.headers.get("x-forwarded-for"))
    result = services.auth.login(db, body.username, body.password, ip)
    u = result.user
    return LoginResponse(
        access_token=result.token,
        expires_in=result.expires_in,
        user=LoginUser(user_id=str(u.user_id), username=u.username, role=u.role),
    )


@router.post("/logout", status_code=204, response_class=Response)
def logout(
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> Response:
    services.auth.logout(db, principal)
    return Response(status_code=204)


@router.get("/me", response_model=UserOut)
def me(principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> UserOut:
    user = db.get(User, principal.user_id)
    if user is None:
        raise AppError(ec.UNAUTHENTICATED)
    return UserOut(**user_view(user))
