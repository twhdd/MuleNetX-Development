from fastapi import APIRouter

from investigation_engine.copilot.report_generator import (
    generate_report
)

router = APIRouter()


@router.get(
    "/copilot/account/{account_id}"
)
def investigate_account(
    account_id: str
):

    return generate_report(
        account_id
    )
