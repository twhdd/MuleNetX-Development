from backend.core.event_store import (
    push_event
)


def evaluate_transaction(
    source,
    target,
    amount
):

    risk = "LOW"

    if amount > 50000:
        risk = "HIGH"

    elif amount > 10000:
        risk = "MEDIUM"

    event = {
        "source": source,
        "target": target,
        "amount": amount,
        "risk": risk
    }

    push_event(event)

    return event
