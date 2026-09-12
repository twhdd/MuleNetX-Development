from fastapi import APIRouter

from backend.services.intelligence.decision_engine import (
    engine
)

router = APIRouter(

    prefix="/decision",

    tags=["Decision Intelligence"]

)


@router.get("/")
def decision():

    return engine.evaluate()
