"""AT-OPS-05: every §25.1 latency target is met by the benchmark harness on the reference environment with the
reference slice active. Reads docs/benchmark.json written by scripts/bench.py (`make bench`); not part of the
default test run. A run on smaller hardware or another dataset is reported as not passing, never hidden."""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.perf

REPORT = Path(__file__).resolve().parents[3] / "docs" / "benchmark.json"
OPERATIONS = {
    "account_lookup",
    "risk_retrieval",
    "neighborhood_2hop",
    "transaction_page",
    "case_retrieval",
    "health",
    "readiness",
    "path_query",
}


def _report() -> dict:
    assert REPORT.exists(), "run `make bench` first"
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_AT_OPS_05_every_operation_measured() -> None:
    results = _report()["results"]
    assert set(results) == OPERATIONS
    assert all(r["samples"] >= 30 and r["errors"] == 0 for r in results.values()), results


def test_AT_OPS_05_latency_targets_met() -> None:
    results = _report()["results"]
    missed = {k: (r["p95_ms"], r["target_ms"]) for k, r in results.items() if not r["met"]}
    assert not missed, f"p95 above target: {missed}"


def test_AT_OPS_05_reference_environment() -> None:
    report = _report()
    assert report["host"]["reference_hardware"], f"host is not the §25.1 reference: {report['host']}"
    assert report["dataset"]["reference_slice"], "the active dataset is not the §7.1.2 reference slice"
