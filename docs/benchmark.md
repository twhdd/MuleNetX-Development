# Benchmark (SRS §25.1, AT-OPS-05)

Generated 2026-10-18T04:05:16Z by `scripts/bench.py` (warm caches, one concurrent user, nearest-rank p95).

## Environment

- Host: macOS-26.2-arm64-arm-64bit, 8 vCPU, 8 GiB RAM; Docker VM 8 CPU / 3.8 GiB.
- Reference hardware (§25.1: 8 vCPU, 32 GiB): **no**.
- Dataset `2c5e127a-f87e-47ad-83c6-864da150a38e`: 48317 transactions, 51457 accounts, 41114 aggregated edges. Reference slice (§7.1.2): **no**.

## Latency

| Operation | Target p95 | p50 | p95 | max | errors | Met |
|---|---|---|---|---|---|---|
| Account lookup | 500 ms | 3.2 ms | 3.5 ms | 6.9 ms | 0 | yes |
| Risk retrieval | 750 ms | 4.7 ms | 8.3 ms | 13.5 ms | 0 | yes |
| Bounded 2-hop neighborhood (default limits) | 1500 ms | 81.7 ms | 121.8 ms | 198.7 ms | 0 | yes |
| Simple transaction query (one page) | 750 ms | 4.2 ms | 5.1 ms | 13.6 ms | 0 | yes |
| Case retrieval | 500 ms | 3.0 ms | 5.8 ms | 12.6 ms | 0 | yes |
| Health | 250 ms | 1.2 ms | 1.7 ms | 2.3 ms | 0 | yes |
| Readiness | 250 ms | 6.0 ms | 10.5 ms | 23.3 ms | 0 | yes |
| Interactive path query | 5000 ms | 784.7 ms | 982.3 ms | 1041.2 ms | 0 | yes |

## Pipeline durations (recorded, no target)

- analytics_duration: 24.603 s
- feature_generation_duration: 1.872 s
- graph_build_duration: 17.44 s
- ingestion_duration: 0.605 s
- profiling_duration: 0.869 s
- ring_analysis_duration: 0.014 s
- scoring_duration: 4.337 s
- training_duration: 78.883 s

## AT-OPS-05

**Not passed**: AT-OPS-05 requires the reference environment and the reference slice; see `docs/OPEN_QUESTIONS.md` (OQ-03, OQ-72) for the documented exception request.
