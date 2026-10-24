"""Deterministic point-in-time behavioural analytics for one account."""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from math import fsum, isfinite
from numbers import Real
from typing import Any, Optional


DEFAULT_WINDOW_STEPS = (1, 7, 30)


def _step(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a non-negative integer")
    try:
        integer_value = int(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{name} must be a non-negative integer") from error
    if integer_value != value or integer_value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return integer_value


def _field(row: Mapping[str, Any], names: tuple[str, ...], index: int) -> Any:
    for name in names:
        if name in row:
            return row[name]
    raise ValueError(f"transaction {index} is missing required field {names[0]}")


def _account(value: Any, field_name: str, index: Optional[int] = None) -> str:
    where = f" in transaction {index}" if index is not None else ""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name}{where} must be a non-empty string")
    return value


def _amount(value: Any, index: int) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"amount in transaction {index} must be a finite non-negative number")
    try:
        amount = float(value)
    except OverflowError as error:
        raise ValueError(
            f"amount in transaction {index} must be a finite non-negative number"
        ) from error
    if not isfinite(amount) or amount < 0:
        raise ValueError(f"amount in transaction {index} must be a finite non-negative number")
    return amount


def _ratio(numerator: float, denominator: float) -> Optional[float]:
    if denominator == 0:
        return None
    ratio = numerator / denominator
    if not isfinite(ratio):
        raise ValueError("inbound-to-outbound amount ratio is not finite")
    return ratio


def _sum(values: Iterable[float]) -> float:
    return fsum(sorted(values))


def _concentration(by_counterparty: dict[str, list[float]]) -> dict[str, Any]:
    ordered = {name: by_counterparty[name] for name in sorted(by_counterparty)}
    counterparty_transactions = {
        name: len(amounts) for name, amounts in ordered.items()
    }
    counterparty_amounts = {
        name: _sum(amounts) for name, amounts in ordered.items()
    }
    transaction_total = sum(counterparty_transactions.values())
    amount_total = _sum(counterparty_amounts.values())

    transaction_shares = {
        name: count / transaction_total
        for name, count in counterparty_transactions.items()
    } if transaction_total else {}
    amount_shares = {
        name: amount / amount_total if amount_total else None
        for name, amount in counterparty_amounts.items()
    }
    defined_amount_shares = [
        share for share in amount_shares.values() if share is not None
    ]

    return {
        "counterparty_count": len(ordered),
        "counterparty_transaction_count": transaction_total,
        "counterparty_amount_total": amount_total,
        "transaction_shares": transaction_shares,
        "amount_shares": amount_shares,
        "transaction_hhi": _sum(share * share for share in transaction_shares.values())
        if transaction_shares else None,
        "amount_hhi": _sum(share * share for share in defined_amount_shares)
        if defined_amount_shares else None,
        "dominant_transaction_share": max(transaction_shares.values(), default=None),
        "dominant_amount_share": max(defined_amount_shares, default=None),
    }


