from fastapi import HTTPException


def require_role(
    user,
    allowed
):

    if user["role"] not in allowed:

        raise HTTPException(
            403,
            "Forbidden"
        )
