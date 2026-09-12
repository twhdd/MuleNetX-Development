from pathlib import Path

from backend.core.hash_report import (
    report_hash
)

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)

from reportlab.lib.styles import (
    getSampleStyleSheet
)


REPORT_DIR = Path(
    "investigation-engine/reports/generated"
)

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def generate_pdf(
    account_id: str,
    report: str
):

    output = REPORT_DIR / f"{account_id}.pdf"

    doc = SimpleDocTemplate(
        str(output)
    )

    styles = getSampleStyleSheet()

    content = [
        Paragraph(
            f"MuleNetX Investigation Report - {account_id}",
            styles["Title"]
        ),
        Spacer(1, 20),
        Paragraph(
            report.replace("\n", "<br/>"),
            styles["BodyText"]
        )
    ]

    doc.build(content)

    return str(output)
