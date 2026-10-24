# Phase 6 — Hardening and release (T42–T45), with the copilot track (T40–T41)

**Gate status: NOT PASSED** (2026-10-19). Three PLAN gate items are met:
- AT-E2E-01 passes five consecutive runs with identical deterministic outputs.
- The full `make test` is green.
- The OpenAPI inventory is complete, with `NOT_YET` empty.

**`make traceability` exits 1** on one gap, AT-OPS-05. This is the same reference-environment blocker that keeps the Phase 3 gate open (OQ-72). Every other one of the 84 acceptance tests passes.

The copilot track (AT-AI-01..05) passes against a mock Ollama. No real model produced a grounded answer on this host (OQ-85).

## Tasks completed

| Task | Commits | Summary |
|---|---|---|
| T40 | `0f8cafe`, `248c255` | `POST /copilot/query`: rule-based intents, retrieval of authorized context with stable references, the Ollama client with the response schema as `format`, five validation rules, a semaphore with a per-user rate limit, and metadata-only audit. A live run found two defects, both fixed: see Defects below. |
| T41 | `a03701c` | `CopilotPanel` in the account, case and ring workspaces. It shows facts, signals, interpretation and limitations separately; references are links; everything carries the `AI INTERPRETATION` label. Unavailable, busy, rate-limited and discarded states are confined to the panel. |
| T42 | `0f3331e` | AT-E2E-01 through the API, from truncated databases and an empty registry, run five times with per-section digests. The Playwright golden path runs through the dashboard on a throwaway Compose project. The §27.12 reliability tests and AT-OPS-01..03 were re-run. |
| T43 | `76b8b87` | Security suite: injection into every string parameter of every operation, every limit parameter rejected, case field and participant rules per role, deny-list vectors, and unpublished ports unreachable from the host. Also fixed two test races. |
| T44 | `bb8546e` | `scripts/demo.py` and `make demo`: the 16 §29 scenarios on a clean throwaway stack, with injected failures. Also the README, `docs/architecture.md` and `docs/limitations.md`. |
| T45 | `154dd63`, `0fbfab5` | `make traceability` → `docs/traceability.md`; `export-errors` → `docs/api-errors.md`; the label-isolation check for definition-of-done item 9. |

## Key decisions

All are recorded in [OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md).

**The clean environment for AT-E2E-01** (OQ-87):
- The backend test truncates PostgreSQL and Neo4j. With an empty registry, training therefore runs every time.
- Run-scoped UUIDs differ between environments by design, so the comparison excludes them.
- The dashboard run uses its own Compose project, so it never touches the user's volumes.

**Copilot context window** (OQ-85):
- The client sends `num_ctx` = context budget + output budget + 2,048.
- It sends `num_predict` = limit + 1, so validation rule 5 can actually fire.

**Security scope and the no-op PATCH** (OQ-88): a PATCH that sets a field to its current value is a no-op. Only a real change is permission-checked.

**Demo** (OQ-89): the demo runs on the synthetic labelled fixture because no PaySim file is available, in a stack started with empty volumes.

**Traceability** (OQ-90):
- Results come from the JUnit reports of the make targets; a test with no recorded result counts as a gap.
- The source labels are allowed only in the modules the SRS needs (OQ-91), enforced by a test.

## Defects found and fixed in this phase

1. **Ollama silently truncated the prompt.** Its default 2,048-token window dropped the start of the ~2.6k-token prompt, which is where the system rules are. Found by the live run; the client now sends `num_ctx`.
2. **Validation rule 5 could never fire.** `num_predict` equalled the limit, so an over-long answer surfaced as a parse failure. It is now the limit + 1.
3. **AT-OPS-03 could not be rerun.** It reused one dataset version, so a second run on the same stack was correctly refused with 409. The version is now unique per run.
4. **Two tests raced the worker's threads.** When stopping a pipeline at `PROFILED`, roughly one run in three let a later stage get claimed first. Both tests (the failure/retry test and the AT-API-01 helper) now wait for claimed jobs to finish before reading the state.
5. **`make typecheck` was broken.** It called a frontend `typecheck` script that did not exist; the script now exists.
6. **AT-OPS-06 was invisible to traceability.** Its tests did not carry the AT-ID in their names; they were renamed.

