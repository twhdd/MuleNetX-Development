from fastapi import APIRouter
from fastapi import Depends

from backend.core.dependencies import (
    current_user
)

from backend.core.authorization import (
    require_permission
)

router = APIRouter()


@router.get(
    "/admin/health"
)
def admin_health(
    user=Depends(
        current_user
    )
):

    require_permission(
        user,
        "system:manage"
    )

    return {
        "status":
        "healthy"
    }
