# Phase 3: Investigation (T22–T29)

**Gate status: NOT PASSED.** It is blocked on AT-OPS-05 and needs a decision from Partha (OQ-72).

- Every other Phase 3 acceptance test passes: AT-FLOW-01..03, AT-INV-01..06, AT-API-01..02 and AT-OPS-02.
- AT-OPS-05 needs the §25.1 reference environment and the §7.1.2 PaySim reference slice. This host is 8 vCPU / 8 GiB, and the PaySim file is not available.
- On a 48,317-row synthetic PaySim-format dataset run through the real Compose stack, every §25.1 latency target was met with wide margin. That run is not the reference, and the AT-OPS-05 test reports it as such.
- Following the owner's instruction to build without stopping, work continues with Phase 4. The gate stays open until Partha supplies the data and hardware or approves the documented exception.

## Tasks completed

| Task | Commit | Summary |
|---|---|---|
| T22 | `c2b6fec` | `/graph/path` (SHORTEST/ALL, depth ≤ 5, results ≤ 50, 5 s timeout), path evidence by `path_id` (OQ-60), `/money-flow` alias, and the §16.9 connectivity statement. |
| T23 | `2b0460c` | Cases with the §17.2 state machine, optimistic concurrency (`CASE_VERSION_CONFLICT`), the §22.2 field and transition rules (analyst participant rules), soft-removed subjects, and findings with validated evidence references. |
| T24 | `2345d93` | `GET /audit`; Pydantic response models on every route (extra fields forbidden); `make openapi` exports `docs/openapi.json` with `x-permission` and the error envelope; an inventory test against the SRS §19.2 matrix (`NOT_YET` for later phases); the AT-SEC-02 xfail removed; AT-API-01/02. |
| T25 | `f0e5d59` | Frontend foundation: Vite + React 18 + TS. API client layer (the only HTTP; the token is held in memory only, both enforced by ESLint). Zustand stores, the §20.4 state views, the §20.5 evidence labels, the lineage badge, the shell with the active-context banner and mobile navigation, and login. `/context` gains `is_synthetic_injection`. |
| T26 | `f7cf815` | Account search; account workspace with risk decomposition (components, coverage, rules, SHAP labelled as covering the ML component only), propagation provenance, history, transactions with a day×hour activity heatmap, features, temporal and community tabs. |
| T27 | `add423c` | D3 graph explorer (deterministic hop-ring layout, flow-matrix heatmap view), money-flow path view, communities, and the Triage screen (signal-matrix heatmap, live graph, score decomposition). |
| T28 | `3aa888d`, `b0d2841` | Cases list and detail (role-aware transitions, 409 reload prompt, subjects, findings); admin ingestion, pipelines (progress read from `/pipeline-runs/{id}`), dataset profile, models, users, audit. Design record in `DESIGN.md` and `.impeccable/design.json`. |
| T29 | `8970c3d` | `scripts/bench.py` (`make bench`) writes `docs/benchmark.{json,md}`; `tests/perf/test_AT_OPS_05_latency.py`; AT-OPS-02 runs in-process and against Compose; two degraded-mode defects fixed (listed below). |

## Key files and decisions

