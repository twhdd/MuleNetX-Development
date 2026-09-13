import uuid

from datetime import datetime

from investigation_engine.case_management.storage import (
    load_cases,
    save_cases
)


def create_case(
    title,
    description
):

    cases = load_cases()

    case = {
        "case_id":
        str(uuid.uuid4()),

        "title":
        title,

        "description":
        description,

        "status":
        "OPEN",

        "accounts":
        [],

        "evidence":
        [],

        "created_at":
        datetime.utcnow().isoformat()
    }

    cases.append(case)

    save_cases(cases)

    return case


def get_cases():

    return load_cases()


def get_case(
    case_id
):

    cases = load_cases()

    for case in cases:

        if case["case_id"] == case_id:
            return case

    return None


def add_account(
    case_id,
    account
):

    cases = load_cases()

    for case in cases:

        if case["case_id"] == case_id:

            if account not in case["accounts"]:
                case["accounts"].append(account)

    save_cases(cases)

    return True


def add_evidence(
    case_id,
    evidence
):

    cases = load_cases()

    for case in cases:

        if case["case_id"] == case_id:

            case["evidence"].append(
                evidence
            )

    save_cases(cases)

    return True


def update_status(
    case_id,
    status
):

    cases = load_cases()

    for case in cases:

        if case["case_id"] == case_id:

            case["status"] = status

    save_cases(cases)

    return True
