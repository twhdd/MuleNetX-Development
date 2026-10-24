"""AT-INT-09: the network-risk counterexample. Removing D reduces network risk by 1.0 and ranks first; removing A
reduces it by 0.4390244 under the normative §16A.12 formula (OQ-80: the SRS fixture's 0.40 counted D, which is
not suspicious)."""

from decimal import Decimal

from tests.interventionutil import counterexample, counterexample_baseline, label, rank

FX = counterexample()


def test_AT_INT_09_baseline() -> None:
    b = counterexample_baseline()
    assert [list(p.accounts) for p in b.paths] == FX["baseline"]["paths"]
    assert b.suspicious_flow == Decimal(FX["baseline"]["flow"])
    assert len(b.pairs) == FX["baseline"]["pairs"]
    assert b.risk_mass == Decimal(FX["baseline"]["risk_mass"])


def test_AT_INT_09_values_and_order() -> None:
    results = {label(r): r for r in rank(counterexample_baseline())}
    for name, expected in FX["candidates"].items():
        r = results[name]
        for metric, value in expected.items():
            actual = r.intervention_score if metric == "intervention_score" else getattr(r.metrics, metric)
            assert format(actual, "f") == value, (name, metric)
    assert results["INTERMEDIARY_REMOVAL D"].metrics.normalized_risk_reduction == Decimal("1.0000000")
    assert results["ACCOUNT_REMOVAL A"].metrics.normalized_risk_reduction == Decimal("0.4390244")
    assert results["INTERMEDIARY_REMOVAL D"].rank_position < results["ACCOUNT_REMOVAL A"].rank_position
    ordered = [label(r) for r in sorted(results.values(), key=lambda r: r.rank_position)]
    position = 0
    for group in FX["rank_groups"]:
        assert set(ordered[position : position + len(group)]) == set(group), (position, group)
        position += len(group)
