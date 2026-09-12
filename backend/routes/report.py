from fastapi import APIRouter
from fastapi.responses import FileResponse

from investigation_engine.copilot.report_generator import (
    generate_report
)

from investigation_engine.reports.pdf_generator import (
    generate_pdf
)

router = APIRouter()


@router.get(
    "/report/account/{account_id}"
)
def create_report(
    account_id: str
):

    result = generate_report(
        account_id
    )

    pdf_path = generate_pdf(
        account_id,
        result["report"]
    )

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"{account_id}.pdf"
    )