## Commands run and results (last run, 2026-10-18/19)

```
make lint typecheck                                     # exit 0 (ruff, mypy strict: 204 files; eslint; tsc)
cd backend
uv run pytest -m "not docker and not perf and not e2e and not ollama" --junitxml=reports/junit-backend.xml
                                                        # 646 passed
uv run pytest tests/e2e -m e2e                          # 5 passed (AT-E2E-01 ×5, digests identical)
uv run pytest -m docker                                 # 4 passed (AT-OPS-01, -02, -03; host port scan)
uv run pytest -m perf                                   # 2 passed, 1 failed (AT-OPS-05 reference environment)
OLLAMA_LIVE_MODEL=qwen2.5:1.5b-instruct OLLAMA_LIVE_NUM_CTX=4096 uv run pytest -m ollama
                                                        # 1 passed; outcome 503 AI_RESPONSE_INVALID rule 5 (OQ-85)
uv run python ../scripts/schema_check.py --dsn <test owner DSN>   # 36 tables, 0 differences
cd ../frontend && npm test                              # 55 passed
npm run e2e (against make e2e-stack)                    # 1 passed (dashboard golden path, 41 s)
make demo                                               # scenarios 1–7 and 9–16 PASS; 8 FAIL (OQ-89)
make traceability                                       # 170 requirements, 84 AT-IDs, 83 passing; gap: AT-OPS-05
```

Visual check of the copilot panel: `.impeccable/review/t41/` at 1440 and 390 px. The unavailable state is from the live stack. These captures are not committed.

## Definition of done (PLAN §12)

| # | Item | State |
|---|---|---|
| 1 | Compose reaches `/ready` 200; only `dashboard` and `backend` published | **met** (AT-OPS-01; host port scan) |
| 2 | `make lint typecheck test` green; AT-E2E-01 five identical runs | **met** |
| 3 | Every requirement and AT-ID linked to a passing test | **not met**: AT-OPS-05 → NFR-02, NFR-16 (OQ-72) |
| 4 | `schema_check.py` reports no difference | **met** |
| 5 | Every §19.2 endpoint and alias implemented with its permission | **met** (`NOT_YET` empty) |
| 6 | §25.1 targets met on reference-class hardware, or an approved exception | **not met**: the measurements met the targets on the synthetic set on this 8 GiB host; there is no reference slice or hardware, and the exception awaits Partha (OQ-72, OQ-03) |
| 7 | `make demo` runs the 16 scenarios | **runs all 16; 15 pass**. Scenario 8 needs a copilot model that answers within 20 s (OQ-89) |
| 8 | No `open` item that affects observable behaviour | **not met**: see below |
| 9 | No source-label leakage | **met**, enforced by `tests/unit/test_label_isolation.py` (OQ-91) |

## Genuine blockers (for Partha)

- **OQ-72 / OQ-03.** Run `make bench` and `make test-perf` on reference hardware with the PaySim reference slice active, or approve the documented exception. This closes AT-OPS-05, definition-of-done items 3 and 6, and the Phase 3 gate.
- **OQ-14 / OQ-85 / OQ-89.** Run the copilot with the 7B model on a host with at least 8 GiB for Docker. Then run `make test-ollama` and `make demo`.
- **OQ-80.** Correct the SRS network-risk counterexample: 0.40 → 0.4390244.
- **OQ-15.** Confirm the default password policy for user management.
- **OQ-56.** Check propagation performance on the reference slice (part of OQ-72).
- **OQ-67.** The dashboard design direction was chosen without design questions; Partha may re-steer it.

## Known limitations

See [docs/limitations.md](../limitations.md).
