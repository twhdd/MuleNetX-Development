from enum import Enum
from datetime import datetime

from pydantic import BaseModel


class CaseStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class InvestigationCase(BaseModel):
    case_id: str
    title: str
    description: str
    created_at: datetime
    status: CaseStatus
    accounts: list[str]
    evidence: list[str]
