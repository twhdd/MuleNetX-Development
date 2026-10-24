"""Component normalization (SRS §12.2–§12.3)."""

import math
from decimal import Decimal

import pytest

from mulenetx.risk.components import component, normalize, percentile_against_table


def test_percentile_against_table_interpolates_and_clamps() -> None:
    table = [float(i) for i in range(101)]  # quantile q at value q
    assert percentile_against_table(50.0, table) == 0.5
    assert percentile_against_table(50.5, table) == pytest.approx(0.505)
    assert percentile_against_table(-3.0, table) == 0.0
    assert percentile_against_table(500.0, table) == 1.0


def test_percentile_plateau_takes_middle() -> None:
    table = [0.0] * 51 + [1.0] * 50
    assert percentile_against_table(0.0, table) == 0.25  # indices 0..50 → middle 25 → 0.25


def test_x_over_x_plus_median() -> None:
    assert normalize("F21", 3.0, "x_over_x_plus_median", {"median_positive": 1.0}, None) == 0.75
    assert normalize("F21", 3.0, "x_over_x_plus_median", {"median_positive": None}, None) == 0.0


def test_log1p_reference_and_missing_table() -> None:
    table = [math.log1p(i) for i in range(101)]
    assert normalize("F11", 50.0, "log1p_percentile_reference", {"quantiles_log1p": table}, None) == pytest.approx(0.5)
    assert normalize("F11", 1.0, "log1p_percentile_reference", {}, None) is None


def test_component_mean_excludes_unavailable() -> None:
    result = component(
        ["F20", "F25", "F28"],
        {"F20": 0.2, "F25": math.nan, "F28": 0.6},
        {"F20": 0, "F25": 2, "F28": 0},
        {"F20": "identity", "F25": "identity", "F28": "identity"},
        {},
    )
    assert result.available and result.score == Decimal("0.4000000")
    assert result.inputs["F25"] is None


def test_component_all_unavailable_is_zero_and_unavailable() -> None:
    result = component(["F11"], {"F11": math.nan}, {"F11": 2}, {"F11": "log1p_percentile_reference"}, {})
    assert (result.score, result.available) == (Decimal(0), False)
