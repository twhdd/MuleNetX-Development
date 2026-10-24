# MuleNetX

MuleNetX is a graph-based platform for investigating money-mule activity. It ingests PaySim-format transactions, builds a validated Neo4j graph, and computes graph analytics and temporal motifs. It trains a replaceable XGBoost model and scores every account with explainable components. It surfaces candidate fraud rings, simulates network interventions hypothetically, and supports investigators with cases, findings and an optional local AI copilot.

Built to **SRS v1.3.3** ([docs/SRS.md](docs/SRS.md)) following [docs/PLAN.md](docs/PLAN.md).

- Build status and handoff notes: [docs/phase-reports/STATUS.md](docs/phase-reports/STATUS.md)
- Assumptions, conflicts and open questions: [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md)
- Architecture and data lineage: [docs/architecture.md](docs/architecture.md)
- Known limitations: [docs/limitations.md](docs/limitations.md)
- API contract: [docs/openapi.json](docs/openapi.json); error codes: [docs/api-errors.md](docs/api-errors.md)
- Requirement → test traceability: [docs/traceability.md](docs/traceability.md)

## Prerequisites

- Docker with Compose v2. Give the Docker VM at least 4 GiB of memory (8 GiB to run the default 7B copilot model) and keep at least 3 GB of free disk.
- For development and tests:
  - Python 3.12 with [uv](https://docs.astral.sh/uv/)
  - Node 20+ with npm
  - Google Chrome, which the Playwright end-to-end run uses

## Configure

```bash
cp .env.example .env
```

Fill every secret in `.env`:

- the PostgreSQL superuser, owner and app passwords;
- the Neo4j password;
- the bootstrap admin username and password, which must be at least 12 characters.

Startup refuses missing values and known default secrets (SR-15). `.env` is never committed.

To change the copilot model, set `OLLAMA_MODEL`. The default is `qwen2.5:7b-instruct`. A smaller model such as `qwen2.5:1.5b-instruct` fits a 4 GiB Docker VM, but a CPU-only host cannot meet the 20 s copilot timeout (OQ-85).

## Run

```bash
docker compose up --build -d          # or: make up
docker compose exec backend python -m mulenetx.cli bootstrap-admin
open http://localhost:8080            # the dashboard; the API is on http://localhost:8000
```

Startup works as follows:

- `migrate` applies the schema and the Neo4j constraints, then exits.
- `backend` (FastAPI) and `worker` (the job runner) start once `migrate` has finished.
- `/ready` returns 200 when PostgreSQL and the active context are usable.

Only `dashboard` (8080) and `backend` (8000) publish ports (SR-22). The copilot model is pulled by the one-off `ollama-pull` service: run `docker compose up ollama-pull`.

Sign in to the dashboard as the bootstrap admin. Then create the other users on **Admin → Users**: investigators and analysts.

## Load data

**From the dashboard.** Open **Admin → Ingestion**, choose a PaySim CSV, and select **Upload and start pipeline**. The upload returns at once. Follow the pipeline run on **Admin → Pipelines**. It moves through:

`INGESTING → PROFILED → GRAPH_BUILDING → … → TRAINING → SCORING → RING_ANALYSIS → READY`

At `READY`, the active context switches atomically and the banner updates.

**The PaySim reference slice (DEC-01).** Acceptance and benchmarks use the slice: the longest prefix of steps with at most 1,000,000 rows.

```bash
cd backend
uv run python ../scripts/make_reference_slice.py PS_20174392719_1491204439457_log.csv /tmp/paysim-slice.csv
# prints the adapter_config; register the slice with it:
docker compose cp /tmp/paysim-slice.csv backend:/data/staging/paysim-slice.csv
docker compose exec backend python -m mulenetx.cli ingest --path /data/staging/paysim-slice.csv \
  --name paysim-reference --dataset-version slice-v1 --adapter-config '<printed json>'
```

**Without PaySim.** `make demo` uses a synthetic labelled fixture (`backend/tests/e2e/fixture.py`).

## Demonstration

```bash
make demo        # SRS §29 scenarios 1–16 on a clean throwaway stack (project mulenetx-demo)
make demo-down   # remove that stack and its volumes
```

`make demo` first stops the main stack, because the demo uses the same ports. It then starts a stack with empty volumes, creates the bootstrap admin, and runs `scripts/demo.py`. The script prints every step and a PASS/FAIL summary. Scenarios 9–11 and 16 inject failures by stopping and starting Compose services, then restore them. For scenario 8, the copilot model must be pulled into that project and must answer within the timeout.

## Develop and test

```bash
make test-services           # PostgreSQL :55432 and Neo4j :57687 for tests (project mulenetx-test)
make lint typecheck          # ruff, mypy strict, eslint, tsc
make test                    # backend (without docker/perf/e2e/ollama markers) + frontend (Vitest)
make test-e2e                # AT-E2E-01: five clean API runs + the dashboard golden path (needs `make e2e-stack`)
make openapi gen-types       # export docs/openapi.json and regenerate the frontend types
make traceability            # requirement → AT → test report (docs/traceability.md)
make bench                   # performance harness (docs/benchmark.md)
```

Some tests need extra setup:

- **`docker`** tests (`uv run pytest -m docker`) drive the real Compose stack.
- **`ollama`** tests need a reachable Ollama: see `backend/tests/integration/test_ollama_live.py`.
- **The dashboard e2e run** needs `E2E_PASSWORD` set to the e2e stack's admin password.

Do not run a development worker against the test database while tests run. It claims test jobs.

Repository layout:

- `backend/mulenetx/`: the API, worker, analytics, ML and copilot.
- `backend/tests/`: unit, integration, acceptance (`test_AT_*`), security and e2e tests.
- `frontend/`: the dashboard. See [frontend/README.md](frontend/README.md).
- `docker/`: the PostgreSQL init script.
- `scripts/`: the demo, the benchmark, the reference slice and the traceability check.
