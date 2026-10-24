# Build status

This is the live handoff file. A fresh session reads it first, then the latest `PHASE_n.md`, then `docs/PLAN.md`.

## Where things stand

- **Branch:** `rebuild`, with one commit per task (`Tnn: ...`). Nothing has been pushed.
- **Completed tasks:** T01–T45, every task in the plan, including the optional copilot track T40–T41.
- **Gates:**

  | Gate | Status |
  |---|---|
  | Phases 1, 2, 4 and 5 | PASSED |
  | Copilot (AT-AI-01..05) | passing against a mock Ollama |
  | Phase 3 | **not passed**: AT-OPS-05 |
  | Phase 6 | **not passed**: `make traceability` has one gap, AT-OPS-05 |

  Phases 3 and 6 share the same blocker: the reference environment and the PaySim slice are unavailable (OQ-72).
- **Test status (last run, 2026-10-18/19):**

  | Suite | Result |
  |---|---|
  | `make lint typecheck` | exit 0 |
  | Backend default suite | 646 passed |
  | e2e | 5 passed |
  | docker | 4 passed |
  | perf | 2 passed, 1 failed (AT-OPS-05) |
  | Frontend | 55 passed |
  | Dashboard golden path (Playwright) | passed |
  | `make demo` | 15 of 16 scenarios pass; scenario 8, the copilot answer, needs a capable host |
  | Traceability | 83 of 84 acceptance tests pass |

  Details are in [PHASE_6.md](PHASE_6.md).

## Blockers for Partha

These blockers need Partha's decision or hardware:

- **OQ-72 / OQ-03.** AT-OPS-05 needs reference hardware and the slice, or an approved exception.
- **OQ-14 / OQ-85 / OQ-89.** The copilot model needs a host with at least 8 GiB for Docker.
- **OQ-80.** An SRS fixture correction.
- **OQ-15.** Confirmation of the password policy.
- **OQ-56.** Propagation performance on the slice.
- **OQ-67.** The design direction.

## Next action

None in the plan. Once the hardware or the decisions above are available, run:

- `make bench && make test-perf && make traceability`;
- `make test-ollama && make demo` with the copilot model pulled.

## Environment

**Test services:** `make test-services` (PostgreSQL :55432, Neo4j :57687; tmpfs, so they are empty after a restart until the tests migrate).

**App stack:** `docker compose up --build -d` with a local `.env` (not committed). Then run `python -m mulenetx.cli bootstrap-admin` inside `backend`.

**Throwaway stacks:**
- `make e2e-stack` / `make e2e-stack-down`
- `make demo` / `make demo-down`

Each uses its own Compose project and volumes on the same ports, so stop the main stack first.

**Rules for working on this host:**
- Keep at least 3 GB of host disk free. Docker hangs when the disk fills.
- The Docker VM has 3.8 GiB. Do not run the app stack and the test services together with Ollama.
- Never run a development worker or uvicorn against the test database while tests run. It claims test jobs, and the suite truncates the database.

## Where to find things

- **Documentation:** README, `docs/architecture.md`, `docs/limitations.md`, `docs/api-errors.md`, `docs/traceability.md`, `docs/benchmark.md`.
- **Frontend:** `frontend/` (see its README). The design context is in `PRODUCT.md`, `DESIGN.md` and `.impeccable/`. Regenerate the types with `make gen-types` after any API change.
