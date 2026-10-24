# Phase 5 — Interventions and evaluation (T36–T39)

**Gate status: PASSED** on 2026-10-18. AT-INT-01..10 and AT-EVAL-01..03 pass.

The Phase 3 gate is still open on AT-OPS-05 (OQ-72).

## Tasks completed

| Task | Commit | Summary |
|---|---|---|
| T36 | `1ade8f6` | Pure intervention engine (§16A), in steps: baseline of in-scope qualifying paths; RANK pool in the §16A.4.3 order with the 5,000 cap; EVALUATE validation with k_max = 3; residuals by filtering; metrics that apply the zero-denominator rules; the intervention score and five-key sort. |
| T37 | `58c6497` | INTERVENTION job and endpoints. Validation runs before a job is created. A submit returns 202 QUEUED and is limited per user (429). Results are served only once COMPLETED (otherwise 409), and every response is labelled hypothetical and carries the baseline truncation state. |
| T38 | `c4a1b45` | EVALUATION job over the model's test split, covering four levels: transaction (max endpoint score), account, ring (WCC reference rings with one-to-one Jaccard matching) and network. Also adds intervention effectiveness against a degree-ranked baseline, NOT_MEASURABLE metrics, lineage, the PaySim limitation, endpoints and aliases. |
| T39 | `3197e29` | Dashboard: a simulation page whose every result is labelled Hypothetical Simulation and which offers no control for a real action, plus an evaluation report showing the four-level progression with the limitation statement. |

## Key files and decisions

**Network-risk counterexample.**
- The fixture's hand-computed ranking was matched exactly: D 0.9666667; then A and edge A>D tied at 0.5689228, separated by candidate ID; then B 0.4198374; and so on.
- The SRS gives 0.40 for removing A. The normative formula gives 0.4390244, which is what the build uses. This is recorded as **OQ-80** and still needs an SRS correction from Partha.

**Purity and canonical state.**
- The engine is pure: AT-INT-07 checks that the intervention package imports no analytics, ML, SHAP, risk, graph or database code.
- AT-INT-01 compares canonical PostgreSQL and Neo4j state before and after a scenario, using row counts and digests.

**Evaluation scope.**
- Evaluation uses the active context. When the context reuses a model trained on another dataset (the model's T_test is before the snapshot cutoff), the run fails with an explicit message (OQ-83). This is the PLAN default.
- For AT-EVAL-02, a dense fraud cluster is injected into the test window (`tests/evalutil.py`). With it, a potential fraud ring is matched (Jaccard 1.0), and the rank-1 and degree-baseline effectiveness are both measured.

## Defects found and fixed in this phase

1. **Reading a FAILED evaluation run returned 500.** The query used a column that does not exist on `jobs`; it now reads `error_summary`.
   - Found by inspecting the UI against live data.
   - Regression test: `tests/api/test_evaluation_failure.py` drives a deterministic FAILED run.
2. **Wide tables widened the whole page on phones.** Every table now sits in a horizontal scroll wrapper, and flex children get `min-width: 0`.

## Commands run and results (last run)

```
cd backend
uv run ruff check . && uv run mypy mulenetx           # clean; 196 source files
uv run pytest tests -m "not docker and not perf"      # 486 passed
uv run pytest tests -k "INT_ or EVAL or intervention_checks or matching"   # all pass (gate set)
cd ../frontend
npm run lint && npm test && npm run build             # clean; 49 passed; built
impeccable detect --json frontend/src                 # []
```

Visual check: `.impeccable/review/t39/` captures of the simulation and evaluation pages at 1440 and 390 px against live data. These captures are not committed.

## Gate

| AT | Result |
|---|---|
| AT-INT-01 | pass. No canonical or graph mutation; only the two intervention tables gain rows. |
| AT-INT-02 | pass. Every §16A.15 output is present. A RANK result and the EVALUATE result for its top candidate agree, including the candidate ID. |
| AT-INT-03 | pass. Exceeding k_max, duplicate targets, empty targets, ineligible accounts or edges, and RANK requests that carry targets all return 400 before any scenario exists. A suspicious community returns 409. |
| AT-INT-04 | pass. Results are identical across runs and under CPU load. |
| AT-INT-05 | pass. The candidate pool is exact, has one candidate per account, follows the §16A.4.3 order, and fails when it exceeds the cap. |
| AT-INT-06 | pass. Ties are broken by candidate ID. |
| AT-INT-07 | pass. The import boundary holds and the engine is pure. |
| AT-INT-08 | pass. Zero denominators are reported as explicit 0 and listed as unavailable. |
| AT-INT-09 | pass, with removal of D giving 1.0000000 and removal of A giving 0.4390244 (see OQ-80). |
| AT-INT-10 | pass. A user's third queued scenario returns 429. |
| AT-EVAL-01..03 | pass. All four levels are present with lineage, and the transaction PR-AUC is recomputed independently. Network metrics are recomputed independently. Intervention effectiveness is compared with the degree baseline. The progression, the PaySim limitation and the NOT_MEASURABLE metrics are shown. |

## Known bugs and limitations

- The degree-ranked baseline is evaluated in memory through the intervention engine and is not persisted as a scenario (OQ-83).
- The local demo stack reuses a model across datasets, so evaluation correctly reports FAILED there. A dataset whose model was trained on it evaluates normally.

## Open questions and defaults introduced

OQ-80 to OQ-83. Newly open: **OQ-80**, an SRS fixture correction for Partha.

## Next steps

1. Optional copilot track: T40 (backend: Ollama, context retrieval, validation, limits) and T41 (UI panel).
2. Phase 6, T42–T45: endpoint inventory with an empty NOT_YET, security hardening, E2E golden path, traceability and release.
