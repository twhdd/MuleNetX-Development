from fastapi import APIRouter

from backend.services.graph_snapshot import (
    create_snapshot
)

router = APIRouter()


@router.post(
    "/snapshot"
)
def snapshot():

    return {
        "file":
        create_snapshot()
    }
