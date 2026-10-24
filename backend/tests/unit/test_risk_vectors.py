"""SRS §27.5 risk test vectors, tier boundaries at ±1e-7, rule regime, and the 0 ≤ final ≤ 0.95 property."""

import math
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mulenetx.risk.compose import Components, compose
from mulenetx.risk.rules import evaluate
from mulenetx.risk.tiers import tier
from tests.ingestutil import expected
from tests.riskutil import RULES, THRESHOLDS, WEIGHTS, components

VECTORS = expected("risk_vectors")


@pytest.mark.parametrize("vector", VECTORS["vectors"], ids=[str(v["id"]) for v in VECTORS["vectors"]])
def test_vector(vector) -> None:
    c = components(vector)
    result = compose(c, Decimal(vector["propagated"]), WEIGHTS, THRESHOLDS)
    exp = vector["expected"]
    assert format(result.pre_propagation_score, "f") == exp["pre"]
    assert format(result.final_score, "f") == exp["final"]
    assert result.risk_tier == exp["tier"]
    assert format(result.signal_coverage, "f") == exp["coverage"]
    assert format(result.max_attainable_score, "f") == exp["max_attainable"]
    if "rule_inputs" in vector:
        inputs = vector["rule_inputs"]
        values = {k: (math.nan if v[0] is None else v[0]) for k, v in inputs.items() if k.startswith("F")}
        states = {k: v[1] for k, v in inputs.items() if k.startswith("F")}
        rr = evaluate(RULES, values, states, {"outgoing_amount_24h": inputs["outgoing_amount_24h"]})
        assert [f["rule_id"] for f in rr.fired] == exp["fired"]
        assert rr.score == Decimal(vector["rules"])


@pytest.mark.parametrize(("score", "want"), VECTORS["tier_boundaries"])
def test_tier_boundaries(score: str, want: str) -> None:
    assert tier(Decimal(score), THRESHOLDS) == want


def test_rounding_happens_before_tiering() -> None:
    rb = VECTORS["rounding_boundary"]
    c = Components(Decimal(rb["ml"]), Decimal(0), True, Decimal(0), True, Decimal(0))
    result = compose(c, Decimal(0), WEIGHTS, THRESHOLDS)
    assert format(result.final_score, "f") == rb["final"] and result.risk_tier == rb["tier"]


def test_unavailable_rule_input_never_fires() -> None:
    values = {"F28": 0.95, "F25": 0.9, "F21": 50.0, "F36": math.nan, "F37": math.nan, "F31": math.nan}
    states = {"F28": 0, "F25": 0, "F21": 0, "F36": 2, "F37": 2, "F31": 2}
    rr = evaluate(RULES, values, states, {"outgoing_amount_24h": None})  # R01's quantity unavailable
    assert [f["rule_id"] for f in rr.fired] == ["R02"]


unit = st.decimals(min_value=0, max_value=1, places=7, allow_nan=False, allow_infinity=False)
half = st.decimals(min_value=0, max_value=Decimal("0.5"), places=7, allow_nan=False, allow_infinity=False)


@given(ml=st.one_of(st.none(), unit), g=unit, b=unit, r=unit, p=half, ga=st.booleans(), ba=st.booleans())
def test_property_final_in_bounds(ml, g, b, r, p, ga, ba) -> None:  # type: ignore[no-untyped-def]
    c = Components(ml, g if ga else Decimal(0), ga, b if ba else Decimal(0), ba, r)
    result = compose(c, p, WEIGHTS, THRESHOLDS)
    assert Decimal(0) <= result.final_score <= Decimal("0.95")
    assert result.final_score <= result.max_attainable_score <= Decimal("0.95")
    assert result.final_score == result.final_score.quantize(Decimal("0.0000001"))
