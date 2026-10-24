# Phase 4 — Rings and motifs (T30–T35)

**Gate status: PASSED** (2026-10-18). AT-MOTIF-01..05, AT-RING-01..05 and AT-FLOW-04 pass. Phase 3's gate remains open on AT-OPS-05 (OQ-72); Phase 4 does not depend on it.

## Tasks completed

| Task | Commit | Summary |
|---|---|---|
| T30 | `ee4e5ef` | `flow/vocabulary.py`: the only definitions of suspicious account and suspicious transaction. It takes final scores and the versioned threshold, and it never reads a label. `flow/analytic_paths.py`: ring scope, eligible and in-scope qualifying paths, flows, suspicious account set and reachable pairs, all under deterministic counters. AT-FLOW-04 runs on the `truncation` fixture. |
| T31 | `630dcda` | Six motif detectors of §15.9: rapid pass-through, fan-in/out with greedy segmentation, circular flow, layered movement, and burst against the 168-bucket baseline. Also exact confidence, maximality, the per-anchor budget and `order_ambiguous`. Motifs are persisted in the ANALYTICS transaction. Adds `GET /accounts/{id}/motifs`, and AT-OPS-04 now compares motif IDs across reruns. |
| T32 | `e0b1a17` | Community signals H, D, C, community_temporal_density and M; the candidate score and class; candidates persisted in the RING_ANALYSIS final transaction alongside activation. |
| T33 | `312d0cc` | Ring membership and constituent transactions; RSD, RC, TC, MFC (top-3), CS, FI, FO, CP and SPD with availability and truncation state; ring risk with components and tier; an evidence builder. |
| T34 | `a132975` | All ring endpoints: list, detail, members, transactions, features, risk, evidence and motifs. `PATCH /rings/{id}/status` follows §9.4 and is audited. The `/fraud-ring-candidates` aliases are in place, and SUSPICIOUS_COMMUNITY rings return `409 RING_INTELLIGENCE_NOT_APPLICABLE`. |
| T35 | `d0692be` | Dashboard: rings list, ring workspace and motif panel (confidence components, `order_ambiguous`), plus an account Motifs tab. The wording is analytical throughout, as §9.5 and §9A.6 require. |

## Key files and decisions

- Fixtures: `backend/tests/fixtures/truncation/`, `fixtures/motifs/*.json` (10 cases) and `fixtures/ring_basic/expected.json`. Every expected value was computed by hand from the SRS formulas, and the working is recorded in each JSON.
  - `ring_basic` covers the candidate score 0.7369318 (POTENTIAL_FRAUD_RING_CANDIDATE) and the features RSD 0.8, RC 0.8214286, TC 0.6, MFC 0.875, CS 0.45, CP 1 and SPD 0.5 (9 of 18 paths).
  - It also covers ring risk 0.5780000 (HIGH).
  - The implementation matched every one of these values on its first run.
- Motif reruns: `motif_id` is the table key and is deterministic per snapshot and version. Rows are therefore inserted with `ON CONFLICT DO NOTHING` and read back by `(graph_snapshot_id, analytics_version)` (OQ-75).
- Ring evidence (§9A.4) is rebuilt on read with the same deterministic enumeration, because paths are not persisted (OQ-78, OQ-79).
- The ring screens extend the established visual world (`DESIGN.md`) and introduce no new direction.
  - The detector run returned `[]`.
  - One capture round at 1440 and 390 px was checked against live data: `.impeccable/review/t35/`, which is not committed.

## Commands run and results (last run)

```
cd backend
uv run ruff check . && uv run mypy mulenetx           # clean; 181 source files
uv run pytest tests -m "not docker and not perf"      # 456 passed
uv run pytest tests -k "MOTIF or RING_0 or FLOW_04"   # 32 passed (Phase 4 gate set)
cd ../frontend
npm run lint                                          # clean
npm test                                              # 46 passed (10 files)
```

## Gate

| AT | Result |
|---|---|
| AT-FLOW-04 | pass. The run is truncated at 50 paths, identical under CPU load, complete at 10,000, and gives disruption 0.5000000 when X is removed. |
| AT-MOTIF-01 | pass. Pass-through: one maximal sequence with confidence 0.8333333, plus the equal-timestamp and parallel cases. |
| AT-MOTIF-02 | pass. Fan-in 0.8888889; fan-out with an inclusive window, 0.6666667; greedy segmentation produces 2 instances. |
| AT-MOTIF-03 | pass. Cycle confidence 0.9722222, with no criminality wording in the evidence. |
| AT-MOTIF-04 | pass. Layered 0.9583333; burst against a 168-bucket baseline, 1.0000000. |
| AT-MOTIF-05 | pass. Nothing just outside any window, and no merge across segments. |
| AT-RING-01..04 | pass, exact on `ring_basic`. Persistence is idempotent on Postgres. |
| AT-RING-05 | pass. ANALYST gets 403 (audited); INVESTIGATOR gets 200 (audited); transitions follow §9.4. |

## Known bugs / limitations

- On the synthetic dataset, ring-scope enumeration for some rings reaches `analytic_max_paths` (10,000), because merchant hubs multiply the eligible paths. When that happens, MFC, SPD and the money-flow signal are marked `LOWER_BOUND_TRUNCATED`, as §9A.2 specifies.
- Ring evidence recomputes the ring scope on each request. The cache holds the last two contexts; the first request for a large scope can be slow, and nothing has been benchmarked on the reference slice (OQ-72).
- Intervention and evaluation endpoints are still in `NOT_YET` (Phase 5).

## Open questions / defaults introduced

OQ-74 … OQ-79 are all `default`. The open items for Partha are unchanged: OQ-03, OQ-14, OQ-15, OQ-56, OQ-67 and OQ-72.

## Next steps (Phase 5, T36–T39)

1. T36–T37: network intervention analysis (SRS §16A): RANK/EVALUATE scenarios as jobs, residual paths, disruption, candidates, and the intervention APIs (AT-INT-*).
2. T38: evaluation runs (SRS §28) and the evaluation APIs, plus aliases (AT-EVAL-*).
3. T39: the intervention and evaluation UI, always labelled Hypothetical Simulation.
