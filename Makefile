SHELL := /bin/bash
COMPOSE := docker compose
TEST_COMPOSE := docker compose -f docker-compose.test.yml -p mulenetx-test
UV := cd backend && uv run

.PHONY: up down logs migrate test test-backend test-frontend test-acceptance test-e2e lint typecheck \
        bench openapi gen-types traceability demo test-services test-services-down e2e-stack e2e-stack-down demo-down test-docker test-perf test-ollama

up:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

migrate:
	$(COMPOSE) run --rm migrate

# Local test services (PostgreSQL + Neo4j on 127.0.0.1 only; separate project from the app stack).
test-services:
	$(TEST_COMPOSE) up -d --wait

test-services-down:
	$(TEST_COMPOSE) down -v

lint:
	$(UV) ruff check .
	@if [ -f frontend/package.json ]; then cd frontend && npm run lint; fi

typecheck:
	$(UV) mypy mulenetx
	@if [ -f frontend/package.json ]; then cd frontend && npm run typecheck; fi

test: test-backend test-frontend

# JUnit reports in backend/reports/ feed `make traceability`.
test-backend: test-services
	$(UV) pytest -m "not docker and not perf and not e2e and not ollama" --junitxml=reports/junit-backend.xml

test-frontend:
	@if [ -f frontend/package.json ]; then cd frontend && npm test; fi

test-acceptance: test-services
	$(UV) pytest tests/acceptance -m "not docker and not perf and not e2e" --junitxml=reports/junit-acceptance.xml

# Tests that drive the Compose stack (AT-OPS-01..03, port scan); needs `.env`. Stop the test services first on
# a small Docker VM.
test-docker:
	$(UV) pytest -m docker --junitxml=reports/junit-docker.xml

# AT-OPS-05 reads docs/benchmark.json from `make bench` (reference environment and slice, §25.1).
test-perf:
	$(UV) pytest -m perf --junitxml=reports/junit-perf.xml

test-ollama:
	$(UV) pytest -m ollama --junitxml=reports/junit-ollama.xml

# AT-E2E-01 needs a clean environment with an empty model registry. `make e2e-stack` starts a throwaway
# Compose project (own volumes, the usual ports; stop `make up` first) and creates the bootstrap admin;
# `make e2e-stack-down` removes it with its volumes. The dashboard run needs E2E_PASSWORD (frontend/e2e/).
e2e-stack:
	$(COMPOSE) -p mulenetx-e2e up --build -d --wait postgres neo4j backend worker dashboard
	$(COMPOSE) -p mulenetx-e2e exec -T backend python -m mulenetx.cli bootstrap-admin

e2e-stack-down:
	$(COMPOSE) -p mulenetx-e2e down -v

# Backend AT-E2E-01 (five clean runs) on the test services, then the dashboard golden path against the
# e2e stack.
test-e2e: test-services
	$(UV) pytest tests/e2e -m "e2e" --junitxml=reports/junit-e2e.xml
	cd backend && uv run python -m tests.e2e.fixture ../frontend/e2e/.data/golden.csv
	cd frontend && npm run e2e

bench:
	$(UV) python ../scripts/bench.py

openapi:
	cd backend && uv run python -m mulenetx.cli export-openapi --out ../docs/openapi.json

gen-types: openapi
	cd frontend && npx openapi-typescript ../docs/openapi.json -o src/api/schema.d.ts

traceability:
	$(UV) python ../scripts/check_traceability.py

# The 16 demonstration scenarios of SRS §29 on a clean throwaway stack (project mulenetx-demo, own volumes,
# usual ports; the main stack is stopped first). Leaves the stack up to explore; `make demo-down` removes it.
demo:
	$(COMPOSE) stop
	$(COMPOSE) -p mulenetx-demo up --build -d --wait postgres neo4j backend worker dashboard
	$(COMPOSE) -p mulenetx-demo exec -T backend python -m mulenetx.cli bootstrap-admin
	$(UV) python ../scripts/demo.py --project mulenetx-demo

demo-down:
	$(COMPOSE) -p mulenetx-demo down -v
