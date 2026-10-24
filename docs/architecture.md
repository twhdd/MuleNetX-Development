# Architecture

This document explains how MuleNetX is put together: its processes, the analysis pipeline, the data lineage, and the main design invariants. The normative text is [SRS.md](SRS.md). Section references (§) point there.

## Processes

| Service | What it does | Published port |
|---|---|---|
| `dashboard` | nginx serving the React build; proxies `/api`, `/health` and `/ready` to `backend` | 8080 |
| `backend` | FastAPI (`mulenetx.main`): authentication, the API of §19, on-demand SHAP and the copilot. It never runs long work. | 8000 |
| `worker` | The job runner (`mulenetx.worker`). It leases jobs from the PostgreSQL queue, sends heartbeats, and resumes after a crash (§7.8). | none |
| `migrate` | A one-off service: applies the Alembic migrations as the owner role, creates the Neo4j constraints, then exits. | none |
| `postgres` | PostgreSQL 16: the canonical data, the analytical results, the job queue and the audit log. | none |
| `neo4j` | Neo4j 5: a derived graph projection of one snapshot, rebuilt from PostgreSQL and never authoritative. | none |
| `ollama` | A local LLM for the optional copilot (§21). Nothing leaves the host. | none |

The backend and worker connect as `mulenetx_app`, which has no DDL rights. Only `migrate` uses `mulenetx_owner` (§6.5).

### Jobs

The worker has two slot groups:

| Slot group | Job kinds | Concurrency |
|---|---|---|
| pipeline | `INGEST`, `PIPELINE_STAGE`, `TRAIN`, `SNAPSHOT_RETIRE` | one at a time |
| analysis | `INTERVENTION`, `EVALUATION` | two at a time |

Each job runs as follows:

- **Lease.** It is claimed with `FOR UPDATE SKIP LOCKED` and holds a lease that heartbeats renew.
- **Expiry.** If the lease expires, another worker can reclaim the job and retry it up to `job_max_attempts`.
- **Failure.** On failure the job records a safe message and a failure category.
- **Resume.** A failed pipeline run resumes from its failed stage (`POST /pipeline-runs/{id}/retry`).

## Pipeline

A pipeline run is a deterministic state machine (§7.6). Each stage is one job:

```text
CREATED → INGESTING → INGESTED → PROFILING → PROFILED → GRAPH_BUILDING → GRAPH_READY
  → ANALYTICS_RUNNING → ANALYTICS_READY → FEATURES_RUNNING → FEATURES_READY
  → TRAINING → MODEL_READY → SCORING → SCORED → RING_ANALYSIS → READY        (any stage → FAILED)
```

| Stage | What happens |
|---|---|
| Ingestion | Validates every row, rejecting with reason codes. Writes dataset-namespaced accounts and transactions. Refuses a file already registered for that dataset version (409). |
| Profiling | Records the dataset profile (§7.9) before any analytics. |
| Graph building | Writes the snapshot to Neo4j in batches, then validates counts and a digest against PostgreSQL. A failed build leaves the previous snapshot active. |
| Analytics | Runs in-process with NetworkX on a projection exported in canonical ID order (DEC-01): PageRank, betweenness, Louvain communities, and the six temporal motif detectors (§15.9). |
| Features | Computes registry v1 features as of the snapshot cutoff (§10), under the `RISK_FEATURES_UNAVAILABLE` regime (DEC-03). |
| Training | Trains XGBoost on chronological `TRAINING_SPLIT` snapshots for retrospective detection (DEC-05), but only when no compatible model exists. If training is impossible (for example, no positive labels), the ML component is unavailable and the pipeline still reaches READY. |
| Scoring | Computes ML, then pre-propagation, then propagation (from sources ranked by pre-propagation score), then the final score and tier. Every component carries an availability state, and coverage is reported. |
| Ring analysis | Scores communities as candidates (§9.2), then computes ring membership, features, risk and evidence for potential fraud ring candidates (§9A). |
| Activation | At READY, the single `active_context` row is switched in one transaction. Every read endpoint defaults to that context, and older contexts stay readable through explicit lineage parameters. |

