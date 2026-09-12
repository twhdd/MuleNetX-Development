from backend.services.alert_engine import (
    evaluate_transaction
)


def process_transaction(
    source,
    target,
    amount
):

    return evaluate_transaction(
        source,
        target,
        amount
    )
