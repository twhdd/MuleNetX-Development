from fastapi import APIRouter

from pydantic import BaseModel

from backend.core.auth import (
    create_access_token
)

from backend.services.token_service import (
    verify_refresh_token
)

router = APIRouter()


class RefreshRequest(
    BaseModel
):
    refresh_token: str


@router.post(
    "/auth/refresh"
)
def refresh(
    body: RefreshRequest
):

    payload = verify_refresh_token(
        body.refresh_token
    )

    token = create_access_token(
        payload["sub"],
        "analyst"
    )

    return {
        "access_token":
        token
    }