**Frontend design (the owner's request: "utilize impeccable…, MULENETX_REDESIGNED as inspiration").**
- The template's world was kept and improved: black ground, serif italic entity names, mono data, and the risk ramp.
- Its illegible 7–9 px type, failing contrast, glyph icons and mock geography were replaced.
- PaySim has no geography, so the India heatmap became three real-data heatmaps (OQ-68):
  - the Triage signal matrix, built from score components;
  - the account day×hour activity heatmap;
  - the explorer flow matrix, an adjacency heatmap.
- No questions were asked of the owner (OQ-67), and every inferred product fact is labelled in `PRODUCT.md`.
- The direction contract is in `.impeccable/surfaces/frontend-src-app-tsx.md`.

**Impeccable finish review.** A fresh reviewer agent ran two fix rounds.
- Round 1 returned 8 material fixes: ramp-only colour, graph rings and legibility, mobile context, mobile nav, the flow-matrix key, the duplicate header, the truncation chip, and the SYNTHETIC DATA label.
- The final verdict scored all 8, plus two regressions from round 1, as resolved, and raised one new item: triage graph labels had shrunk with the zoom.
- That item was fixed after the last verdict (labels are counter-scaled to about 12 px on screen) and checked by me on a recapture. The reviewer did not re-score it, because the unattended two-round budget was spent.
- The detector run returned `[]`.

**Backend.**
- Response read models: `backend/mulenetx/api/schemas/responses.py`.
- OpenAPI annotation and export: `backend/mulenetx/openapi.py`. The app serves no `/openapi.json` (OQ-64).

## Defects found and fixed in this phase

1. **A stopped Neo4j container made `/ready` return 500** (found by AT-OPS-02 on Compose). The Neo4j driver raises `ValueError("Cannot resolve address neo4j:7687")` when the host name has no DNS entry.
   - That error now maps to neo4j DOWN, and to `503 GRAPH_UNAVAILABLE` on the graph endpoints.
   - Any other `ValueError` still propagates (`tests/unit/test_neo4j_unreachable.py`).
2. **The dashboard nginx returned 502 after the backend container was recreated.** nginx had resolved `backend` once at startup. It now re-resolves through Docker DNS (`resolver 127.0.0.11`, variable `proxy_pass`). This was verified by recreating the backend twice.
3. **Browsers label CSV uploads inconsistently.** The client now always sends the file part as `text/csv` (OQ-73, `frontend/tests/upload.test.ts`).

## Commands run and results (last run)

```
cd backend
uv run ruff check .                                   # All checks passed!
uv run mypy mulenetx                                  # Success: no issues found in 162 source files
uv run pytest tests -m "not docker and not perf"      # 406 passed
uv run pytest tests/acceptance/test_AT_OPS_01_clean_startup.py tests/acceptance/test_AT_OPS_02_neo4j_down.py -m docker
                                                      # 2 passed (real Compose stack; dashboard built from the Vite app)
uv run python ../scripts/bench.py --samples 60        # against Compose, synthetic 48,317-row dataset; see docs/benchmark.md
uv run pytest tests/perf -m perf                      # 2 passed, 1 failed: test_AT_OPS_05_reference_environment (non-reference host and dataset)
cd ../frontend
npm run lint                                          # eslint + tsc clean
npm test                                              # 40 passed (9 files)
npm run build                                         # built
```

Each frontend task commit (T25–T28) was checked out on its own and passed `tsc` and Vitest: 19, 25, 33 and 39 tests respectively.

End-to-end through Compose:
- A CSV uploaded through the dashboard proxy (`:8080/api/v1/ingestion`) reached READY in about 2.3 minutes. The pipeline durations are in `docs/benchmark.md`.
- Login through the dashboard proxy returned 200, and a deep link served `index.html`.

## Gate

| AT | Result |
|---|---|
| AT-FLOW-01..03 | pass |
| AT-INV-01..06 | pass |
| AT-API-01 | pass. Every implemented endpoint and alias returns its SRS status and a body that validates against its OpenAPI schema. |
| AT-API-02 | pass. `400 LIMIT_EXCEEDED` for every limit; `413` for every body limit. |
| AT-OPS-02 | pass, in-process and on Compose. |
| AT-OPS-05 | **not passed**. Latencies were met on non-reference hardware with a non-reference dataset (p95 values: account 3.5 ms, risk 8.3 ms, 2-hop neighbourhood 121.8 ms, transactions 5.1 ms, case 5.8 ms, health 1.7 ms, ready 10.5 ms, path 982 ms). The reference precondition fails (OQ-03, OQ-72). |

## Known bugs / limitations

- The reference-slice pipeline cost has never been measured. Exact betweenness is O(V·E) per component, and PaySim's component structure at 1M rows has not been observed (OQ-72).
- Mobile graph hover tooltips are mouse-only by design; touch users tap to select.
- SYNTHETIC DATA is shown in the banner only. Synthetic injection itself is not implemented (OQ-71).
- The dashboard has no Playwright E2E suite yet; that is T44 (golden path).

## Open questions / defaults introduced

OQ-61 … OQ-73. Items open for Partha:
- OQ-03 (hardware)
- OQ-14 (model size)
- OQ-15 (password policy)
- OQ-56 (propagation performance)
- OQ-67 (design was not confirmed with the owner)
- OQ-72 (AT-OPS-05 exception, PaySim file)

## Next steps (Phase 4, T30–T35)

1. T30: the suspicious-flow vocabulary and analytical path enumeration (AT-FLOW-04).
2. T31: temporal motifs (AT-MOTIF-01..05).
3. T32–T35: candidate scoring, ring intelligence, ring APIs and the ring UI.
4. Shrink `NOT_YET` in `tests/api/test_inventory.py` as the motif and ring endpoints land.
