"""PaySim adapter (SRS §7.1.1, §6.2.1)."""

import io
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from mulenetx.ingestion.adapters.paysim_v1 import header_problems, normalize, read_rows, transaction_ref
from mulenetx.ingestion.validation import RowRejectedError

ANCHOR = datetime(2020, 1, 1, tzinfo=UTC)
ROW = {"step": "5", "type": "TRANSFER", "amount": "10.5", "nameOrig": "C1", "nameDest": "M2", "isFraud": "1"}


def test_timestamp_is_anchor_plus_step_hours() -> None:
    assert normalize(ROW, 1, ANCHOR).timestamp == datetime(2020, 1, 1, 5, tzinfo=UTC)
    assert normalize({**ROW, "step": "0"}, 1, ANCHOR).timestamp == ANCHOR
    assert normalize({**ROW, "step": "743"}, 1, ANCHOR).timestamp == datetime(2020, 1, 31, 23, tzinfo=UTC)


def test_amount_rounded_half_even_to_6dp() -> None:
    assert normalize({**ROW, "amount": "9.1234567"}, 1, ANCHOR).amount == Decimal("9.123457")
    assert normalize({**ROW, "amount": "0.0000005"}, 1, ANCHOR).amount == Decimal("0.000000")
    assert normalize({**ROW, "amount": "0.0000015"}, 1, ANCHOR).amount == Decimal("0.000002")


def test_transaction_ref_zero_padded() -> None:
    assert transaction_ref(7) == "0000000007"
    assert normalize(ROW, 12345, ANCHOR).source_transaction_ref == "0000012345"


def test_account_types_and_label() -> None:
    r = normalize(ROW, 1, ANCHOR)
    assert (r.source_account_type, r.destination_account_type, r.fraud_label) == ("CUSTOMER", "MERCHANT", True)


@pytest.mark.parametrize(
    ("override", "code"),
    [
        ({"amount": ""}, "MISSING_COLUMN"),
        ({"amount": "abc"}, "TYPE_ERROR"),
        ({"step": "x"}, "TYPE_ERROR"),
        ({"nameOrig": "Z9"}, "INVALID_ACCOUNT_ID"),
        ({"amount": "-1"}, "INVALID_AMOUNT"),
        ({"amount": "NaN"}, "INVALID_AMOUNT"),
        ({"amount": "1e20"}, "INVALID_AMOUNT"),
        ({"step": "-1"}, "INVALID_TIMESTAMP"),
        ({"type": "WIRE"}, "INVALID_TYPE"),
        ({"isFraud": "2"}, "INVALID_LABEL"),
        ({"nameDest": "C" + "9" * 200}, "FIELD_TOO_LONG"),
    ],
)
def test_rejection_codes(override: dict[str, str], code: str) -> None:
    with pytest.raises(RowRejectedError) as err:
        normalize({**ROW, **override}, 1, ANCHOR)
    assert err.value.code == code


def test_discarded_columns_never_leave_the_adapter() -> None:
    text = (
        "step,type,amount,nameOrig,oldbalanceOrg,newbalanceOrig,nameDest,oldbalanceDest,newbalanceDest,isFraud,"
        "isFlaggedFraud\n1,TRANSFER,1,C1,5,4,C2,6,7,0,1\n"
    )
    [(ordinal, row)] = list(read_rows(io.StringIO(text)))
    assert ordinal == 1
    assert set(row) == {"step", "type", "amount", "nameOrig", "nameDest", "isFraud"}


def test_source_record_hash_is_content_based() -> None:
    a = normalize(ROW, 1, ANCHOR)
    b = normalize(ROW, 2, ANCHOR)
    assert a.source_record_hash == b.source_record_hash and len(a.source_record_hash) == 64
    assert a.source_transaction_ref != b.source_transaction_ref


def test_header_problems() -> None:
    assert header_problems(["step", "type"]) == [
        "amount",
        "nameOrig",
        "oldbalanceOrg",
        "newbalanceOrig",
        "nameDest",
        "oldbalanceDest",
        "newbalanceDest",
        "isFraud",
        "isFlaggedFraud",
    ]
