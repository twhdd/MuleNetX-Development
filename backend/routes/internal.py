from fastapi import APIRouter

from pydantic import BaseModel

from backend.services.live_ingestion import (
    process_transaction
)

router = APIRouter()


class TransactionEvent(
    BaseModel
):
    source: str
    target: str
    amount: float


@router.post(
    "/internal/event"
)
def event(
    body: TransactionEvent
):

    return process_transaction(
        body.source,
        body.target,
        body.amount
    )
