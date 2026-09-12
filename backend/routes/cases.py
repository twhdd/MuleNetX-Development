from fastapi import APIRouter

from pydantic import BaseModel

from investigation_engine.case_management.service import (
    add_account,
    add_evidence,
    create_case,
    get_case,
    get_cases,
    update_status
)

router = APIRouter()


class CaseRequest(BaseModel):

    title: str
    description: str


class AccountRequest(BaseModel):

    account: str


class EvidenceRequest(BaseModel):

    evidence: str


class StatusRequest(BaseModel):

    status: str


@router.post("/cases")
def create(
    body: CaseRequest
):

    return create_case(
        body.title,
        body.description
    )


@router.get("/cases")
def all_cases():

    return get_cases()


@router.get("/cases/{case_id}")
def case(
    case_id: str
):

    return get_case(
        case_id
    )


@router.post(
    "/cases/{case_id}/account"
)
def account(
    case_id: str,
    body: AccountRequest
):

    add_account(
        case_id,
        body.account
    )

    return {
        "success": True
    }


@router.post(
    "/cases/{case_id}/evidence"
)
def evidence(
    case_id: str,
    body: EvidenceRequest
):

    add_evidence(
        case_id,
        body.evidence
    )

    return {
        "success": True
    }


@router.put(
    "/cases/{case_id}/status"
)
def status(
    case_id: str,
    body: StatusRequest
):

    update_status(
        case_id,
        body.status
    )

    return {
        "success": True
    }
