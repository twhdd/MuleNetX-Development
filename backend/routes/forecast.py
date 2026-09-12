from fastapi import APIRouter

from backend.services.intelligence.forecast_engine import engine

router = APIRouter(
    prefix="/forecast",
    tags=["Forecast Engine"]
)


@router.get("/")
def forecast():

    return engine.forecast()
