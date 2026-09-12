from fastapi import APIRouter

from backend.services.intelligence.executive_engine import (
    engine
)

router = APIRouter(

    prefix="/executive-engine",

    tags=["Executive Engine"]

)


@router.get("/")
def executive():

    return engine.build()
