from fastapi import APIRouter

from pydantic import BaseModel

from backend.core.auth import (
    create_access_token,
    verify_password
)

from backend.models.user_store import (
    USERS
)

router = APIRouter()


class LoginRequest(
    BaseModel
):
    username: str
    password: str


@router.post(
    "/auth/login"
)
def login(
    body: LoginRequest
):

    user = USERS.get(
        body.username
    )

    if not user:

        return {
            "error":
            "invalid credentials"
        }

    if not verify_password(
        body.password,
        user["password"]
    ):

        return {
            "error":
            "invalid credentials"
        }

    token = create_access_token(
        body.username,
        user["role"]
    )

    return {
        "access_token":
        token,

        "role":
        user["role"]
    }
