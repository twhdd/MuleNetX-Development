"""AT-FLOW-04: analytical enumeration of the `truncation` fixture is truncated deterministically at
`analytic_max_paths = 50` and is identical under CPU load; with 10,000 it is complete (SRS §16.7.2)."""

import json
import threading
from decimal import Decimal

from mulenetx.flow.analytic_paths import Budget, enumerate_ring_scope
from tests.flowutil import context, projection_from_fixture
from tests.ingestutil import fixture_csv

EXPECTED = json.loads((fixture_csv("truncation").parent / "expected.json").read_text())


def _run(max_paths: int):  # type: ignore[no-untyped-def]
    proj = projection_from_fixture("truncation")
    scores = {a: "0.9000000" for a in EXPECTED["suspicious"]} | {a: "0.1000000" for a in EXPECTED["non_suspicious"]}
    return enumerate_ring_scope(proj, EXPECTED["ring_members"], context(scores), Budget(max_paths=max_paths))


def _burn(stop: threading.Event) -> None:
    x = 0
    while not stop.is_set():
        x = (x * 31 + 7) % 1_000_003


def test_AT_FLOW_04_truncated_deterministically() -> None:
    first = _run(50)
    assert first.truncated is True
    assert 0 < len(first.qualifying_paths) <= EXPECTED["bounded"]["qualifying_paths_at_most"]
    stop = threading.Event()
    burners = [threading.Thread(target=_burn, args=(stop,)) for _ in range(4)]
    for t in burners:
        t.start()
    try:
        under_load = [_run(50) for _ in range(3)]
    finally:
        stop.set()
        for t in burners:
            t.join()
    for r in under_load:
        assert r.truncated is True
        assert r.qualifying_paths == first.qualifying_paths
        assert r.eligible_paths == first.eligible_paths
        assert r.counters == first.counters


def test_AT_FLOW_04_complete_with_full_bound() -> None:
    full = _run(10_000)
    exp = EXPECTED["unbounded"]
    assert full.truncated is False
    assert len(full.qualifying_paths) == exp["qualifying_paths"]
    assert len(full.eligible_paths) == exp["eligible_paths"]
    through_x = [p for p in full.qualifying_paths if "X" in p]
    assert len(through_x) == exp["paths_through_X"]
    disruption = (Decimal(len(through_x)) / Decimal(len(full.qualifying_paths))).quantize(Decimal("0.0000001"))
    assert str(disruption) == exp["normalized_path_disruption_removing_X"]
    assert full.eligible_flow == Decimal(exp["eligible_flow"])
    assert full.suspicious_flow == Decimal(exp["suspicious_flow"])
