from fastapi import APIRouter

from backend.services.intelligence.recommendation_engine import engine

router = APIRouter(
    prefix="/recommendation",
    tags=["Recommendation Engine"]
)


@router.get("/")
def recommendation():

    return engine.generate()
