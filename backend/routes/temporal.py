from fastapi import APIRouter

from backend.services.intelligence.temporal_engine import engine

router = APIRouter(
    prefix="/temporal",
    tags=["Temporal Intelligence"]
)


@router.get("/")
def temporal():

    return engine.timeline()
