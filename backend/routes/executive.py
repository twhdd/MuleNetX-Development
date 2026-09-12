from fastapi import APIRouter

from backend.services.executive_service import service

router = APIRouter(
    prefix="/executive",
    tags=["Executive Intelligence"]
)


@router.get("/summary")
def get_executive_summary():

    return service.generate_summary()
