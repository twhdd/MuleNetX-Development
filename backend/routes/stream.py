from fastapi import APIRouter

from backend.core.event_store import (
    get_events
)

router = APIRouter()


@router.get(
    "/stream/events"
)
def events():

    return get_events()
