from fastapi import HTTPException

from backend.core.permissions import (
    ROLE_PERMISSIONS
)


def require_permission(
    user,
    permission
):

    permissions = (
        ROLE_PERMISSIONS.get(
            user["role"],
            []
        )
    )

    if permission not in permissions:

        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )
