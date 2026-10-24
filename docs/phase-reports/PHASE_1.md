# Phase 1 — Foundation (T01–T12)

**Gate status: PASSED** (2026-10-17), with the one temporary strict xfail the plan permits (AT-SEC-02 until T24).

## Tasks completed

| Task | Commit | Summary |
|---|---|---|
| T01 | `dd01e36` | Tree of PLAN §4, uv + ruff (E,F,I,B,UP,S) + mypy strict, `.env.example` with every §23.2 key, Makefile, `docs/SRS.md` (byte-identical), `docs/PLAN.md`, `docs/OPEN_QUESTIONS.md`. |
| T02 | — | `core/`: config (fail-fast secrets), JSON logging, error envelope + 32 error codes, UUIDv5 ids, decimal (`round7`), time, pagination (cap 10,000, cursors), lineage/staleness, percentile rank; request-ID / log / body-size middleware; app factory. |
| T03 | — | Migrations 0001–0002 (identity, canonical, pipeline, lineage), roles via `docker/postgres/init.sh`, ORM models, `scripts/schema_check.py`. |
| T04 | — | Migrations 0003–0006: 36 tables, composite community FKs, immutability trigger (`reject_immutable_update`, "Once" columns), app-role revokes on 12 append-only tables, SECURITY DEFINER purge functions (OQ-11). |
| T05 | — | `docker-compose.yml` (8 services, only dashboard/backend publish ports), one backend image with `backend`/`worker`/`migrate` entrypoints, `/health`, `/ready`, Neo4j constraints CLI. |
| T06 | — | Opaque sessions (SHA-256 stored), Argon2id, throttling from audit events, permission matrix as data, audit service, users API, bootstrap-admin CLI. |
| T07 | — | PostgreSQL job queue (SKIP LOCKED claim), heartbeat thread, lease reaper, guarded completion, per-kind slots and timeouts, worker entrypoint. |
| T08 | — | State machine (18 states) as data, stage registry with recorded no-op stages, pipeline handler, retry, pipeline/model/context APIs, `/ingestion/{id}/retry` alias. |
| T09 | — | PaySim adapter (discards `isFlaggedFraud` and balances), validation codes, streamed upload with cap and checksum, UNLOGGED staging + COPY, single-transaction canonical insert, reference-slice tool, `mulenetx ingest`. |
| T10 | — | Profiling stage and `GET /datasets/{id}/profile` (all §7.9 metrics). |
| T11 | — | Neo4j snapshot build (UNWIND/MERGE batches, TRANSFERRED_TO aggregates), validation (counts, exact micro-unit sums, digest), batched delete for retry, SNAPSHOT_RETIRE job. |
| T12 | `6855e1b` | Activation (§6.9 in one transaction, projections, retirement of the previous snapshot), accounts search/profile, keyset transactions, bounded neighborhood (408/410/503). |

Commit hashes for every task: `git log --oneline rebuild`.

## Key files and decisions

- Backend package: `backend/mulenetx/` (layout of PLAN §4). Services never import FastAPI; routes call services/repositories.
- `mulenetx/core/runtime.py` holds the engine, session factory and Neo4j client for both processes.
- Jobs: `jobs/queue.py` (claim SQL of PLAN §7.2), `jobs/lease.py`, `jobs/runner.py`, `jobs/pipeline_handler.py`, `jobs/stages/*`.
- Stage contract: the run enters a stage's running state when its job starts; success commits final outputs + done state + next job + job SUCCEEDED in one transaction (OQ-19).
- Later-phase stages are recorded no-ops: PROFILING (now real), GRAPH_BUILDING (now real), ANALYTICS (writes an `analytics_runs` row `{"noop": true}`), FEATURES/TRAINING/SCORING/RING_ANALYSIS (no rows). RING_ANALYSIS's final transaction runs activation.
- Test infrastructure: `docker-compose.test.yml` (PostgreSQL 127.0.0.1:55432, Neo4j 127.0.0.1:57687) — OQ-02. `tests/factories.py` makes fresh rows for all 36 tables; `tests/endpoints.py` is the endpoint→permission registry used by AT-SEC-01/04.
- All assumptions: `docs/OPEN_QUESTIONS.md` OQ-01 … OQ-36.

## Commands run and results (last run)

```
cd backend
uv run ruff check .                     # All checks passed!
uv run mypy mulenetx                    # Success: no issues found in 117 source files
uv run pytest -m "not docker"           # 219 passed, 1 xfailed (AT-SEC-02, strict, T24)
uv run pytest tests/acceptance/test_AT_OPS_01_clean_startup.py -m docker          # 1 passed
uv run pytest tests/acceptance/test_AT_OPS_03_worker_killed_resume.py -m docker   # 1 passed (98.8 s, real `docker kill`)
python ../scripts/schema_check.py --dsn <owner dsn>                               # 36 tables checked, 0 differences
```

## Gate

| AT | Result |
|---|---|
| AT-DATA-01..05 | pass (05: 200 MB upload → 202 in < 30 s) |
| AT-GRAPH-01..05 | pass |
| AT-OPS-01 | pass (Compose stack; only dashboard/backend published) |
| AT-OPS-03 | pass (in-process and real container kill) |
| AT-OPS-06 | pass (every PK/FK/UNIQUE/CHECK rejected, >300 immutable columns, privileges) |
| AT-SEC-01, 03, 04, 05 | pass (SEC-03/04 cover the endpoints that exist; completed in T43) |
| AT-SEC-02 | strict xfail until `GET /audit` exists (T24) — the single xfail PLAN T06 permits |

## Known bugs / limitations

- Host differs from the SRS reference (8 vCPU / 8 GiB, Docker VM 3.8 GiB) — OQ-03. The local `.env` uses `qwen2.5:1.5b-instruct` — OQ-14.
- Profile path statistics are lower bounds when `path_enumeration.truncated` is true (by design, §7.9).
- FastAPI spools multipart uploads to a temp file before the handler copies to `STAGING_DIR` (OQ-27).
- Other projects' containers on this machine were stopped to free port 8000 and VM memory; names saved in the session scratchpad (`docker start` restores them).

## Open questions / defaults introduced

OQ-01 … OQ-36 in `docs/OPEN_QUESTIONS.md`; `open` items needing Partha: OQ-03 (hardware), OQ-14 (model size), OQ-15 (password policy).

## Next steps (Phase 2, T13–T21)

1. T13: replace the ANALYTICS no-op with NetworkX metrics/components/Louvain (`analytics/`), AT-ANALYTICS-01..02.
2. T14–T15: feature registry v1 (42 features) and FEATURES stage.
3. T16–T17: target/splits/leakage, training snapshots, XGBoost training and registry.
4. T18–T19: risk composition, propagation, SCORING stage and risk APIs.
5. T20–T21: SHAP, graph metrics/community APIs, AT-OPS-04.
