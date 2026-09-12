from fastapi import APIRouter
from fastapi import WebSocket

from backend.core.websocket_manager import (
    manager
)

router = APIRouter()


@router.websocket(
    "/ws/live"
)
async def websocket_feed(
    websocket: WebSocket
):

    await manager.connect(
        websocket
    )

    try:

        while True:

            await websocket.receive_text()

    except Exception:

        manager.disconnect(
            websocket
        )