def build_account_analytics(
    transactions: Iterable[Mapping[str, Any]],
    account_id: str,
    cutoff_step: int,
    window_steps: Iterable[int] = DEFAULT_WINDOW_STEPS,
) -> dict[str, Any]:
    """Compute account analytics from transactions observed through ``cutoff_step``.

    Each row must contain ``step``, ``amount``, ``name_orig`` and ``name_dest``;
    the PaySim aliases ``nameOrig`` and ``nameDest`` are also accepted.
    Future rows are ignored after validating only their step.
    """
    account_id = _account(account_id, "account_id")
    cutoff_step = _step(cutoff_step, "cutoff_step")
    if isinstance(window_steps, (str, bytes)) or not isinstance(window_steps, Iterable):
        raise ValueError("window_steps must be an iterable of positive integers")
    windows = tuple(_step(window, "window size") for window in window_steps)
    if any(window == 0 for window in windows):
        raise ValueError("window sizes must be positive integers")
    if len(set(windows)) != len(windows):
        raise ValueError("window sizes must be unique")
    windows = tuple(sorted(windows))

    observed: list[tuple[int, float, str, str]] = []
    for index, row in enumerate(transactions):
        if not isinstance(row, Mapping):
            raise ValueError(f"transaction {index} must be a mapping")
        step = _step(_field(row, ("step",), index), f"step in transaction {index}")
        if step > cutoff_step:
            continue
        origin = _account(
            _field(row, ("name_orig", "nameOrig"), index),
            "name_orig",
            index,
        )
        destination = _account(
            _field(row, ("name_dest", "nameDest"), index),
            "name_dest",
            index,
        )
        amount = _amount(_field(row, ("amount",), index), index)
        if origin == account_id or destination == account_id:
            observed.append((step, amount, origin, destination))

    inbound: list[tuple[int, float, str]] = []
    outbound: list[tuple[int, float, str]] = []
    for step, amount, origin, destination in observed:
        if origin == account_id:
            outbound.append((step, amount, destination))
        if destination == account_id:
            inbound.append((step, amount, origin))

    inbound_amount = _sum(amount for _, amount, _ in inbound)
    outbound_amount = _sum(amount for _, amount, _ in outbound)
    turnover = _sum(amount for _, amount, _, _ in observed)
    activity_steps = sorted({step for step, _, _, _ in observed})
    gaps = [
        later - earlier
        for earlier, later in zip(activity_steps, activity_steps[1:])
    ]

    inbound_counterparties: dict[str, list[float]] = defaultdict(list)
    outbound_counterparties: dict[str, list[float]] = defaultdict(list)
    for _, amount, counterparty in inbound:
        if counterparty != account_id:
            inbound_counterparties[counterparty].append(amount)
    for _, amount, counterparty in outbound:
        if counterparty != account_id:
            outbound_counterparties[counterparty].append(amount)

    trailing_windows: dict[str, dict[str, Any]] = {}
    for window in windows:
        start_exclusive = cutoff_step - window
        in_window = [
            transaction for transaction in observed
            if start_exclusive < transaction[0] <= cutoff_step
        ]
        in_window_inbound = [
            transaction for transaction in inbound
            if start_exclusive < transaction[0] <= cutoff_step
        ]
        in_window_outbound = [
            transaction for transaction in outbound
            if start_exclusive < transaction[0] <= cutoff_step
        ]
        trailing_windows[str(window)] = {
            "window_size_steps": window,
            "start_step_exclusive": start_exclusive,
            "end_step_inclusive": cutoff_step,
            "transaction_count": len(in_window),
            "amount_total": _sum(row[1] for row in in_window),
            "inbound_transaction_count": len(in_window_inbound),
            "inbound_amount_total": _sum(row[1] for row in in_window_inbound),
            "outbound_transaction_count": len(in_window_outbound),
            "outbound_amount_total": _sum(row[1] for row in in_window_outbound),
        }

    return {
        "account_id": account_id,
        "cutoff_step": cutoff_step,
        "window_sizes_steps": list(windows),
        "inbound_transaction_count": len(inbound),
        "outbound_transaction_count": len(outbound),
        "inbound_amount_total": inbound_amount,
        "outbound_amount_total": outbound_amount,
        "average_transaction_amount": turnover / len(observed) if observed else None,
        "inbound_to_outbound_amount_ratio": _ratio(inbound_amount, outbound_amount),
        "total_turnover": turnover,
        "first_activity_step": activity_steps[0] if activity_steps else None,
        "last_activity_step": activity_steps[-1] if activity_steps else None,
        "activity_span_steps": (
            activity_steps[-1] - activity_steps[0] if activity_steps else None
        ),
        "distinct_activity_step_gap_count": len(gaps),
        "mean_distinct_activity_step_gap": _sum(gaps) / len(gaps) if gaps else None,
        "max_distinct_activity_step_gap": max(gaps, default=None),
        "trailing_windows": trailing_windows,
        "inbound_counterparty_concentration": _concentration(inbound_counterparties),
        "outbound_counterparty_concentration": _concentration(outbound_counterparties),
    }
