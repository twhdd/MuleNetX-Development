"""PaySim adapter `paysim-v1` (SRS §7.1.1, §6.2).

`isFlaggedFraud` and the four balance columns are discarded here, before any row leaves the adapter.
"""

from __future__ import annotations

import csv
import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Final, TextIO

from mulenetx.ingestion.validation import RowRejectedError

ADAPTER: Final[str] = "paysim-v1"
TIMESTAMP_RESOLUTION_SECONDS: Final[int] = 3600
REQUIRED_COLUMNS: Final[tuple[str, ...]] = (
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "newbalanceOrig",
    "nameDest",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud",
)
DISCARDED_COLUMNS: Final[frozenset[str]] = frozenset(
    {"isFlaggedFraud", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest"}
)
ALLOWED_TYPES: Final[frozenset[str]] = frozenset({"CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"})
ACCOUNT_TYPES: Final[dict[str, str]] = {"C": "CUSTOMER", "M": "MERCHANT"}
MAX_ACCOUNT_REF: Final[int] = 128
MAX_TYPE_LEN: Final[int] = 50
MAX_AMOUNT: Final[Decimal] = Decimal("100000000000000")  # NUMERIC(20,6): < 10^14
SIX_DP: Final[Decimal] = Decimal("0.000001")


@dataclass(frozen=True)
class NormalizedRow:
    ordinal: int
    source_transaction_ref: str
    source_account_ref: str
    source_account_type: str
    destination_account_ref: str
    destination_account_type: str
    amount: Decimal
    timestamp: datetime
    transaction_type: str
    fraud_label: bool
    source_record_hash: str


def header_problems(header: list[str]) -> list[str]:
    """Missing required columns of the source schema (checked synchronously at upload, §19.5)."""
    present = {h.strip() for h in header}
    return [c for c in REQUIRED_COLUMNS if c not in present]


def transaction_ref(ordinal: int) -> str:
    return f"{ordinal:010d}"


def _account(value: str) -> tuple[str, str]:
    ref = value.strip()
    if not ref:
        raise RowRejectedError("MISSING_COLUMN")
    if len(ref) > MAX_ACCOUNT_REF:
        raise RowRejectedError("FIELD_TOO_LONG")
    account_type = ACCOUNT_TYPES.get(ref[0])
    if account_type is None:
        raise RowRejectedError("INVALID_ACCOUNT_ID")
    return ref, account_type


def normalize(raw: dict[str, str | None], ordinal: int, epoch_anchor: datetime) -> NormalizedRow:
    """Validate and normalize one source row; raise RowRejectedError with the §7.3 reason code."""
    values: dict[str, str] = {}
    for column in ("step", "type", "amount", "nameOrig", "nameDest", "isFraud"):
        v = raw.get(column)
        if v is None or not v.strip():
            raise RowRejectedError("MISSING_COLUMN")
        values[column] = v.strip()

    if len(values["type"]) > MAX_TYPE_LEN:
        raise RowRejectedError("FIELD_TOO_LONG")
    src_ref, src_type = _account(values["nameOrig"])
    dst_ref, dst_type = _account(values["nameDest"])

    step_text = values["step"]
    if not step_text.lstrip("-").isdigit():
        raise RowRejectedError("TYPE_ERROR")
    step = int(step_text)
    if step < 0 or step > 24 * 365 * 100:
        raise RowRejectedError("INVALID_TIMESTAMP")
    timestamp = epoch_anchor + timedelta(hours=step)

    try:
        amount = Decimal(values["amount"])
    except InvalidOperation as exc:
        raise RowRejectedError("TYPE_ERROR") from exc
    if not amount.is_finite() or amount < 0:
        raise RowRejectedError("INVALID_AMOUNT")
    amount = amount.quantize(SIX_DP, rounding=ROUND_HALF_EVEN)
    if amount >= MAX_AMOUNT:
        raise RowRejectedError("INVALID_AMOUNT")

    if values["type"] not in ALLOWED_TYPES:
        raise RowRejectedError("INVALID_TYPE")
    if values["isFraud"] not in ("0", "1"):
        raise RowRejectedError("INVALID_LABEL")
    fraud = values["isFraud"] == "1"

    canonical = "|".join((str(step), values["type"], format(amount, "f"), src_ref, dst_ref, "1" if fraud else "0"))
    return NormalizedRow(
        ordinal=ordinal,
        source_transaction_ref=transaction_ref(ordinal),
        source_account_ref=src_ref,
        source_account_type=src_type,
        destination_account_ref=dst_ref,
        destination_account_type=dst_type,
        amount=amount,
        timestamp=timestamp,
        transaction_type=values["type"],
        fraud_label=fraud,
        source_record_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )


def read_rows(stream: TextIO) -> Iterator[tuple[int, dict[str, str | None]]]:
    """Yield (1-based row ordinal, row dict) with the discarded columns already removed."""
    reader = csv.DictReader(stream)
    for ordinal, row in enumerate(reader, start=1):
        if None in row:  # more fields than the header
            row.pop(None)
        yield ordinal, {k: v for k, v in row.items() if k not in DISCARDED_COLUMNS}
