# Phase 2 — Account analytics (T13–T21)

**Gate status: PASSED** (2026-10-18).

## Tasks completed

| Task | Summary |
|---|---|
| T13 | NetworkX projection export (canonical order), degree, PageRank (0.85/100/1e-6, uniform dangling), exact Brandes betweenness, WCC (min account id), Louvain (res 1.0, seed 42), canonical community IDs; analytics run + outputs in one COPY transaction. Content-derived snapshot IDs (OQ-37). |
| T14 | `features/registry_v1.json` (42 entries, every §10.5 field; `definition_hash` = file SHA-256), transactional F01–F10/F20–F26/F35/F38–F42, temporal F27–F30 (§15.3–§15.7), state encoding. |
| T15 | Graph F11–F18, flow F32/F34 (DFS pre-order, cap 100), risk-derived features UNAVAILABLE under the frozen regime, FeatureService (COPY persistence, deterministic `feature_snapshot_id`), FEATURES stage. |
| T16 | Target (retrospective detection), nearest-rank split boundaries, first-split entity assignment, TRAINING_SPLIT snapshots + analytics + features, seven leakage checks. |
| T17 | Native XGBoost training (§11.8), max-F1 threshold, §11.10 metrics, artifacts + SHA-256, registry and compatibility rule (§7.6 rule 3), normalization reference + risk logic version, TRAINING stage; ML-unavailable path (rule 4). |
| T18 | Pure risk functions: normalizers, G_SET/B_SET components, rules R01–R05, decimal composition (7 dp half-even before tiers), tiers, coverage, max attainable. |
| T19 | Per-source bounded BFS propagation, SCORING stage (§12.1 order), risk/history/propagation/features/temporal APIs. |
| T20 | On-demand TreeSHAP (XGBoost built-in, OQ-58) with immutable cache, `GET /accounts/{id}/shap`. Fixed a T19 persistence bug (all rows had received the last account's components) and added `tests/integration/test_scoring_integrity.py`. |
| T21 | `GET /graph/metrics`, `/communities`, `/communities/{id}`, `/accounts/{id}/community`; AT-OPS-04. |

## Key decisions (see `docs/OPEN_QUESTIONS.md` OQ-37 … OQ-59)

- Snapshot IDs are UUIDv5 of content so reruns reproduce community/motif/path IDs (OQ-37); run IDs stay random.
- Assessment IDs UUIDv5(scoring run, account); the scoring run is created only after the model is load-checked (OQ-55).
- Risk logic versions carry `normalization_reference.model_version`; a reused model brings its own (OQ-49).
- Native XGBoost API (scikit-learn wrapper incompatible with sklearn 1.9, OQ-48); XGBoost built-in TreeSHAP (OQ-58).

## Commands and results (last run)

```
cd backend
uv run ruff check .        # All checks passed!
uv run mypy mulenetx       # Success: no issues found in 152 source files
uv run pytest -m "not docker"   # 351 passed, 1 xfailed (AT-SEC-02 until T24)
```

Gate tests: AT-ANALYTICS-01..02, AT-FEAT-01..04, AT-ML-01..04, AT-RISK-01..06, AT-PROP-01..03, AT-XAI-01, AT-TEMP-01..02, AT-OPS-04 — all PASSED (`-k` run listed per file in the session log).

## Known bugs / limitations

- Propagation is one Python BFS per source (as specified); may be slow around merchant hubs on the reference slice (OQ-56) — measured in T29.
- Docker incident 2026-10-18: host disk filled (test staging leftovers, 3.5 GB) and Docker Desktop hung; fixed by cleaning test staging (now auto-cleaned by a session fixture) and restarting Docker Desktop. Other projects' containers were stopped again.
- Test PostgreSQL uses tmpfs; restarting test services empties it (fixtures re-migrate).

## Next steps (Phase 3, T22–T29)

T22 interactive paths (`/graph/path`, `/graph/paths/{id}`, `/money-flow` alias) → T23 cases/subjects/findings → T24 audit API + inventory test (removes the AT-SEC-02 xfail) → T25–T28 frontend (use impeccable; MULENETX_REDESIGNED.jsx as inspiration; heatmap must use real data, no fabricated geography) → T29 benchmark + AT-OPS-02.