The following work is triggered on demand, outside the pipeline:

| Work | How it runs |
|---|---|
| SHAP | Computed by the backend for one assessment and cached; it explains the ML component only. |
| Intervention scenarios | `INTERVENTION` jobs. They are pure functions of the ring's baseline and never mutate canonical data or the graph. |
| Evaluation runs | `EVALUATION` jobs over the model's test split. |
| Copilot | Answered by the backend. It retrieves only context the caller may read, calls Ollama with a JSON schema, and validates the output (§21). |

## Data lineage (SRS Appendix B)

```text
Dataset ─┬─ DatasetProfile
         └─ IngestionRun → Accounts, Transactions
PipelineRun (stages as Jobs)
  → GraphSnapshot (cutoff, OPERATIONAL | TRAINING_SPLIT; validated; Neo4j build)
  → AnalyticsRun → AccountGraphMetrics, Communities + memberships, TemporalMotifs
  → FeatureVersion → AccountFeatureValues (as_of)
  → ModelVersion (TRAINING_SPLIT snapshots, split boundaries, regime)
  → ScoringRun → RiskAssessments, PropagationContributions, SHAP (on demand)
  → Ring analysis → candidates (+ status history), memberships, feature sets, ring risk
  → ActiveContext (single row, switched at READY)
Investigation: Cases → Subjects, Findings (append-only, evidence references checked)
Hypothetical: InterventionScenarios → candidates;  EvaluationRuns → metrics
Audit: every privileged action and every denial (metadata only for the copilot)
```

Every analytical response carries its `lineage` (dataset, snapshot, analytics run, scoring run, model and risk-logic versions), `computed_at` and `is_stale`.

## Invariants worth knowing

1. **Canonical data is authoritative.** PostgreSQL holds the source of truth, and Neo4j is a rebuildable projection. Labels are used only for training and evaluation, never for scoring, rings or motifs.
2. **One definition of suspicious.** The definitions of suspicious account and suspicious transaction live only in `flow/vocabulary.py`.
3. **Determinism.** IDs derived from content (rings, motifs, paths, candidates) are UUIDv5. Enumeration uses fixed orders and explicit counters. A run that reaches a limit reports truncation instead of silently returning less. Reruns produce identical results (AT-OPS-04), and so do clean environments (AT-E2E-01, five runs).
4. **Hypothetical means hypothetical.** No endpoint or UI control blocks, freezes or changes any account or payment. Intervention outputs are labelled `HYPOTHETICAL SIMULATION`.
5. **Analytical, not accusatory.** Wording never asserts criminality, and the copilot rejects any answer that does (deny-list, §21.6).
6. **Security.**
   - Every route is permission-checked from one matrix (§22.2), and denials are audited.
   - Limits are rejected, never clamped.
   - Errors use one envelope and leak nothing.
   - The session token lives in the browser tab's memory only.

## Code map

| Package | Responsibility |
|---|---|
| `ingestion`, `profiling` | adapters, validation, the reference slice, the dataset profile |
| `graph` | the Neo4j client, the snapshot builder and validator, bounded neighbourhood and path queries |
| `analytics`, `motifs` | graph metrics, communities, temporal motif detection |
| `features`, `ml`, `explain` | the feature registry, training and the model registry, SHAP |
| `risk`, `propagation` | component scores, propagation, final score and tier |
| `flow` | the suspicious vocabulary, bounded money-flow paths, ring-scope path enumeration |
| `rings` | candidates, membership, ring features, risk and evidence |
| `interventions` | the pure intervention engine (§16A) |
| `evaluation` | multi-level evaluation (§28.7) |
| `investigation` | cases, subjects, findings and their rules |
| `copilot` | intents, context retrieval, the Ollama client, validation, limits |
| `jobs`, `activation` | the queue, the runner, pipeline stages, context activation |
| `auth`, `audit`, `api`, `core`, `db` | identity and permissions, the audit log, routes and schemas, configuration, persistence |
