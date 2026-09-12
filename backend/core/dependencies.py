from fastapi import Header
from fastapi import HTTPException

from backend.core.auth import (
    verify_token
)


def current_user(
    authorization: str = Header(
        default=""
    )
):

    if not authorization:

        raise HTTPException(
            401,
            "Missing Token"
        )

    token = authorization.replace(
        "Bearer ",
        ""
    )

    try:

        return verify_token(
            token
        )

    except Exception:

        raise HTTPException(
            401,
            "Invalid Token"
        )
