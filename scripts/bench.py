"""Benchmark harness for SRS §25.1 (AT-OPS-05).

Measures p95 latency per §25.1 operation against a running backend with warm caches and one concurrent user,
then writes docs/benchmark.json (read by tests/perf/test_AT_OPS_05_latency.py) and docs/benchmark.md.

Usage (from backend/, the stack running with a dataset active):
    MULENETX_BENCH_USERNAME=... MULENETX_BENCH_PASSWORD=... uv run python ../scripts/bench.py \
        [--base-url http://127.0.0.1:8000] [--samples 60] [--reference-slice]

`--reference-slice` asserts that the active dataset is the §7.1.2 PaySim reference slice; without it the
results are recorded as a non-reference run. The host specification is recorded as found; a miss on smaller
hardware is reported, never hidden (PLAN T29).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]

# operation → p95 target in milliseconds (SRS §25.1)
TARGETS_MS: dict[str, float] = {
    "account_lookup": 500,
    "risk_retrieval": 750,
    "neighborhood_2hop": 1500,
    "transaction_page": 750,
    "case_retrieval": 500,
    "health": 250,
    "readiness": 250,
    "path_query": 5000,
}
LABELS = {
    "account_lookup": "Account lookup",
    "risk_retrieval": "Risk retrieval",
    "neighborhood_2hop": "Bounded 2-hop neighborhood (default limits)",
    "transaction_page": "Simple transaction query (one page)",
    "case_retrieval": "Case retrieval",
    "health": "Health",
    "readiness": "Readiness",
    "path_query": "Interactive path query",
}


def p95(values: list[float]) -> float:
    """Nearest-rank 95th percentile."""
    ordered = sorted(values)
    rank = max(1, -(-95 * len(ordered) // 100))
    return ordered[rank - 1]


def host_spec() -> dict[str, Any]:
    spec: dict[str, Any] = {"platform": platform.platform(), "cpu_count": os.cpu_count(), "python": sys.version.split()[0]}
    try:
        if sys.platform == "darwin":
            spec["memory_bytes"] = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True))
        else:
            with open("/proc/meminfo") as f:
                spec["memory_bytes"] = int(f.readline().split()[1]) * 1024
    except (OSError, subprocess.SubprocessError, ValueError):
        spec["memory_bytes"] = None
    try:
        info = json.loads(subprocess.check_output(["docker", "info", "--format", "{{json .}}"], text=True, timeout=20))
        spec["docker_vm_cpus"] = info.get("NCPU")
        spec["docker_vm_memory_bytes"] = info.get("MemTotal")
    except (OSError, subprocess.SubprocessError, ValueError):
        spec["docker_vm_cpus"] = spec["docker_vm_memory_bytes"] = None
    gib = 1024**3
    spec["reference_hardware"] = bool(
        (spec.get("cpu_count") or 0) >= 8 and (spec.get("memory_bytes") or 0) >= 31 * gib
    )
    return spec


class Bench:
    def __init__(self, base: str, username: str, password: str) -> None:
        self.http = httpx.Client(base_url=base, timeout=30)
        resp = self.http.post("/api/v1/auth/login", json={"username": username, "password": password})
        resp.raise_for_status()
        self.http.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"

    def get(self, url: str, **params: Any) -> httpx.Response:
        return self.http.get(url, params=params or None)

    def measure(self, calls: list[Callable[[], httpx.Response]], samples: int) -> dict[str, Any]:
        for call in calls:  # warm the caches for every target
            call()
        timings: list[float] = []
        errors = 0
        for i in range(samples):
            call = calls[i % len(calls)]
            start = time.perf_counter()
            resp = call()
            timings.append((time.perf_counter() - start) * 1000)
            if resp.status_code >= 400:
                errors += 1
        return {
            "samples": samples,
            "errors": errors,
            "p50_ms": round(statistics.median(timings), 1),
            "p95_ms": round(p95(timings), 1),
            "max_ms": round(max(timings), 1),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("MULENETX_BENCH_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--samples", type=int, default=60)
    parser.add_argument("--reference-slice", action="store_true")
    parser.add_argument("--out", default=str(ROOT / "docs"))
    args = parser.parse_args()
    username = os.environ.get("MULENETX_BENCH_USERNAME")
    password = os.environ.get("MULENETX_BENCH_PASSWORD")
    if not username or not password:
        print("set MULENETX_BENCH_USERNAME and MULENETX_BENCH_PASSWORD", file=sys.stderr)
        return 2
    b = Bench(args.base_url, username, password)
    ctx = b.get("/api/v1/context").json()
    if not ctx["is_active"]:
        print("no active dataset: run the pipeline to READY first", file=sys.stderr)
        return 2
    accounts = [a["account_id"] for a in b.get("/api/v1/accounts", sort="risk_score", order="desc", page_size=20).json()["items"]]
    runs = b.get("/api/v1/pipeline-runs", dataset_id=ctx["dataset_id"], state="READY").json()["items"]
    run = b.get(f"/api/v1/pipeline-runs/{runs[0]['pipeline_run_id']}").json() if runs else {}
    pairs: list[tuple[str, str]] = []
    for acc in accounts:
        nb = b.get("/api/v1/graph/neighborhood", account_id=acc, depth=2).json()
        two = [n["account_id"] for n in nb.get("nodes", []) if n["hop"] == 2]
        one = [n["account_id"] for n in nb.get("nodes", []) if n["hop"] == 1]
        if two or one:
            pairs.append((acc, (two or one)[0]))
    cases = b.get("/api/v1/cases").json()["items"]
    if not cases:
        created = b.http.post("/api/v1/cases", json={"title": "Benchmark probe", "priority": "LOW"})
        created.raise_for_status()
        cases = [created.json()]
    case_ids = [c["case_id"] for c in cases[:10]]

    def each(fn: Callable[[str], httpx.Response], items: list[str]) -> list[Callable[[], httpx.Response]]:
        return [lambda item=item: fn(item) for item in items]

    ops: dict[str, list[Callable[[], httpx.Response]]] = {
        "account_lookup": each(lambda a: b.get(f"/api/v1/accounts/{a}"), accounts),
        "risk_retrieval": each(lambda a: b.get(f"/api/v1/accounts/{a}/risk"), accounts),
        "neighborhood_2hop": each(lambda a: b.get("/api/v1/graph/neighborhood", account_id=a, depth=2), accounts),
        "transaction_page": each(lambda a: b.get(f"/api/v1/accounts/{a}/transactions"), accounts),
        "case_retrieval": each(lambda c: b.get(f"/api/v1/cases/{c}"), case_ids),
        "health": [lambda: b.get("/health")],
        "readiness": [lambda: b.get("/ready")],
        "path_query": [
            lambda s=s, d=d: b.get("/api/v1/graph/path", source_account_id=s, destination_account_id=d) for s, d in pairs
        ],
    }
    results = {name: {**b.measure(calls, args.samples), "target_ms": TARGETS_MS[name]} for name, calls in ops.items() if calls}
    for r in results.values():
        r["met"] = r["p95_ms"] <= r["target_ms"] and r["errors"] == 0
    metrics = run.get("metrics", {})
    report = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "host": host_spec(),
        "dataset": {
            "dataset_id": ctx["dataset_id"],
            "reference_slice": args.reference_slice,
            "records_accepted": metrics.get("records_accepted"),
            "graph_nodes": metrics.get("graph_nodes"),
            "graph_edges": metrics.get("graph_edges"),
        },
        "pipeline_durations_s": {k: v for k, v in metrics.items() if k.endswith("_duration")},
        "results": results,
    }
    out = Path(args.out)
    (out / "benchmark.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (out / "benchmark.md").write_text(render(report), encoding="utf-8")
    print(json.dumps({k: (v["p95_ms"], v["met"]) for k, v in results.items()}))
    return 0


def render(r: dict[str, Any]) -> str:
    h = r["host"]
    gib = 1024**3
    mem = f"{h['memory_bytes'] / gib:.0f} GiB" if h.get("memory_bytes") else "unknown"
    vm = f"{h['docker_vm_memory_bytes'] / gib:.1f} GiB" if h.get("docker_vm_memory_bytes") else "unknown"
    d = r["dataset"]
    lines = [
        "# Benchmark (SRS §25.1, AT-OPS-05)",
        "",
        f"Generated {r['generated_at']} by `scripts/bench.py` (warm caches, one concurrent user, nearest-rank p95).",
        "",
        "## Environment",
        "",
        f"- Host: {h['platform']}, {h['cpu_count']} vCPU, {mem} RAM; Docker VM {h.get('docker_vm_cpus')} CPU / {vm}.",
        f"- Reference hardware (§25.1: 8 vCPU, 32 GiB): **{'yes' if h['reference_hardware'] else 'no'}**.",
        f"- Dataset `{d['dataset_id']}`: {d['records_accepted']} transactions, {d['graph_nodes']} accounts, "
        f"{d['graph_edges']} aggregated edges. Reference slice (§7.1.2): **{'yes' if d['reference_slice'] else 'no'}**.",
        "",
        "## Latency",
        "",
        "| Operation | Target p95 | p50 | p95 | max | errors | Met |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, v in r["results"].items():
        lines.append(
            f"| {LABELS[name]} | {v['target_ms']:.0f} ms | {v['p50_ms']} ms | {v['p95_ms']} ms | {v['max_ms']} ms | "
            f"{v['errors']} | {'yes' if v['met'] else '**no**'} |"
        )
    lines += ["", "## Pipeline durations (recorded, no target)", ""]
    for k, v in sorted(r["pipeline_durations_s"].items()):
        lines.append(f"- {k}: {v} s")
    verdict = all(v["met"] for v in r["results"].values()) and h["reference_hardware"] and d["reference_slice"]
    lines += [
        "",
        "## AT-OPS-05",
        "",
        "**Pass**" if verdict else "**Not passed**: AT-OPS-05 requires the reference environment and the reference slice; "
        "see `docs/OPEN_QUESTIONS.md` (OQ-03, OQ-72) for the documented exception request.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
