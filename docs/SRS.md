# MuleNetX — Software Requirements Specification

## Graph-Native Financial Crime Intelligence & Investigation Platform

| Field | Value |
|---|---|
| Document title | MuleNetX — Software Requirements Specification |
| Version | **1.3.3** |
| Status | FROZEN — Engineering / Implementation Specification |
| Supersedes | SRS v1.3.2 |
| Product source of truth | Finalized MuleNetX README |
| Change basis | MuleNetX Principal Engineer Design Audit (2026-10-17), findings AUD-001 to AUD-032 |
| Structural reference | JÄGER SRS v2.0 |
| Project type | Graph analytics / ML / financial-crime investigation |
| Relational source of truth | PostgreSQL |
| Graph platform | Neo4j (Community edition sufficient) |
| Backend | FastAPI (API process + worker process, one codebase) |
| Frontend | React + D3 + Zustand |
| Initial ML | XGBoost behind a replaceable model interface |
| Explainability | SHAP (TreeSHAP) |
| Local AI | Ollama + Qwen behind an AI service boundary |
| Deployment | Docker Compose |
| Primary demonstration dataset | PaySim |

## Revision History

| Version | Description |
|---|---|
| 0.1 | Initial SRS derived from README. |
| 1.0 | Expanded requirements, data model, API, security, evaluation, acceptance, and risk sections. |
| 1.1 | Implementation-readiness revision: formal domain model, synchronization, feature/API/service boundaries, pipeline semantics, configuration, NFR targets, testing direction. |
| 1.2 | Deterministic implementation contract: PostgreSQL schema, normative 42-feature registry, account-level target policy, frozen risk/ring/propagation configuration, API/auth/RBAC/AI contracts, graph algorithm parameters, temporal/money-flow semantics, threat model, traceability, acceptance tests. |
| 1.3 | Uniqueness extension: Ring Intelligence, Temporal Behavioral Motifs, Network Intervention Analysis, Multi-Level Evaluation. |
| 1.3.1 | Contract cleanup and freeze: ring-risk formulas, intervention mathematics, analytical schemas, evaluation reference construction, traceability. |
| 1.3.2 | Freeze hardening: motif-confidence parameters, intervention candidate generation, traceability labels, risk terminology. |
| **1.3.3** | **Audit correction release**, including the design-review fixes of Appendix F.6. Introduces the event-time model (§3.4) and the suspicious-flow vocabulary (§3.5); makes the scoring order acyclic (§12–13); completes the pipeline state machine and adds a job execution model (§7); namespaces canonical identifiers per dataset (§6.2); defines the Neo4j physical schema and snapshot switch-over (§6.8); separates analytical from interactive path bounds and makes intervention residuals exact (§16A); revises intervention network risk (§16A.5); adds missing persistence, endpoints, permissions and authentication sessions; defines motif enumeration, ring membership, risk components and evaluation metrics; deterministic identifiers throughout; regenerated traceability. Every change is listed in Appendix F with its audit finding. All weights, thresholds, algorithm parameters, the 42-feature registry identities and the target rule are unchanged except where Appendix F states otherwise. |

---

# 1. Introduction

## 1.1 Purpose

This Software Requirements Specification defines MuleNetX, a graph-native financial crime intelligence and investigation platform.

MuleNetX combines transactional data, graph relationships, graph analytics, behavioral and temporal signals, machine-learning predictions, explainability, analytical risk scoring, community and ring analysis, bounded money-flow analysis, hypothetical intervention analysis, investigation cases, findings, and a local AI investigation copilot.

This SRS is the implementation contract derived from the finalized README. It is intentionally more precise than the README so that the implementation plan can translate requirements into modules, migrations, services, endpoints, configuration, tests, and deployment steps without redefining the product. Where the README and this SRS differ, this SRS governs; README §38 requirement identifiers are superseded by the identifiers in §30 of this document.

## 1.2 Product Boundary

MuleNetX is an analytical and investigation system. It is **not**:

- an autonomous fraud adjudication engine;
- an authoritative mule-account classifier;
- a law-enforcement decision system;
- a banking core;
- a real-time payment-monitoring system;
- a production SAR filing system;
- an unrestricted AI agent.

The system surfaces evidence, analytical signals, model outputs, and investigation workflow. Human investigators retain responsibility for interpretation and final decisions.

## 1.3 Scope

### MVP in scope

1. Dataset ingestion.
2. Schema validation and normalization.
3. Duplicate detection and invalid-record handling.
4. PostgreSQL persistence.
5. Neo4j graph construction.
6. Graph synchronization, validation, and readiness tracking.
7. Bounded graph exploration.
8. Graph metrics.
9. Community detection.
10. Account-level feature generation.
11. Temporal and behavioral features.
12. Model training and fraud-probability inference.
13. Model metadata and versioning.
14. SHAP explanations.
15. Analytical risk scoring.
16. Risk tiers.
17. Bounded risk propagation.
18. Potential fraud-ring candidate analysis.
19. Bounded money-flow/path analysis.
20. Account investigation workflow.
21. Cases, case subjects, and findings.
22. Authentication and RBAC.
23. Audit events and request correlation.
24. React + D3 dashboard.
25. FastAPI API and background worker.
26. Local Ollama/Qwen copilot.
27. Docker Compose deployment.
28. Unit, integration, API, security, and end-to-end tests.
29. Ring Intelligence, including ring-level features, risk, and evidence.
30. Temporal Behavioral Motifs: rapid pass-through, fan-in, fan-out, circular flow, layered movement, and burst activity.
31. Network Intervention Analysis as bounded hypothetical simulation and decision support only.
32. Multi-Level Evaluation across transaction, account, ring, and network levels.
33. A dataset profiling report produced before analytics (§7.9).

### MVP out of scope

- real-time streaming transaction processing;
- banking-core or SWIFT integration;
- production SAR generation or filing;
- external KYC/SIEM integration;
- authoritative mule-account adjudication;
- autonomous law-enforcement decisions;
- unrestricted cloud LLM processing;
- autonomous AI database agents;
- multi-tenancy;
- enterprise distributed graph infrastructure;
- production AML certification;
- network-scoped (non-ring) intervention scenarios (deferred; §16A.4);
- more than one active dataset per deployment (§1.6, DEC-04).

## 1.4 Intended Audience

Backend engineers, frontend engineers, graph/data engineers, ML engineers, QA engineers, security reviewers, investigators and analysts, project evaluators, and future maintainers.

## 1.5 Normative Language

- **MUST** — mandatory for MVP acceptance.
- **MUST NOT** — prohibited.
- **SHOULD** — expected unless explicitly justified.
- **SHOULD NOT** — normally prohibited unless justified.
- **MAY** — optional and non-blocking.

Requirement identifiers use the prefixes `FR-*` (functional), `SR-*` (security), `AI-*` (copilot), and `NFR-*` (non-functional). Every identifier is listed once in §30 with its normative section. Acceptance tests use `AT-*` identifiers, each unique.

## 1.6 Baseline Decisions

The design audit raised five questions whose answers change implementation. v1.3.3 freezes the recommended default for each. Each default is a configuration or policy choice; changing one requires a new SRS revision and the regression tests named in the row.

| ID | Decision | Frozen default | Rationale | Affected |
|---|---|---|---|---|
| DEC-01 | Reference dataset size and analytics engine | Acceptance runs on the **PaySim reference slice** (§7.1.2: the longest prefix of steps whose cumulative row count is ≤ 1,000,000). Batch graph algorithms run **in-process in Python (NetworkX)** over a projection exported from PostgreSQL in canonical ID order. The full PaySim file is a **benchmark tier** that MAY use the Neo4j Graph Data Science plugin under a distinct `analytics_version`. | Keeps exact betweenness and deterministic Louvain feasible on a workstation; the benchmark tier preserves a scale path. | §7.1, §8, §25, AT-ANALYTICS-* |
| DEC-02 | Product–data fit | A **dataset profiling report** (§7.9) is produced for every dataset before analytics. Synthetic pattern injection is **disabled by default** and MAY be enabled only under §7.10. Ring, motif and intervention capabilities MUST be demonstrated on deterministic fixtures regardless. | PaySim may contain few multi-hop chains; results must be honest about it. | §7.9, §7.10, §27, §28 |
| DEC-03 | Risk-derived features F19, F31, F33, F36, F37 and rules R03–R05 | Feature regime **`RISK_FEATURES_UNAVAILABLE`**: these features are `UNAVAILABLE` at both training and inference, and R03–R05 do not fire, until a later revision introduces a prior-run regime. | Removes the scoring cycle without changing the registry. | §10.2, §11.11, §12.5 |
| DEC-04 | Datasets per deployment | **One active dataset** at a time. Earlier datasets and all their analytical history remain readable through explicit lineage parameters. | Removes cross-dataset ambiguity from every investigator query. | §6.2, §6.9, §19 |
| DEC-05 | Model target semantics | **Retrospective detection**: the label window equals the observation window (§11.4). Forward prediction is out of scope for v1. | Most PaySim accounts have one transaction, so a forward horizon would leave almost every observation unlabelled. | §11 |

## 1.7 Delivery Sequence and Dependency Gates

The MVP scope of §1.3 is unchanged. It is delivered in the order below; each phase starts only when the previous phase's gate passes. Pipeline stages owned by a later phase (§7.6) are implemented as recorded no-op stages until that phase, so the state machine is complete from Phase 1. The copilot is optional throughout and MAY be built any time after Phase 3.

| Phase | Delivers | Gate (acceptance tests, §28.2) |
|---|---|---|
| 1. Foundation | ingestion, profiling, job queue and worker, auth and RBAC, canonical APIs, Neo4j build and activation, Compose deployment | AT-DATA-01..05, AT-GRAPH-01..05, AT-OPS-01, AT-OPS-03, AT-OPS-06, AT-SEC-01..05 |
| 2. Account analytics | graph metrics and communities, features, training, scoring, propagation, SHAP | AT-ANALYTICS-01..02, AT-FEAT-01..04, AT-ML-01..04, AT-RISK-01..06, AT-PROP-01..03, AT-XAI-01, AT-TEMP-01..02, AT-OPS-04 |
| 3. Investigation | dashboard, graph explorer, money flow, cases, subjects, findings | AT-FLOW-01..03, AT-INV-01..06, AT-API-01..02, AT-OPS-02, AT-OPS-05 |
| 4. Rings and motifs | motif detection, candidates, ring features, ring risk, analytical path enumeration | AT-MOTIF-01..05, AT-RING-01..05, AT-FLOW-04 |
| 5. Interventions and evaluation | RANK/EVALUATE simulation, multi-level evaluation | AT-INT-01..10, AT-EVAL-01..03 |
| Copilot (optional, after 3) | AI copilot | AT-AI-01..05 |
| MVP complete | all of the above | AT-E2E-01 |

---

# 2. Stakeholders and Intended Users

| Stakeholder | Responsibility |
|---|---|
| Investigator | Review suspicious accounts and construct evidence-backed investigations. |
| Analyst | Explore data, graph structure, and analytical results. |
| Administrator | Manage access, pipelines, and operational configuration. |
| ML Engineer | Train, evaluate, and version models. |
| Data/Graph Engineer | Maintain ingestion, graph construction, and analytics. |
| Developer | Implement and maintain the platform. |
| QA Engineer | Validate functional, integration, security, and E2E behavior. |
| Evaluator | Assess correctness, rigor, explainability, and engineering quality. |

## 2.1 Investigator

The investigator can search accounts, inspect transactions, view risk and SHAP explanations, explore bounded graph neighborhoods, inspect communities and rings, trace money flows, run hypothetical intervention simulations, create and manage cases, link accounts and transactions to cases, add findings, review ring candidates, and use the copilot.

## 2.2 Analyst

The analyst can inspect analytical data, graph results, risk outputs, temporal behavior, rings, simulations, and investigation information, and can contribute to cases within the limits of §22.2.

## 2.3 Administrator

The administrator can manage users and roles, run and retry pipelines, inspect operational and audit information, and change permitted system configuration.

---

# 3. Product Overview

## 3.1 Core Problem

A transaction-level classifier can identify unusual transactions but provides limited context about the surrounding account network. MuleNetX combines transaction evidence with graph structure, behavioral patterns, temporal signals, model outputs, and explainability to support investigation.

## 3.2 Core Analytical Flow

```text
Transactions
    ↓
Canonical PostgreSQL data
    ↓
Neo4j graph snapshot (derived)
    ↓
Graph analytics + communities + temporal motifs
    ↓
Account features → ML inference → SHAP (on demand)
    ↓
Risk composition → propagation → risk tier
    ↓
Ring candidate extraction → ring features → ring risk → ring evidence
    ↓
Hypothetical intervention simulation (on demand)
    ↓
Investigation (cases, subjects, findings) → local AI copilot
```

This progression does not imply that every community is a ring, every temporal motif is suspicious, or every high-impact intervention candidate should be executed. These are analytical outputs requiring investigator interpretation. The executable stage order is defined by the pipeline state machine in §7.6.

## 3.3 Core Principles

1. Graph-first investigation.
2. Evidence before interpretation.
3. PostgreSQL is canonical for accounts, transactions, and every persisted analytical result.
4. Neo4j is derived, rebuildable analytical state.
5. Risk assessments and other analytical records are immutable.
6. Analytical outputs are versioned and bound to explicit lineage.
7. Interactive graph/path exploration is bounded.
8. AI is local-first and advisory.
9. Security is enforced server-side.
10. Core investigation works without Ollama.
11. Event time and processing time are never compared with each other (§3.4).

## 3.4 Time Model

MuleNetX distinguishes two kinds of time. Mixing them is prohibited.

| Kind | Meaning | Fields |
|---|---|---|
| **Event time** | When a financial event happened in the dataset. | `transactions.timestamp`, `graph_snapshots.data_cutoff`, `scoring_runs.as_of`, `risk_assessments.as_of`, `account_feature_values.as_of`, `temporal_motifs.start_time`/`end_time`, observation cutoff `T` |
| **Processing time** | When MuleNetX computed or recorded something. | every `created_at`, `computed_at`, `generated_at`, `started_at`, `completed_at`, `updated_at` |

Rules:

1. Every cutoff rule ("information ≤ T") compares **event time with event time**.
2. A graph snapshot's `data_cutoff` is the maximum `timestamp` of the transactions it contains. A snapshot is usable for an observation at `T` only if `data_cutoff ≤ T`.
3. A risk assessment's `as_of` equals the `data_cutoff` of the snapshot it was scored on.
4. Processing-time fields are used only for audit, ordering of records with identical lineage, operations, and staleness display.
5. Source timestamps are normalized to UTC before persistence. Dataset adapters that derive timestamps (PaySim `step`) MUST use a fixed, versioned anchor recorded in the adapter configuration and therefore in `pipeline_version` (§7.1.1).
6. Each dataset records its `timestamp_resolution_seconds` (PaySim: 3600). Temporal detectors record in evidence when ordering within that resolution is ambiguous (§15.9.1).

## 3.5 Suspicious-Flow Vocabulary

The following terms are normative wherever they appear. Each is evaluated against exactly one **analytical context** `(graph_snapshot_id, scoring_run_id)`; mixing contexts is prohibited.

| Term | Definition |
|---|---|
| **Account projection** | The directed simple graph whose nodes are accounts and whose edges are the `TRANSFERRED_TO` adjacencies of the snapshot (§6.8). Parallel transactions between an ordered pair form one edge. |
| **Suspicious account** | `is_suspicious_account(a, R)`: TRUE iff account `a` has an assessment in scoring run `R` with `final_score ≥ suspicious_threshold`. Baseline `suspicious_threshold = 0.50` (the HIGH threshold of §12.6), versioned in `risk_logic_versions`. An account with no assessment in `R` is not suspicious. Unavailable risk components do not change this rule: they already contribute 0 to `final_score` (§12.8). |
| **Suspicious transaction** | `is_suspicious_transaction(t, R)`: TRUE iff `t` is in the snapshot of `R` and `is_suspicious_account(t.source, R)` or `is_suspicious_account(t.destination, R)`. This is the only definition: ring features, money-flow quantities, interventions and evaluation all call it. Its only inputs are the scoring run's `final_score` values and the threshold; source fraud labels (`fraud_label`, `isFlaggedFraud`) are never an input. Source labels are used only as the evaluation reference (§28.7) and as the training target (§11.2). |
| **Path** | A directed simple path in the account projection: no account appears twice. Path length counts account-to-account hops. Path identity is the ordered account-ID sequence. |
| **Qualifying path** | A path of length 1 to `analytic_max_depth` (5) whose first and last accounts are both suspicious. |
| **Supporting transactions of a path** | For each hop `(u,v)`, every transaction from `u` to `v` in the snapshot, ordered `(timestamp, transaction_id)`. |
| **Scope** | The set of accounts a ring-level or intervention computation may traverse. **Ring scope** = the ring's members plus every account that lies on a qualifying path having at least one endpoint in the ring. |
| **In-scope qualifying path** | A qualifying path that has at least one endpoint in the ring and lies entirely within ring scope. |
| **Eligible path** | A path of length 1 to `analytic_max_depth` with at least one endpoint in the ring and lying entirely within ring scope (no suspicion requirement on endpoints). |
| **Eligible flow** | The sum of amounts of the unique supporting transactions of all eligible paths. Each transaction is counted once. |
| **Suspicious flow** | The sum of amounts of the unique **suspicious** supporting transactions of all in-scope qualifying paths. Each transaction is counted once. |
| **Suspicious account set (of a scope)** | The suspicious accounts that lie on at least one in-scope qualifying path. |
| **Reachable suspicious pair** | An ordered pair `(s,d)` of distinct suspicious accounts such that at least one in-scope qualifying path starts at `s` and ends at `d`. |

Enumeration of eligible and qualifying paths uses the analytical bounds of §16.7.2, never the interactive bounds.

---

# 4. System Architecture

## 4.1 Logical Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│ React Dashboard (D3 + Zustand + API client)                  │
└──────────────────────────────┬───────────────────────────────┘
                               │ HTTPS JSON
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ FastAPI API process                                          │
│ Auth → Authz → Validation → Application Services             │
└──────────────┬───────────────────────────────┬───────────────┘
               │ enqueue jobs                   │ synchronous reads
               ▼                                ▼
┌──────────────────────────────┐   ┌────────────────────────────┐
│ Worker process (same code)   │──▶│ Domain / Analytical        │
│ pipeline stages, simulations,│   │ Services                   │
│ evaluation                   │   └──┬─────────┬─────────┬─────┘
└──────────────────────────────┘      ▼         ▼         ▼
                                  PostgreSQL   Neo4j   Model artifacts
                                                          + Ollama (AIService only)
```

## 4.2 Dependency Direction

```text
API routes / worker entrypoints
 ↓
Application Services
 ↓
Domain / Analytical Services
 ↓
Repository Interfaces
 ↓
Infrastructure Adapters
 ↓
PostgreSQL / Neo4j / Model Artifacts / Ollama
```

The frontend MUST NOT connect directly to either database. API routes MUST NOT embed analytical algorithms. The AI model MUST NOT have direct database or system execution authority. Only `GraphService` and `AnalyticsService` hold a Neo4j driver. Only `AIService` calls Ollama.

## 4.3 Logical Services

The MVP uses logical service boundaries inside one codebase; they are not separately deployed microservices.

```text
IngestionService        ProfilingService        JobService
AccountService          TransactionService      GraphService
AnalyticsService        TemporalMotifService    FeatureService
MLService               ExplainabilityService   RiskService
PropagationService      MoneyFlowService        RingIntelligenceService
InterventionService     EvaluationService       InvestigationService
AIService               AuditService            AuthService
```

## 4.4 Process Model

The backend image runs as two processes in two Compose services:

- **`backend`** serves the API. It never runs pipeline stages, training, simulations, or evaluation inline; it enqueues them as jobs (§7.8).
- **`worker`** claims and executes jobs. It runs the same codebase with a different entrypoint.

No additional broker, queue, or scheduler is introduced; the job queue is a PostgreSQL table.

## 4.5 Architecture Invariants

The implementation MUST preserve:

1. PostgreSQL ownership of canonical accounts, transactions, and persisted analytical results.
2. Neo4j as derived, rebuildable graph representation.
3. Stable, dataset-namespaced canonical IDs across stores.
4. Server-enforced graph/path bounds.
5. Immutable risk assessments and analytical records.
6. Explicit analytical staleness.
7. Versioned model/feature/analytics/risk logic.
8. Server-side authorization.
9. AI isolation from protected resources.
10. Core investigation availability without Ollama.
11. The event-time/processing-time separation of §3.4.
12. An acyclic analytical stage order (§7.6).

The complete invariant list is Appendix C.

---

# 5. Canonical Domain Model

This section defines each entity's meaning and lifecycle. Field-level definitions (types, nullability, constraints, indexes) appear **only** in §6.3, which is normative; §5 does not repeat field lists.

## 5.1 Entity Inventory

| Group | Entities |
|---|---|
| Canonical financial entities | Account, Transaction |
| Investigation entities | Case, CaseSubject, Finding, AuditEvent, User, AuthSession |
| Pipeline and lineage metadata | Dataset, DatasetProfile, IngestionRun, PipelineRun, Job, GraphSnapshot, AnalyticsRun, FeatureVersion, ModelVersion, RiskLogicVersion, ScoringRun, ActiveContext |
| Account-level analytical records | AccountGraphMetrics, AccountFeatureValues, RiskAssessment, PropagationContribution, ShapExplanation |
| Community and ring records | Community, CommunityMembership, PotentialFraudRingCandidate, RingMembership, RingFeatureSet, RingRiskAssessment |
| Uniqueness analytical records | TemporalMotif, InterventionScenario, InterventionCandidate, EvaluationRun, EvaluationMetric |

All analytical records are derived state. They MUST retain lineage to the graph snapshot, scoring run, and configuration versions that produced them, and MUST NOT become competing sources of truth for canonical accounts or transactions. Metadata entities support reproducibility and MUST NOT be confused with canonical financial entities.

## 5.2 Account

An account is an entity participating in transactions within one dataset. Its identity is `account_id`, namespaced by dataset (§6.2). Canonical fields are immutable. `risk_score`, `risk_tier`, `community_id`, and `latest_risk_assessment_id` are a **current projection** maintained from the active scoring run (§6.9); they are never an independent source of truth.

## 5.3 Transaction

A transaction is one source-dataset financial event between two accounts of the same dataset. Canonical transaction rows are immutable after ingestion. A correction requires a new dataset version. `fraud_label` preserves the source dataset's label semantics; it is not a mule-account label.

## 5.4 RiskAssessment

A RiskAssessment is an immutable analytical snapshot for one account, produced by exactly one ScoringRun. Its score fields follow the canonical terminology of §12.10. All score fields are in `[0,1]`. `as_of` is event time (§3.4).

## 5.5 Community

A community is a graph-structural grouping produced by community detection on one graph snapshot. Community membership is an analytical result and does not imply criminal activity. `community_id` is deterministic (§6.2.3).

## 5.6 Potential Fraud Ring Candidate and Ring

A **candidate** is a community scored by §9.2 with `candidate_score ≥ 0.50`. Candidates carry a class: `SUSPICIOUS_COMMUNITY` (0.50 ≤ score < 0.70) or `POTENTIAL_FRAUD_RING_CANDIDATE` (score ≥ 0.70). A candidate MUST NOT be represented as a confirmed criminal organization.

A candidate of class `POTENTIAL_FRAUD_RING_CANDIDATE` is processed by Ring Intelligence (§9A) and is then called a **ring**. The ring is the same record: `ring_id` is `candidate_id`. A separate ring entity MUST NOT be introduced. Ring members are defined in §9A.2. Ring features and ring risk are immutable snapshots associated with the candidate. The candidate's workflow status (`CANDIDATE`, `REVIEWED`, `DISMISSED`) is the only mutable field and does not alter any score.

## 5.7 Case and CaseSubject

A case groups an investigation. Its status follows the state machine in §17.2. A **CaseSubject** links a case to an account, transaction, ring, or intervention scenario under investigation. Subjects can be added and removed; every change is audited.

## 5.8 Finding

A finding is an investigator-authored, append-only record attached to a case. Evidence SHOULD reference stable identifiers: transaction, account, risk assessment, graph snapshot, SHAP explanation, motif, community, ring, path, or scenario identifiers.

## 5.9 AuditEvent

An append-only record of a security-relevant or investigative action. Sensitive metadata MUST be minimized (§24.3).

## 5.10 Dataset and DatasetProfile

A dataset is one immutable source file normalized under one adapter configuration. A changed source file or a changed normalization is a new dataset version. Each dataset has a short unique `dataset_key` used to namespace canonical identifiers. A DatasetProfile is the profiling report of §7.9.

## 5.11 IngestionRun, PipelineRun, and Job

An IngestionRun records loading one dataset. A PipelineRun records progress of one dataset through the state machine of §7.6. A Job is one unit of background work claimed by the worker (§7.8).

## 5.12 GraphSnapshot and AnalyticsRun

A GraphSnapshot is one immutable build of the account/transaction graph in Neo4j, with an event-time `data_cutoff` (§3.4). An AnalyticsRun records one execution of the graph algorithms and motif detectors on one snapshot.

## 5.13 FeatureVersion, ModelVersion, RiskLogicVersion

Versioned definitions. A FeatureVersion is identified by the hash of the serialized feature registry. A ModelVersion records a trained artifact with its target definition, feature version, feature regime, splits, and metrics. A RiskLogicVersion records every weight, normalization reference, rule, tier threshold, and propagation parameter.

## 5.14 ScoringRun and ActiveContext

A ScoringRun is one execution of feature generation, inference, risk composition, and propagation for one graph snapshot with one model version and one risk logic version. Every RiskAssessment, PropagationContribution, and every downstream ring record references exactly one scoring run.

The ActiveContext is the single row per deployment that names the active dataset, graph snapshot, analytics run, scoring run, model version, and risk logic version. API defaults and staleness (§19.12) are computed against it.

## 5.15 TemporalMotif

A detected behavioral pattern instance of type `RAPID_PASS_THROUGH`, `FAN_IN`, `FAN_OUT`, `CIRCULAR_FLOW`, `LAYERED_MOVEMENT`, or `BURST_ACTIVITY`. `motif_confidence` is a deterministic pattern-strength score and MUST NOT be described as a probability of criminality.

## 5.16 InterventionScenario and InterventionCandidate

An InterventionScenario is one hypothetical simulation against an immutable baseline (§16A). It runs in mode `RANK` (generate and rank single-target candidates) or `EVALUATE` (score one user-specified intervention). An InterventionCandidate is one evaluated hypothetical action within a scenario. Scenarios MUST NOT mutate canonical financial or operational state.

## 5.17 EvaluationRun and EvaluationMetric

An EvaluationRun records one execution of Multi-Level Evaluation (§28.7) with its reference-set construction version and lineage. EvaluationMetrics are its immutable results per level.

---

# 6. Data Architecture

## 6.1 Source-of-Truth Matrix

| Data | PostgreSQL | Neo4j | Authority |
|---|---|---|---|
| Accounts, transactions | Canonical | Derived copy per snapshot | PostgreSQL |
| Dataset, ingestion, pipeline, job metadata | Canonical | — | PostgreSQL |
| Graph topology | Snapshot metadata | Primary traversal representation | Neo4j for traversal; rebuildable from PostgreSQL |
| Graph metrics, communities, motifs | Canonical analytical results | MAY cache as node properties | PostgreSQL |
| Features, risk assessments, propagation, SHAP | Canonical analytical results | — | PostgreSQL |
| Rings, ring features, ring risk | Canonical analytical results | — | PostgreSQL |
| Intervention scenarios and candidates | Canonical analytical results | — | PostgreSQL |
| Evaluation results | Canonical analytical results | — | PostgreSQL |
| Cases, subjects, findings, audit, users, sessions | Canonical | — | PostgreSQL |
| Feature, model, risk-logic definitions | Canonical metadata | — | PostgreSQL |
| Model artifacts | Content hash and reference | — | Artifact volume |

Neo4j holds nothing that cannot be rebuilt from PostgreSQL.

## 6.2 Canonical Identity Contract

### 6.2.1 Canonical identifiers

`account_id` and `transaction_id` are immutable domain identifiers owned by PostgreSQL and **namespaced by dataset**:

```text
account_id     = "{dataset_key}:{source_account_ref}"
transaction_id = "{dataset_key}:{source_transaction_ref}"
```

- `dataset_key` is the dataset's short unique key (`[a-z0-9_-]{1,24}`).
- `source_account_ref` is the account identifier in the source file (PaySim: `nameOrig`/`nameDest`).
- `source_transaction_ref` is the source file's transaction identifier. If the source has none (PaySim), it is the 1-based **row ordinal** in the source file, zero-padded to 10 digits so that lexicographic and numeric order agree.
- Neo4j MUST store the same values as properties. Neo4j internal element IDs MUST NOT be exposed as domain identifiers.
- The UI displays `source_account_ref`/`source_transaction_ref`; APIs accept and return canonical IDs.

### 6.2.2 Account type derivation

`account_type` comes from the dataset adapter. For PaySim: names beginning `C` → `CUSTOMER`; names beginning `M` → `MERCHANT`; any other prefix rejects the row.

### 6.2.3 Deterministic analytical identifiers

Wherever an identifier participates in ordering, tie-breaking, or "stable identity", it MUST be a UUIDv5 under the fixed namespace UUID `6f1c2a3e-5b7d-4e0a-9c1f-2d8b4a6e0f13` over the canonical content string below (fields joined with `|`, lists sorted ascending and joined with `,`):

| Identifier | Content string |
|---|---|
| `community_id` | `community\|{graph_snapshot_id}\|{analytics_version}\|{sorted member account_ids}` |
| `candidate_id` (= `ring_id`) | `candidate\|{graph_snapshot_id}\|{scoring_run_id}\|{community_id}` |
| `motif_id` | `motif\|{graph_snapshot_id}\|{analytics_version}\|{motif_type}\|{temporal_window_seconds}\|{sorted transaction_ids}` |
| `path_id` | `path\|{graph_snapshot_id}\|{ordered account_ids}` |
| `intervention_candidates.candidate_id` | `intervention\|{baseline_graph_snapshot_id}\|{scoring_run_id}\|{target_ring_id}\|{operation_type}\|{sorted target_ids}\|{ranking_configuration_hash}` |
| `reference_ring_id` | `refring\|{reference_construction_version}\|{sorted member account_ids}` |

`community_id` is stored as text of the UUID. Other identifiers are stored as `UUID`. Primary keys of purely administrative records (users, cases, findings, audit events, jobs, runs, scenarios) MAY be random UUIDv4.

## 6.3 PostgreSQL Physical Schema

The following schema is normative for the MVP. SQL syntax may vary, but types, nullability, constraints, indexes, and semantics MUST remain equivalent. "Imm." means immutable after insert. All timestamps are `TIMESTAMPTZ` in UTC. Every `*_version` column referencing a version table is a foreign key unless marked otherwise.

### 6.3.1 Identity and access

#### `users`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| user_id | UUID | No | PK | Imm. |
| username | VARCHAR(100) | No | UNIQUE, non-empty | Imm. |
| password_hash | TEXT | No | Argon2id encoded hash | Yes |
| role | VARCHAR(20) | No | CHECK ADMIN/INVESTIGATOR/ANALYST | Yes |
| is_active | BOOLEAN | No | DEFAULT TRUE | Yes |
| created_at | TIMESTAMPTZ | No | DEFAULT now() | Imm. |
| updated_at | TIMESTAMPTZ | No | — | Yes |
| last_login_at | TIMESTAMPTZ | Yes | — | Yes |

Indexes: unique `username`; `(role, is_active)`. Users are never physically deleted; deactivate with `is_active = false`. Deactivation and role change revoke all sessions of that user in the same transaction.

#### `auth_sessions`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| session_id | UUID | No | PK | Imm. |
| token_hash | CHAR(64) | No | UNIQUE; SHA-256 of the opaque token | Imm. |
| user_id | UUID | No | FK users | Imm. |
| role_at_issue | VARCHAR(20) | No | role when issued | Imm. |
| created_at | TIMESTAMPTZ | No | — | Imm. |
| last_seen_at | TIMESTAMPTZ | No | — | Yes |
| idle_expires_at | TIMESTAMPTZ | No | — | Yes |
| absolute_expires_at | TIMESTAMPTZ | No | — | Imm. |
| revoked_at | TIMESTAMPTZ | Yes | terminal | Yes, once |
| revocation_reason | VARCHAR(30) | Yes | LOGOUT/DEACTIVATED/ROLE_CHANGED/ADMIN/EXPIRED | Yes, once |

Indexes: unique `token_hash`; `(user_id, revoked_at)`. The plaintext token is never stored or logged.

### 6.3.2 Canonical financial data

#### `datasets`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| dataset_id | UUID | No | PK | Imm. |
| dataset_key | VARCHAR(24) | No | UNIQUE, `[a-z0-9_-]{1,24}` | Imm. |
| name | VARCHAR(200) | No | non-empty | Imm. |
| source | VARCHAR(100) | No | non-empty | Imm. |
| dataset_version | VARCHAR(100) | No | UNIQUE(name, dataset_version) | Imm. |
| schema_version | VARCHAR(50) | No | — | Imm. |
| adapter | VARCHAR(50) | No | e.g. `paysim-v1` | Imm. |
| adapter_config | JSONB | No | includes epoch anchor, slice rule, synthetic flag | Imm. |
| checksum | CHAR(64) | No | SHA-256 of source file; UNIQUE(checksum, dataset_version) | Imm. |
| timestamp_resolution_seconds | INTEGER | No | CHECK > 0 | Imm. |
| is_synthetic_injection | BOOLEAN | No | DEFAULT FALSE (§7.10) | Imm. |
| record_count | BIGINT | Yes | CHECK ≥ 0 | Set once at ingestion success |
| created_at | TIMESTAMPTZ | No | DEFAULT now() | Imm. |

A changed source file or adapter configuration is a new dataset version.

#### `accounts`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| account_id | VARCHAR(160) | No | PK; namespaced (§6.2) | Imm. |
| dataset_id | UUID | No | FK datasets | Imm. |
| source_account_ref | VARCHAR(128) | No | non-empty; UNIQUE(dataset_id, source_account_ref) | Imm. |
| account_type | VARCHAR(50) | No | non-empty (§6.2.2) | Imm. |
| created_at | TIMESTAMPTZ | Yes | source value if provided | Imm. |
| risk_score | NUMERIC(8,7) | Yes | CHECK 0 ≤ x ≤ 1; projection | Projection |
| risk_tier | VARCHAR(20) | Yes | CHECK LOW/MEDIUM/HIGH/CRITICAL; projection | Projection |
| community_id | VARCHAR(64) | Yes | projection | Projection |
| latest_risk_assessment_id | UUID | Yes | FK risk_assessments; projection | Projection |

No normal application operation physically deletes an account. Projection columns are written only by the projection update of §6.9. Indexes: PK; `(dataset_id, risk_tier, risk_score DESC)`; `(dataset_id, community_id)`; `(dataset_id, source_account_ref)`; `source_account_ref text_pattern_ops` for prefix search.

#### `transactions`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| transaction_id | VARCHAR(160) | No | PK; namespaced (§6.2) | Imm. |
| dataset_id | UUID | No | FK datasets | Imm. |
| ingestion_run_id | UUID | No | FK ingestion_runs | Imm. |
| source_transaction_ref | VARCHAR(128) | No | UNIQUE(dataset_id, source_transaction_ref) | Imm. |
| source_account_id | VARCHAR(160) | No | FK accounts; same dataset | Imm. |
| destination_account_id | VARCHAR(160) | No | FK accounts; same dataset | Imm. |
| amount | NUMERIC(20,6) | No | CHECK amount ≥ 0 | Imm. |
| timestamp | TIMESTAMPTZ | No | UTC event time | Imm. |
| transaction_type | VARCHAR(50) | No | non-empty | Imm. |
| fraud_label | BOOLEAN | Yes | source semantics | Imm. |
| source_record_hash | CHAR(64) | No | SHA-256 of normalized source row | Imm. |

Canonical transaction rows are immutable. Indexes: PK; `(source_account_id, timestamp DESC, transaction_id)`; `(destination_account_id, timestamp DESC, transaction_id)`; `(dataset_id, timestamp, transaction_id)`; `(ingestion_run_id)`; `(dataset_id, source_record_hash)`.

### 6.3.3 Pipeline and lineage

#### `dataset_profiles`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| dataset_id | UUID | No | PK, FK datasets | Imm. |
| profile_version | VARCHAR(50) | No | — | Imm. |
| metrics | JSONB | No | the metrics listed in §7.9 | Imm. |
| created_at | TIMESTAMPTZ | No | — | Imm. |

#### `ingestion_runs`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| ingestion_run_id | UUID | No | PK | Imm. |
| dataset_id | UUID | No | FK datasets | Imm. |
| pipeline_version | VARCHAR(100) | No | — | Imm. |
| started_at | TIMESTAMPTZ | No | — | Imm. |
| completed_at | TIMESTAMPTZ | Yes | terminal only | Once |
| status | VARCHAR(20) | No | CHECK CREATED/RUNNING/SUCCEEDED/FAILED | State only |
| records_seen | BIGINT | No | CHECK ≥ 0 | Until terminal |
| records_accepted | BIGINT | No | CHECK ≥ 0 | Until terminal |
| records_rejected | BIGINT | No | CHECK ≥ 0 | Until terminal |
| records_duplicate | BIGINT | No | CHECK ≥ 0 | Until terminal |
| rejection_summary | JSONB | No | reason code → count, plus ≤ 100 sample row ordinals | Until terminal |
| error_summary | TEXT | Yes | safe; no secrets | Until terminal |

Indexes: `(dataset_id, started_at DESC)`; `(status, started_at DESC)`.

#### `pipeline_runs`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| pipeline_run_id | UUID | No | PK | Imm. |
| dataset_id | UUID | No | FK datasets | Imm. |
| ingestion_run_id | UUID | Yes | FK ingestion_runs | Set once |
| current_state | VARCHAR(30) | No | CHECK states of §7.6 | State machine |
| graph_snapshot_id | UUID | Yes | FK graph_snapshots | Set once |
| analytics_run_id | UUID | Yes | FK analytics_runs | Set once |
| scoring_run_id | UUID | Yes | FK scoring_runs | Set once |
| model_version | VARCHAR(100) | Yes | FK model_versions | Set once |
| started_at | TIMESTAMPTZ | No | — | Imm. |
| updated_at | TIMESTAMPTZ | No | — | Yes |
| completed_at | TIMESTAMPTZ | Yes | terminal only | Once |
| failure_stage | VARCHAR(30) | Yes | failure only | Failure only |
| failure_category | VARCHAR(50) | Yes | failure only | Failure only |
| safe_failure_message | TEXT | Yes | no secrets | Failure only |
| resumable_from | VARCHAR(30) | Yes | stage to resume at | Failure only |

Indexes: `(dataset_id, started_at DESC)`; `(current_state, updated_at DESC)`.

#### `jobs`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| job_id | UUID | No | PK | Imm. |
| kind | VARCHAR(40) | No | CHECK kinds of §7.8 | Imm. |
| payload | JSONB | No | stage inputs (IDs only) | Imm. |
| status | VARCHAR(20) | No | CHECK QUEUED/RUNNING/SUCCEEDED/FAILED/CANCELLED | State only |
| lock_key | BIGINT | Yes | advisory lock key (§7.8) | Imm. |
| attempts | INTEGER | No | CHECK ≥ 0 | Yes |
| max_attempts | INTEGER | No | CHECK ≥ 1 | Imm. |
| lease_owner | VARCHAR(100) | Yes | worker identity | Yes |
| lease_expires_at | TIMESTAMPTZ | Yes | — | Yes |
| requested_by | UUID | Yes | FK users | Imm. |
| request_id | VARCHAR(100) | Yes | correlation | Imm. |
| created_at | TIMESTAMPTZ | No | — | Imm. |
| started_at | TIMESTAMPTZ | Yes | — | Yes |
| completed_at | TIMESTAMPTZ | Yes | — | Once |
| failure_category | VARCHAR(40) | Yes | e.g. LEASE_EXPIRED, TIMEOUT, LIMIT_EXCEEDED, DEPENDENCY_UNAVAILABLE, INTERNAL | Yes |
| error_summary | TEXT | Yes | safe; latest failure of any attempt | Yes |

Indexes: `(status, created_at)`; `(kind, status)`; `(lease_expires_at) WHERE status = 'RUNNING'`.

#### `graph_snapshots`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| graph_snapshot_id | UUID | No | PK | Imm. |
| dataset_id | UUID | No | FK datasets | Imm. |
| ingestion_run_id | UUID | No | FK ingestion_runs | Imm. |
| purpose | VARCHAR(20) | No | CHECK OPERATIONAL/TRAINING_SPLIT | Imm. |
| data_cutoff | TIMESTAMPTZ | No | event time; max included `timestamp` | Imm. |
| pipeline_version | VARCHAR(100) | No | — | Imm. |
| graph_schema_version | VARCHAR(50) | No | — | Imm. |
| source_record_count | BIGINT | No | CHECK ≥ 0 | Imm. |
| node_count | BIGINT | Yes | CHECK ≥ 0; set at validation | Once |
| edge_count | BIGINT | Yes | CHECK ≥ 0; set at validation | Once |
| validation_digest | CHAR(64) | Yes | §6.8.4 | Once |
| status | VARCHAR(20) | No | CHECK BUILDING/VALIDATING/READY/FAILED/RETIRED | State only |
| created_at | TIMESTAMPTZ | No | — | Imm. |
| ready_at | TIMESTAMPTZ | Yes | — | Once |

Indexes: `(dataset_id, purpose, data_cutoff DESC)`; `(status)`.

#### `analytics_runs`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| analytics_run_id | UUID | No | PK | Imm. |
| graph_snapshot_id | UUID | No | FK graph_snapshots | Imm. |
| analytics_version | VARCHAR(100) | No | — | Imm. |
| engine | VARCHAR(30) | No | CHECK NETWORKX/NEO4J_GDS | Imm. |
| algorithm_configuration | JSONB | No | all §8 parameters, seeds, library versions | Imm. |
| started_at | TIMESTAMPTZ | No | — | Imm. |
| completed_at | TIMESTAMPTZ | Yes | terminal only | Once |
| status | VARCHAR(20) | No | CHECK RUNNING/SUCCEEDED/FAILED | State only |
| error_summary | TEXT | Yes | safe | Failure only |

Indexes: `(graph_snapshot_id, started_at DESC)`; `(status)`.

#### `feature_versions`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| feature_version | VARCHAR(100) | No | PK | Imm. |
| definition_hash | CHAR(64) | No | UNIQUE | Imm. |
| feature_count | INTEGER | No | CHECK > 0 (v1: 42) | Imm. |
| feature_registry_reference | TEXT | No | path of registry file in repository | Imm. |
| created_at | TIMESTAMPTZ | No | — | Imm. |

#### `model_versions`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| model_version | VARCHAR(100) | No | PK | Imm. |
| model_type | VARCHAR(100) | No | — | Imm. |
| target_definition | JSONB | No | §11.4 fields | Imm. |
| feature_version | VARCHAR(100) | No | FK feature_versions | Imm. |
| feature_regime | VARCHAR(40) | No | CHECK RISK_FEATURES_UNAVAILABLE (§10.2) | Imm. |
| training_dataset_id | UUID | No | FK datasets | Imm. |
| training_snapshot_ids | JSONB | No | train/validation/test snapshot IDs | Imm. |
| split_boundaries | JSONB | No | T_train, T_val, T_test | Imm. |
| training_config | JSONB | No | hyperparameters, class weight | Imm. |
| class_distribution | JSONB | No | per split | Imm. |
| evaluation_metrics | JSONB | No | §11.10 | Imm. |
| operating_threshold | NUMERIC(8,7) | No | CHECK 0 ≤ x ≤ 1 | Imm. |
| artifact_reference | TEXT | No | path on artifact volume | Imm. |
| artifact_sha256 | CHAR(64) | No | verified at load | Imm. |
| implementation_version | VARCHAR(100) | No | library/runtime versions | Imm. |
| random_seed | INTEGER | No | — | Imm. |
| created_at | TIMESTAMPTZ | No | — | Imm. |

Indexes: `(feature_version)`; `(created_at DESC)`.

#### `risk_logic_versions`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| risk_logic_version | VARCHAR(100) | No | PK | Imm. |
| formula_identifier | VARCHAR(100) | No | `weighted-normalized-v1` | Imm. |
| configuration | JSONB | No | weights, component feature sets, normalization methods (§12.2–12.3) | Imm. |
| normalization_reference | JSONB | No | quantile tables and medians (§12.2) | Imm. |
| rules | JSONB | No | §12.5 | Imm. |
| tier_thresholds | JSONB | No | §12.6 | Imm. |
| propagation_parameters | JSONB | No | §13.2 | Imm. |
| ring_parameters | JSONB | No | §9.2, §9A.3 weights and thresholds | Imm. |
| created_at | TIMESTAMPTZ | No | — | Imm. |

#### `scoring_runs`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| scoring_run_id | UUID | No | PK | Imm. |
| graph_snapshot_id | UUID | No | FK graph_snapshots | Imm. |
| analytics_run_id | UUID | No | FK analytics_runs | Imm. |
| as_of | TIMESTAMPTZ | No | = snapshot `data_cutoff` | Imm. |
| feature_version | VARCHAR(100) | No | FK | Imm. |
| feature_snapshot_id | UUID | No | groups `account_feature_values` | Imm. |
| model_version | VARCHAR(100) | Yes | FK; NULL only when ML unavailable | Imm. |
| risk_logic_version | VARCHAR(100) | No | FK | Imm. |
| started_at | TIMESTAMPTZ | No | — | Imm. |
| completed_at | TIMESTAMPTZ | Yes | terminal only | Once |
| status | VARCHAR(20) | No | CHECK RUNNING/SUCCEEDED/FAILED | State only |
| accounts_scored | BIGINT | Yes | CHECK ≥ 0 | Once |

Indexes: `(graph_snapshot_id, started_at DESC)`; `(status)`.

#### `active_context`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| singleton | BOOLEAN | No | PK, CHECK singleton = TRUE | Imm. |
| dataset_id | UUID | Yes | FK datasets | Yes |
| graph_snapshot_id | UUID | Yes | FK graph_snapshots | Yes |
| analytics_run_id | UUID | Yes | FK analytics_runs | Yes |
| scoring_run_id | UUID | Yes | FK scoring_runs | Yes |
| model_version | VARCHAR(100) | Yes | FK model_versions | Yes |
| risk_logic_version | VARCHAR(100) | Yes | FK risk_logic_versions | Yes |
| updated_at | TIMESTAMPTZ | No | — | Yes |
| updated_by_pipeline_run_id | UUID | Yes | FK pipeline_runs | Yes |

Exactly one row. Updated only by the activation step of §6.9 in a single transaction.

### 6.3.4 Account-level analytical results

#### `account_graph_metrics`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| analytics_run_id | UUID | No | FK analytics_runs | Imm. |
| account_id | VARCHAR(160) | No | FK accounts | Imm. |
| degree | INTEGER | No | CHECK ≥ 0 | Imm. |
| in_degree | INTEGER | No | CHECK ≥ 0 | Imm. |
| out_degree | INTEGER | No | CHECK ≥ 0 | Imm. |
| pagerank_raw | DOUBLE PRECISION | No | — | Imm. |
| pagerank_norm | NUMERIC(8,7) | No | CHECK 0 ≤ x ≤ 1 | Imm. |
| betweenness_raw | DOUBLE PRECISION | No | algorithm-normalized | Imm. |
| component_id | VARCHAR(64) | No | deterministic: min account_id in component | Imm. |
| component_size | INTEGER | No | CHECK ≥ 1 | Imm. |
| community_id | VARCHAR(64) | No | composite FK `(analytics_run_id, community_id)` → communities | Imm. |
| community_size | INTEGER | No | CHECK ≥ 1 | Imm. |

PK: `(analytics_run_id, account_id)`. Index: `(account_id, analytics_run_id)`.

#### `account_feature_values`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| feature_snapshot_id | UUID | No | groups one generation | Imm. |
| account_id | VARCHAR(160) | No | FK accounts | Imm. |
| as_of | TIMESTAMPTZ | No | observation cutoff `T` (event time) | Imm. |
| feature_version | VARCHAR(100) | No | FK feature_versions | Imm. |
| graph_snapshot_id | UUID | No | FK graph_snapshots; `data_cutoff ≤ as_of` | Imm. |
| analytics_run_id | UUID | No | FK analytics_runs | Imm. |
| feature_values | DOUBLE PRECISION[] | No | length = feature_count, registry order; NaN for UNAVAILABLE/NOT_APPLICABLE | Imm. |
| feature_states | SMALLINT[] | No | same length; 0 OBSERVED, 1 ZERO, 2 UNAVAILABLE, 3 NOT_APPLICABLE | Imm. |
| created_at | TIMESTAMPTZ | No | — | Imm. |

PK: `(feature_snapshot_id, account_id)`. Index: `(account_id, as_of DESC)`.

#### `risk_assessments`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| assessment_id | UUID | No | PK | Imm. |
| scoring_run_id | UUID | No | FK scoring_runs | Imm. |
| account_id | VARCHAR(160) | No | FK accounts | Imm. |
| as_of | TIMESTAMPTZ | No | = scoring run `as_of` | Imm. |
| graph_snapshot_id | UUID | No | FK graph_snapshots | Imm. |
| feature_snapshot_id | UUID | No | with account_id, FK account_feature_values | Imm. |
| model_version | VARCHAR(100) | Yes | FK; NULL when ML unavailable | Imm. |
| feature_version | VARCHAR(100) | No | FK | Imm. |
| analytics_version | VARCHAR(100) | No | — | Imm. |
| risk_logic_version | VARCHAR(100) | No | FK | Imm. |
| ml_score | NUMERIC(8,7) | Yes | CHECK 0 ≤ x ≤ 1; NULL when unavailable | Imm. |
| graph_signal_score | NUMERIC(8,7) | No | CHECK 0 ≤ x ≤ 1 | Imm. |
| behavioral_signal_score | NUMERIC(8,7) | No | CHECK 0 ≤ x ≤ 1 | Imm. |
| rule_signal_score | NUMERIC(8,7) | No | CHECK 0 ≤ x ≤ 1 | Imm. |
| pre_propagation_score | NUMERIC(8,7) | No | CHECK 0 ≤ x ≤ 1 (§12.4) | Imm. |
| propagated_risk | NUMERIC(8,7) | No | CHECK 0 ≤ x ≤ 0.5 | Imm. |
| final_score | NUMERIC(8,7) | No | CHECK 0 ≤ x ≤ 1 | Imm. |
| risk_tier | VARCHAR(20) | No | CHECK tier | Imm. |
| signal_availability | JSONB | No | per component: AVAILABLE/UNAVAILABLE plus reasons | Imm. |
| fired_rules | JSONB | No | ordered rule IDs with contributions | Imm. |
| generated_at | TIMESTAMPTZ | No | processing time | Imm. |

UNIQUE: `(scoring_run_id, account_id)`. Indexes: `(account_id, as_of DESC, generated_at DESC)`; `(scoring_run_id, risk_tier, final_score DESC)`; `(model_version)`.

#### `propagation_contributions`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| scoring_run_id | UUID | No | FK scoring_runs | Imm. |
| account_id | VARCHAR(160) | No | receiving account | Imm. |
| source_account_id | VARCHAR(160) | No | FK accounts | Imm. |
| source_assessment_id | UUID | No | FK risk_assessments | Imm. |
| distance | SMALLINT | No | CHECK 1..3 | Imm. |
| source_score | NUMERIC(8,7) | No | source `pre_propagation_score` | Imm. |
| decay_value | NUMERIC(8,7) | No | 1/(1+distance) | Imm. |
| contribution | NUMERIC(8,7) | No | CHECK 0 ≤ x ≤ 0.5 | Imm. |
| rank | SMALLINT | No | 1 = winning source | Imm. |

PK: `(scoring_run_id, account_id, rank)`. At most `propagation_provenance_top_n` (default 5) rows per receiving account; rank 1 is the source that determined `propagated_risk`.

#### `shap_explanations`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| assessment_id | UUID | No | PK, FK risk_assessments | Imm. |
| model_version | VARCHAR(100) | No | must equal the assessment's | Imm. |
| feature_version | VARCHAR(100) | No | must equal the assessment's | Imm. |
| explainer | VARCHAR(50) | No | `tree_shap_interventional` or `tree_shap_path_dependent`, frozen per model | Imm. |
| base_value | DOUBLE PRECISION | No | in model output space | Imm. |
| output_space | VARCHAR(20) | No | CHECK LOG_ODDS/PROBABILITY | Imm. |
| contributions | JSONB | No | 42 entries: feature id, name, value, state, shap, direction | Imm. |
| computed_at | TIMESTAMPTZ | No | — | Imm. |

Rows are computed on first request (§14.2) and are an immutable cache.

### 6.3.5 Communities and rings

#### `communities`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| community_id | VARCHAR(64) | No | deterministic (§6.2.3) | Imm. |
| analytics_run_id | UUID | No | FK analytics_runs | Imm. |
| graph_snapshot_id | UUID | No | FK graph_snapshots | Imm. |
| algorithm | VARCHAR(100) | No | — | Imm. |
| algorithm_version | VARCHAR(100) | No | — | Imm. |
| member_count | INTEGER | No | CHECK ≥ 1 | Imm. |
| computed_at | TIMESTAMPTZ | No | — | Imm. |
| analytical_summary | JSONB | Yes | — | Imm. |

PK: `(analytics_run_id, community_id)`. Index: `(graph_snapshot_id)`.

`community_id` is unique only within an analytics run: two runs over the same snapshot with the same analytics version produce the same `community_id`. Every reference to a community is therefore the composite `(analytics_run_id, community_id)`; no table references `community_id` alone. The analytics run (not the snapshot) is the identity scope because one snapshot can carry several analytics runs, and the run determines the snapshot.

#### `community_memberships`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| analytics_run_id | UUID | No | FK analytics_runs | Imm. |
| community_id | VARCHAR(64) | No | composite FK `(analytics_run_id, community_id)` → communities | Imm. |
| account_id | VARCHAR(160) | No | FK accounts | Imm. |
| membership_score | NUMERIC(12,8) | Yes | algorithm-specific | Imm. |

PK: `(analytics_run_id, community_id, account_id)`. Index: `(account_id, analytics_run_id)`.

#### `potential_fraud_ring_candidates`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| candidate_id | UUID | No | PK; deterministic (§6.2.3); also `ring_id` | Imm. |
| community_id | VARCHAR(64) | No | composite FK `(analytics_run_id, community_id)` → communities | Imm. |
| analytics_run_id | UUID | No | FK analytics_runs | Imm. |
| graph_snapshot_id | UUID | No | FK graph_snapshots | Imm. |
| scoring_run_id | UUID | No | FK scoring_runs | Imm. |
| candidate_score | NUMERIC(8,7) | No | CHECK 0.5 ≤ x ≤ 1 | Imm. |
| candidate_class | VARCHAR(40) | No | CHECK SUSPICIOUS_COMMUNITY/POTENTIAL_FRAUD_RING_CANDIDATE | Imm. |
| signal_summary | JSONB | No | H, D, C, community_temporal_density, M, with availability | Imm. |
| candidate_status | VARCHAR(20) | No | CHECK CANDIDATE/REVIEWED/DISMISSED | Status only |
| status_changed_by | UUID | Yes | FK users | Status only |
| status_changed_at | TIMESTAMPTZ | Yes | — | Status only |
| analytics_version | VARCHAR(100) | No | — | Imm. |
| risk_logic_version | VARCHAR(100) | No | FK | Imm. |
| created_at | TIMESTAMPTZ | No | — | Imm. |

UNIQUE `(scoring_run_id, analytics_run_id, community_id)`: at most one candidate per community per scoring run. Candidate generation is idempotent: a rerun of the same scoring run derives the same `candidate_id` (§6.2.3) and inserts with `ON CONFLICT DO NOTHING`. Indexes: `(scoring_run_id, candidate_class, candidate_score DESC)`; `(analytics_run_id, community_id)`; `(candidate_status)`.

#### `ring_memberships`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| ring_id | UUID | No | FK potential_fraud_ring_candidates | Imm. |
| account_id | VARCHAR(160) | No | FK accounts | Imm. |

PK: `(ring_id, account_id)`. Index: `(account_id)`. Ring constituent transactions are not stored; they are the snapshot transactions whose source and destination are both ring members (§9A.2), retrieved by query in `(timestamp, transaction_id)` order.

#### `ring_feature_sets`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| ring_feature_set_id | UUID | No | PK | Imm. |
| ring_id | UUID | No | FK candidates | Imm. |
| analytics_run_id | UUID | No | FK analytics_runs | Imm. |
| community_id | VARCHAR(64) | No | composite FK `(analytics_run_id, community_id)` → communities; equals the candidate's | Imm. |
| graph_snapshot_id | UUID | No | FK | Imm. |
| scoring_run_id | UUID | No | FK | Imm. |
| analytics_version | VARCHAR(100) | No | — | Imm. |
| feature_version | VARCHAR(100) | No | ring feature registry version | Imm. |
| ring_size | INTEGER | No | CHECK ≥ 1 | Imm. |
| transaction_count | INTEGER | No | CHECK ≥ 0 | Imm. |
| start_time | TIMESTAMPTZ | Yes | NULL when transaction_count = 0 | Imm. |
| end_time | TIMESTAMPTZ | Yes | NULL when transaction_count = 0 | Imm. |
| temporal_span_seconds | BIGINT | No | CHECK ≥ 0 | Imm. |
| suspicious_transaction_density | NUMERIC(8,7) | No | RSD | Imm. |
| risk_concentration | NUMERIC(8,7) | No | RC | Imm. |
| temporal_coordination | NUMERIC(8,7) | No | TC (§9A.2) | Imm. |
| money_flow_concentration | NUMERIC(8,7) | No | MFC | Imm. |
| centrality_signal | NUMERIC(8,7) | No | CS | Imm. |
| fan_in_signal | NUMERIC(8,7) | No | FI | Imm. |
| fan_out_signal | NUMERIC(8,7) | No | FO | Imm. |
| cycle_presence | NUMERIC(8,7) | No | CP ∈ {0,1} | Imm. |
| suspicious_path_density | NUMERIC(8,7) | No | SPD | Imm. |
| eligible_path_count | INTEGER | No | CHECK ≥ 0 | Imm. |
| qualifying_path_count | INTEGER | No | CHECK ≥ 0 | Imm. |
| paths_truncated | BOOLEAN | No | §16.7.2 | Imm. |
| availability | JSONB | No | per feature AVAILABLE/UNAVAILABLE | Imm. |
| computed_at | TIMESTAMPTZ | No | — | Imm. |

All decimal features CHECK 0 ≤ x ≤ 1. Indexes: `(ring_id, computed_at DESC)`; `(scoring_run_id)`.

#### `ring_risk_assessments`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| ring_risk_assessment_id | UUID | No | PK | Imm. |
| ring_id | UUID | No | FK candidates | Imm. |
| feature_set_id | UUID | No | FK ring_feature_sets | Imm. |
| scoring_run_id | UUID | No | FK scoring_runs | Imm. |
| member_risk | NUMERIC(8,7) | No | §9A.3 | Imm. |
| transaction_risk | NUMERIC(8,7) | No | = RSD | Imm. |
| topology_signal | NUMERIC(8,7) | No | §9A.3 | Imm. |
| temporal_signal | NUMERIC(8,7) | No | §9A.3 | Imm. |
| money_flow_signal | NUMERIC(8,7) | No | §9A.3 | Imm. |
| ring_risk_score | NUMERIC(8,7) | No | §9A.3 | Imm. |
| risk_tier | VARCHAR(20) | No | §12.6 thresholds | Imm. |
| availability | JSONB | No | per component | Imm. |
| risk_logic_version | VARCHAR(100) | No | FK | Imm. |
| analytics_version | VARCHAR(100) | No | — | Imm. |
| feature_version | VARCHAR(100) | No | — | Imm. |
| generated_at | TIMESTAMPTZ | No | — | Imm. |

All decimals CHECK 0 ≤ x ≤ 1. Indexes: `(ring_id, generated_at DESC)`; `(scoring_run_id, risk_tier)`.

### 6.3.6 Temporal motifs

#### `temporal_motifs`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| motif_id | UUID | No | PK; deterministic (§6.2.3) | Imm. |
| analytics_run_id | UUID | No | FK analytics_runs | Imm. |
| graph_snapshot_id | UUID | No | FK graph_snapshots | Imm. |
| motif_type | VARCHAR(40) | No | CHECK six types | Imm. |
| anchor_account_id | VARCHAR(160) | No | FK accounts; §15.9 per type | Imm. |
| start_time | TIMESTAMPTZ | No | event time | Imm. |
| end_time | TIMESTAMPTZ | No | event time | Imm. |
| temporal_window_seconds | INTEGER | No | CHECK > 0 | Imm. |
| participating_account_ids | JSONB | No | array, ascending | Imm. |
| participating_transaction_ids | JSONB | No | array, `(timestamp, transaction_id)` order | Imm. |
| transaction_count | INTEGER | No | CHECK > 0 | Imm. |
| motif_confidence | NUMERIC(8,7) | No | CHECK 0 ≤ x ≤ 1 | Imm. |
| order_ambiguous | BOOLEAN | No | §15.9.1 | Imm. |
| evidence | JSONB | No | §15.9.8 | Imm. |
| analytics_version | VARCHAR(100) | No | — | Imm. |
| computed_at | TIMESTAMPTZ | No | — | Imm. |

Indexes: `(analytics_run_id, motif_type, start_time)`; `(anchor_account_id, start_time)`; GIN `(participating_account_ids jsonb_path_ops)`.

### 6.3.7 Network intervention

#### `intervention_scenarios`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| scenario_id | UUID | No | PK | Imm. |
| mode | VARCHAR(10) | No | CHECK RANK/EVALUATE | Imm. |
| target_ring_id | UUID | No | FK candidates | Imm. |
| baseline_graph_snapshot_id | UUID | No | FK graph_snapshots | Imm. |
| scoring_run_id | UUID | No | FK scoring_runs | Imm. |
| intervention_type | VARCHAR(40) | Yes | EVALUATE only; CHECK four types | Imm. |
| target_ids | JSONB | Yes | EVALUATE only; sorted | Imm. |
| baseline_suspicious_flow | NUMERIC(20,4) | Yes | CHECK ≥ 0; set at completion | Once |
| baseline_suspicious_paths | INTEGER | Yes | CHECK ≥ 0 | Once |
| baseline_reachable_suspicious_pairs | INTEGER | Yes | CHECK ≥ 0 | Once |
| baseline_risk_mass | NUMERIC(20,7) | Yes | CHECK ≥ 0 (§16A.5) | Once |
| baseline_paths_truncated | BOOLEAN | Yes | §16.7.2 | Once |
| eligible_candidate_ids | JSONB | Yes | RANK only; the full pool (§16A.4.4) | Once |
| ranking_configuration | JSONB | No | §16A.14 weights, k_max, bounds | Imm. |
| ranking_configuration_hash | CHAR(64) | No | SHA-256 of canonical JSON | Imm. |
| analytics_version | VARCHAR(100) | No | — | Imm. |
| risk_logic_version | VARCHAR(100) | No | FK | Imm. |
| requested_by | UUID | No | FK users | Imm. |
| job_id | UUID | Yes | FK jobs | Imm. |
| status | VARCHAR(20) | No | CHECK QUEUED/RUNNING/COMPLETED/FAILED | State only |
| error_summary | TEXT | Yes | safe | Failure only |
| created_at | TIMESTAMPTZ | No | — | Imm. |
| completed_at | TIMESTAMPTZ | Yes | — | Once |

Results are immutable once `COMPLETED`. Indexes: `(target_ring_id, created_at DESC)`; `(status)`.

#### `intervention_candidates`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| candidate_id | UUID | No | deterministic (§6.2.3) | Imm. |
| scenario_id | UUID | No | FK intervention_scenarios | Imm. |
| operation_type | VARCHAR(40) | No | CHECK four types | Imm. |
| target_ids | JSONB | No | sorted account IDs, or `[edge_id]` | Imm. |
| residual_suspicious_flow | NUMERIC(20,4) | No | CHECK ≥ 0 | Imm. |
| flow_disruption | NUMERIC(20,4) | No | CHECK ≥ 0 | Imm. |
| flow_disruption_percentage | NUMERIC(8,7) | No | CHECK 0..1 | Imm. |
| residual_suspicious_paths | INTEGER | No | CHECK ≥ 0 | Imm. |
| normalized_path_disruption | NUMERIC(8,7) | No | CHECK 0..1 | Imm. |
| residual_reachable_suspicious_pairs | INTEGER | No | CHECK ≥ 0 | Imm. |
| normalized_connectivity_disruption | NUMERIC(8,7) | No | CHECK 0..1 | Imm. |
| residual_risk_mass | NUMERIC(20,7) | No | CHECK ≥ 0 | Imm. |
| residual_network_risk | NUMERIC(8,7) | No | CHECK 0..1 (§16A.12) | Imm. |
| normalized_risk_reduction | NUMERIC(8,7) | No | CHECK 0..1 | Imm. |
| intervention_cost | NUMERIC(12,4) | No | CHECK ≥ 0 | Imm. |
| normalized_intervention_cost | NUMERIC(8,7) | No | CHECK 0..1 | Imm. |
| intervention_score | NUMERIC(8,7) | No | CHECK 0..1 | Imm. |
| rank_position | INTEGER | No | CHECK > 0 | Imm. |
| affected_account_ids | JSONB | No | sorted | Imm. |
| affected_path_ids | JSONB | No | sorted | Imm. |
| alternative_path_ids | JSONB | No | sorted | Imm. |
| unavailable_metrics | JSONB | No | names of metrics with zero denominators | Imm. |
| evidence | JSONB | No | ranking inputs and supporting transaction IDs | Imm. |
| created_at | TIMESTAMPTZ | No | — | Imm. |

PK: `(scenario_id, candidate_id)`. UNIQUE `(scenario_id, rank_position)`. Because `candidate_id` is derived from the scenario's baseline, scoring run, ring, operation, sorted targets and ranking configuration (§6.2.3), the same candidate has the same ID in every rerun, which makes it a valid final tie-breaker (§16A.14). Baseline values are read from the parent scenario.

### 6.3.8 Investigation

#### `cases`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| case_id | UUID | No | PK | Imm. |
| title | VARCHAR(250) | No | non-empty | §22.2 |
| status | VARCHAR(30) | No | CHECK §17.2 states | State machine |
| priority | VARCHAR(20) | No | CHECK LOW/MEDIUM/HIGH/CRITICAL | §22.2 |
| assigned_to | UUID | Yes | FK users | §22.2 |
| created_by | UUID | No | FK users | Imm. |
| created_at | TIMESTAMPTZ | No | — | Imm. |
| updated_at | TIMESTAMPTZ | No | — | Yes |
| closed_at | TIMESTAMPTZ | Yes | terminal only | Once |
| version | INTEGER | No | optimistic concurrency; increments on update | Yes |

Indexes: `(status, updated_at DESC)`; `(assigned_to, status)`; `(created_by)`; `(created_at DESC)`. Cases are never physically deleted.

#### `case_subjects`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| case_id | UUID | No | FK cases | Imm. |
| subject_type | VARCHAR(20) | No | CHECK ACCOUNT/TRANSACTION/RING/SCENARIO | Imm. |
| subject_id | VARCHAR(160) | No | validated to exist at insert | Imm. |
| added_by | UUID | No | FK users | Imm. |
| added_at | TIMESTAMPTZ | No | — | Imm. |
| removed_by | UUID | Yes | FK users | Once |
| removed_at | TIMESTAMPTZ | Yes | — | Once |

PK: `(case_id, subject_type, subject_id, added_at)`. Removal is a soft removal; history is retained. Index: `(subject_type, subject_id)`.

#### `findings`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| finding_id | UUID | No | PK | Imm. |
| case_id | UUID | No | FK cases | Imm. |
| type | VARCHAR(50) | No | non-empty | Imm. |
| description | TEXT | No | non-empty; ≤ 20,000 chars | Imm. |
| evidence | JSONB | No | list of `{type, id}` references, validated | Imm. |
| source | VARCHAR(100) | No | non-empty | Imm. |
| created_by | UUID | No | FK users | Imm. |
| created_at | TIMESTAMPTZ | No | — | Imm. |

Findings are append-only. Indexes: `(case_id, created_at)`; `(created_by, created_at)`.

#### `audit_events`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| event_id | UUID | No | PK | Imm. |
| user_id | UUID | Yes | FK users | Imm. |
| action | VARCHAR(100) | No | — | Imm. |
| resource_type | VARCHAR(100) | No | — | Imm. |
| resource_id | VARCHAR(200) | Yes | — | Imm. |
| outcome | VARCHAR(20) | No | CHECK SUCCESS/DENIED/FAILED | Imm. |
| timestamp | TIMESTAMPTZ | No | processing time | Imm. |
| request_id | VARCHAR(100) | Yes | — | Imm. |
| metadata | JSONB | Yes | sanitized (§24.3) | Imm. |

Audit records are append-only. Indexes: `(timestamp DESC)`; `(user_id, timestamp DESC)`; `(resource_type, resource_id)`; `(request_id)`.

### 6.3.9 Evaluation

#### `evaluation_runs`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| evaluation_run_id | UUID | No | PK | Imm. |
| dataset_id | UUID | No | FK datasets | Imm. |
| model_version | VARCHAR(100) | No | FK | Imm. |
| test_snapshot_id | UUID | No | FK graph_snapshots | Imm. |
| scoring_run_id | UUID | No | FK scoring_runs | Imm. |
| analytics_version | VARCHAR(100) | No | — | Imm. |
| risk_logic_version | VARCHAR(100) | No | FK | Imm. |
| reference_construction_version | VARCHAR(50) | No | — | Imm. |
| configuration | JSONB | No | — | Imm. |
| status | VARCHAR(20) | No | CHECK QUEUED/RUNNING/COMPLETED/FAILED | State only |
| created_at | TIMESTAMPTZ | No | — | Imm. |
| completed_at | TIMESTAMPTZ | Yes | — | Once |

#### `evaluation_metrics`

| Column | Type | Null | Constraint | Mutable |
|---|---|---|---|---|
| evaluation_run_id | UUID | No | FK evaluation_runs | Imm. |
| level | VARCHAR(20) | No | CHECK TRANSACTION/ACCOUNT/RING/NETWORK | Imm. |
| metric | VARCHAR(60) | No | §28.7 | Imm. |
| value | DOUBLE PRECISION | Yes | NULL when unavailable | Imm. |
| sample_count | BIGINT | No | CHECK ≥ 0 | Imm. |
| availability | VARCHAR(20) | No | AVAILABLE/UNAVAILABLE | Imm. |
| details | JSONB | Yes | confusion matrix, curves, limitations | Imm. |

PK: `(evaluation_run_id, level, metric)`.

## 6.4 Foreign-Key Delete/Update Semantics

- Domain identifiers use `ON UPDATE RESTRICT`.
- Every foreign key uses `ON DELETE RESTRICT` unless stated below.
- Neo4j-only snapshot data is deleted by the snapshot retirement job; the PostgreSQL `graph_snapshots` row is retained with status `RETIRED`, and every analytical record referencing it remains valid.
- Cases, findings, users, and audit events are never physically deleted. `cases.assigned_to` keeps `RESTRICT` because users are never deleted.
- Audit events are never cascaded or edited.

## 6.5 Database Constraints and Immutability Enforcement

Migrations MUST enforce primary keys, uniqueness, score ranges, non-negative amounts and counts, valid role/status/tier values, and required identifiers. Immutability is enforced in depth:

1. The application database role has no `UPDATE` or `DELETE` privilege on `findings`, `audit_events`, `transactions`, `risk_assessments`, `account_feature_values`, `shap_explanations`, `propagation_contributions`, `ring_feature_sets`, `ring_risk_assessments`, `temporal_motifs`, `intervention_candidates`, and `evaluation_metrics`.
2. A `BEFORE UPDATE` trigger on tables with partially mutable rows rejects changes to columns marked "Imm.".
3. Migrations run under a separate owner role.

## 6.6 Transaction Boundaries

- Accepted canonical rows of one ingestion run commit atomically with that run's terminal metadata (§7.2).
- A RiskAssessment is inserted atomically as a complete record. All assessments of a scoring run become visible together when the scoring run is marked `SUCCEEDED` and the active context is updated.
- Neo4j construction is a derived operation after the PostgreSQL commit and is not part of a distributed transaction. Its consistency strategy is §6.8.
- Activation of a pipeline's outputs (§6.9) is one PostgreSQL transaction.
- Case updates use optimistic concurrency on `cases.version`; a stale version returns `409 CASE_VERSION_CONFLICT`.

## 6.7 Migration Ordering

Parent tables are created before dependent tables. The cyclic reference `accounts.latest_risk_assessment_id → risk_assessments` is added as a separate migration step after `risk_assessments` exists. Seeds MUST bootstrap an administrator without storing a plaintext password (§22.1).

## 6.8 Neo4j Physical Schema and Snapshot Consistency

### 6.8.1 Graph schema

```text
(:Account {snapshot_key, snapshot_id, account_id, dataset_id, account_type})
(:Transaction {snapshot_key, snapshot_id, transaction_id, amount, timestamp, transaction_type})
(:Account)-[:SENDS]->(:Transaction)-[:RECEIVED_BY]->(:Account)
(:Account)-[:TRANSFERRED_TO {snapshot_id, tx_count, total_amount, first_ts, last_ts}]->(:Account)
```

- `snapshot_key = snapshot_id + ":" + account_id` (or `transaction_id`). Neo4j Community lacks composite node keys, so the concatenated key carries uniqueness.
- `TRANSFERRED_TO` is the account projection of §3.5: one relationship per ordered account pair with at least one transaction in the snapshot. All traversals use it; `Transaction` nodes are evidence.
- `fraud_label` is **not** written to Neo4j. Labels stay in PostgreSQL so that no graph query can leak them into features.
- Neo4j MAY cache `pagerank_norm`, `community_id`, and `risk_tier` as Account properties for visualization; these caches are never read by analytical computation.

Constraints and indexes: UNIQUE `Account.snapshot_key`; UNIQUE `Transaction.snapshot_key`; index `Account(account_id)`; index `Account(snapshot_id)`; index `Transaction(transaction_id)`.

### 6.8.2 Build

1. Create `graph_snapshots` row with status `BUILDING`, `data_cutoff`, and purpose.
2. Load accounts, then transactions, from PostgreSQL in ascending canonical ID order, in batches (`graph_build_batch_size`, default 10,000) using `UNWIND` with `MERGE` on `snapshot_key`. Batches are idempotent.
3. Build `TRANSFERRED_TO` aggregates from the loaded transactions.

### 6.8.3 Retry

A failed or interrupted build is retried by deleting every node and relationship with that `snapshot_id` in batches, then rebuilding. Partial snapshots are never read because only `READY` snapshots referenced by the active context or by an explicit lineage parameter are queried.

### 6.8.4 Validation

Status `VALIDATING` compares Neo4j with PostgreSQL for the snapshot's transaction set:

- account node count = distinct accounts referenced by the snapshot's transactions;
- transaction node count = transaction count;
- `TRANSFERRED_TO` count = distinct ordered account pairs;
- sum of `total_amount` = sum of transaction amounts (exact decimal comparison after both sides are rounded to 6 dp);
- `validation_digest` = SHA-256 over the sorted list of `transaction_id` values read back from Neo4j, which must equal the digest computed from PostgreSQL.

Any mismatch sets status `FAILED` with `failure_category = GRAPH_VALIDATION_MISMATCH`. On success the snapshot becomes `READY`.

### 6.8.5 Query isolation

Every Cypher query issued by GraphService receives `snapshot_id` as a parameter and matches only nodes and relationships of that snapshot. The default `snapshot_id` is the active context's. Cypher is parameterized; labels, relationship types, and property names come from a fixed allow-list in code.

### 6.8.6 Retirement

After a new operational snapshot is activated, the previous operational snapshot is retired by a job that deletes its Neo4j data in batches and sets its status `RETIRED`. `TRAINING_SPLIT` snapshots are retired as soon as training and evaluation complete. Analytical results for retired snapshots remain in PostgreSQL; graph-traversal endpoints for a retired snapshot return `410 SNAPSHOT_RETIRED`.

## 6.9 Activation and Current Projections

When a pipeline run reaches `READY`, one PostgreSQL transaction:

1. updates `active_context` to the run's dataset, snapshot, analytics run, scoring run, model version, and risk logic version;
2. updates the projection columns of `accounts` for the dataset from the run's assessments and community memberships;
3. writes an audit event `pipeline.activate`.

If any step fails, nothing changes and the previous context stays active. The projection is never written outside this transaction.

---

# 7. Dataset Ingestion, Pipeline, and Jobs

## 7.1 Input

PaySim is the primary demonstration dataset. Future supported datasets MUST be normalized into the canonical schema through a versioned adapter. CSV is the only supported file format in the MVP.

### 7.1.1 PaySim adapter (`paysim-v1`)

| Source column | Canonical treatment |
|---|---|
| `step` | `timestamp = epoch_anchor + step × 1 hour`. `epoch_anchor` is fixed in `adapter_config` (baseline `2020-01-01T00:00:00Z`). `timestamp_resolution_seconds = 3600`. |
| `type` | `transaction_type`; allowed values `CASH_IN`, `CASH_OUT`, `DEBIT`, `PAYMENT`, `TRANSFER`. |
| `amount` | `amount`; must parse as a decimal ≥ 0 with at most 6 fractional digits after rounding half-even. |
| `nameOrig`, `nameDest` | `source_account_ref`, destination `source_account_ref`; account type per §6.2.2. |
| `isFraud` | `fraud_label` (`1` → TRUE, `0` → FALSE). |
| `isFlaggedFraud` | **Discarded.** It is a rule output of the simulator and MUST NOT be stored or used as a feature. |
| `oldbalanceOrg`, `newbalanceOrig`, `oldbalanceDest`, `newbalanceDest` | **Discarded.** They encode the simulator's fraud mechanism and are a known leakage source. |
| (row position) | `source_transaction_ref` = 1-based row ordinal, zero-padded to 10 digits. |

### 7.1.2 PaySim reference slice

The reference slice (DEC-01) is defined deterministically as all rows with `step ≤ S*`, where `S*` is the largest step such that the number of rows with `step ≤ S*` is at most `reference_slice_max_rows` (baseline 1,000,000). The slice rule and `S*` are recorded in `adapter_config`. A slice is a distinct dataset version from the full file.

## 7.2 Ingestion Pipeline

```text
Upload or server-path registration
 → checksum and header check (synchronous, §19.5)
 → INGEST job:
     stream rows into a per-run unlogged staging table (COPY)
     → validate and normalize each row
     → classify ACCEPTED / REJECTED(reason) / DUPLICATE
     → single transaction: INSERT accounts (ON CONFLICT DO NOTHING) + INSERT accepted transactions
                           + finalize ingestion_runs counts and status
     → drop staging table
```

## 7.3 Validation

The ingestion layer MUST validate: required columns; types; account identifiers (non-empty, ≤ 128 characters, allowed prefix); amount validity (§7.1.1); timestamp derivability; allowed transaction type; fraud-label values; duplicate policy (§7.5); and source-schema compatibility. Each rejection has a reason code from a fixed list (`MISSING_COLUMN`, `TYPE_ERROR`, `INVALID_ACCOUNT_ID`, `INVALID_AMOUNT`, `INVALID_TIMESTAMP`, `INVALID_TYPE`, `INVALID_LABEL`, `FIELD_TOO_LONG`). Malformed records MUST NOT enter canonical storage.

## 7.4 Batch Failure Isolation

Invalid records are isolated from valid records. The run records accepted, rejected, and duplicate counts, a reason-code histogram, and up to 100 sample row ordinals per reason. Row content is not copied into metadata.

## 7.5 Idempotency and Duplicates

- **Same file, same dataset version** (same checksum and `dataset_version`): `409 DATASET_ALREADY_REGISTERED`.
- **Same file, new dataset version** (explicit reprocessing, for example under a new adapter configuration): allowed; creates a new dataset with a new `dataset_key` and disjoint canonical IDs.
- **Retry of the same ingestion run**: truncates the run's staging table and repeats; the canonical insert is a single transaction, so a retry never duplicates canonical rows.
- **Row duplicates**: a row is a duplicate when its `source_transaction_ref` repeats within the file. For PaySim, row ordinals are unique by construction, so content-identical rows are distinct events and are **not** treated as duplicates. `source_record_hash` is retained for diagnostics.

## 7.6 Pipeline State Machine

```text
CREATED
  → INGESTING → INGESTED
  → PROFILING → PROFILED
  → GRAPH_BUILDING → GRAPH_READY
  → ANALYTICS_RUNNING → ANALYTICS_READY
  → FEATURES_RUNNING → FEATURES_READY
  → [TRAINING → MODEL_READY]        (only when no compatible model is registered)
  → SCORING → SCORED
  → RING_ANALYSIS → READY
```

| Stage | Work | Inputs | Outputs |
|---|---|---|---|
| INGESTING | §7.2 | uploaded file | canonical rows, ingestion run |
| PROFILING | §7.9 | canonical rows | `dataset_profiles` row |
| GRAPH_BUILDING | §6.8.2–6.8.4 for the OPERATIONAL snapshot (`data_cutoff` = dataset max timestamp) | canonical rows | READY snapshot |
| ANALYTICS_RUNNING | §8 metrics, components, communities; §15.9 motifs | snapshot | `analytics_runs`, `account_graph_metrics`, `communities`, `community_memberships`, `temporal_motifs` |
| FEATURES_RUNNING | §10 for every account at `T = data_cutoff` | analytics run | `account_feature_values` |
| TRAINING | §11; builds TRAINING_SPLIT snapshots and their analytics/features; registers a model | dataset | `model_versions`, artifact |
| SCORING | §11 inference, §12, §13 in the order of §12.4 | features, model | `scoring_runs`, `risk_assessments`, `propagation_contributions` |
| RING_ANALYSIS | §9 candidates, §9A rings | scoring run, analytics run | candidates, memberships, ring features, ring risk |
| READY | §6.9 activation | all of the above | `active_context` updated |

Rules:

1. Any active state MAY transition to `FAILED`, recording `failure_stage`, `failure_category`, `safe_failure_message`, and `resumable_from`.
2. Invalid transitions MUST be rejected.
3. TRAINING is entered only if no registered model has the current `feature_version`, `feature_regime`, and target definition; otherwise the transition `FEATURES_READY → SCORING` is taken and the chosen model is recorded on the pipeline run.
4. If no model can be trained or loaded, SCORING still runs with `ml_score` unavailable (§11.12), and the run reaches READY with that state visible.
5. Multi-Level Evaluation (§28.7) and intervention simulation (§16A) are separate jobs that require a READY pipeline run.
6. The analytical order is acyclic: no stage reads an output of a later stage of the same run.

## 7.7 Retry and Resume

Each stage writes all of its outputs keyed by its run identifier (snapshot, analytics run, feature snapshot, scoring run). A stage is retried by deleting that stage's partial outputs for that identifier and re-running it; canonical records are never touched by retries.

```text
FAILED(resumable_from = X)
 → verify prerequisites of X are READY
 → delete partial outputs of X
 → re-run X
 → continue the state machine
```

`POST /pipeline-runs/{id}/retry` (ADMIN) performs this. Retrying a stage whose prerequisites are missing returns `409 PIPELINE_PREREQUISITE_MISSING`.

## 7.8 Job Execution Model

- All long-running work is executed by the `worker` process from the `jobs` table. Job kinds: `INGEST`, `PIPELINE_STAGE`, `TRAIN`, `INTERVENTION`, `EVALUATION`, `SNAPSHOT_RETIRE`.
- A worker claims a job with `SELECT … FOR UPDATE SKIP LOCKED`, sets `RUNNING`, `lease_owner`, and `lease_expires_at = now() + job_lease_seconds` (baseline 60), and renews the lease every `job_heartbeat_seconds` (baseline 15).
- Pipeline stages of one dataset are serialized with a PostgreSQL advisory lock whose key is derived from `dataset_id`. Two pipeline runs for the same dataset cannot execute stages concurrently; a second `POST` returns `409 PIPELINE_ALREADY_RUNNING`.
- A job whose lease expires is returned to `QUEUED` if `attempts < max_attempts`, otherwise marked `FAILED` with `failure_category = LEASE_EXPIRED`; its pipeline run moves to `FAILED` with `resumable_from` set.
- Each job kind has a wall-clock limit (`job_timeout_seconds` per kind). Exceeding it fails the job; it never yields partial results.
- Worker concurrency is configurable (baseline 1 pipeline job and 2 intervention/evaluation jobs at once).

**Durable job lifecycle.** The same lifecycle applies to every job kind:

1. **Acceptance is durable before the response.** The endpoint inserts the resource row (dataset, pipeline run, scenario, or evaluation run) and its `jobs` row with status `QUEUED` in one PostgreSQL transaction, commits, and only then returns `202`. If the commit fails, the client receives an error and nothing is queued.
2. **Claim and attempts.** Claiming increments `attempts` and sets the lease in the same statement. The latest failure of any attempt is recorded in `failure_category` and `error_summary`; every attempt start and failure is also logged with the `job_id` (§24.2).
3. **Idempotent execution.** A job writes only rows keyed by its own run identifier. Before (re)executing, it deletes its own partial outputs (§7.7); rows with deterministic identifiers (§6.2.3) are inserted with `ON CONFLICT DO NOTHING`. Re-running a job therefore never duplicates or alters completed outputs. Status changes of the parent resource (`RUNNING`, `COMPLETED`, `FAILED`) are written in the same transaction as the job's final outputs.
4. **Recovery after a restart.** No job state lives in process memory. If the backend restarts, queued and running jobs are unaffected. If a worker dies, its job's lease stops being renewed; when `lease_expires_at` passes, any worker returns the job to `QUEUED` (or `FAILED` when `attempts = max_attempts`). A `RUNNING` row with an expired lease is the only definition of a stale job, and lease expiry is the only recovery mechanism.
5. **Terminal states.** `SUCCEEDED`, `FAILED`, and `CANCELLED` (ADMIN action only) are terminal for a job. A failed pipeline run is resumed only through `POST /pipeline-runs/{id}/retry`, which creates a new job; failed scenarios and evaluation runs are re-submitted as new resources.

## 7.9 Dataset Profiling

The PROFILING stage records, for the dataset, at least:

- row counts (seen, accepted, rejected by reason), distinct accounts by type, distinct timestamps, rows per timestamp (min, median, max);
- fraction of accounts that appear as both sender and receiver;
- out-degree and in-degree distributions (quantiles);
- maximum directed chain length in the account projection (bounded at 10) and the count of directed simple paths of length ≥ 2, estimated by bounded enumeration;
- fraud-label prevalence by transaction type;
- sizes of weakly connected components of the subgraph induced by fraud-labelled transactions (histogram);
- count of accounts with ≥ 7 active days (input to F27 availability).

The profile is displayed on the ingestion run page and is attached to every evaluation report. It is informational and never alters analytics.

## 7.10 Synthetic Pattern Injection (optional, disabled by default)

A deployment MAY create a derived dataset that adds deterministic synthetic transactions realizing the six motif types and ring structures, to demonstrate Ring Intelligence and Intervention Analysis. If used:

1. it is a separate dataset version with `is_synthetic_injection = TRUE` and its generator configuration and seed in `adapter_config`;
2. injected transactions carry `fraud_label = NULL` and are excluded from model training and from every PaySim-label evaluation metric;
3. every API response and UI view of that dataset shows a persistent `SYNTHETIC DATA` label;
4. evaluation reports MUST state that metrics on injected patterns measure detector recall on known templates, not real-world performance.

---

# 8. Graph Intelligence

## 8.1 General Contract

Every metric result is tied to an `analytics_run_id` (and therefore a `graph_snapshot_id`), `analytics_version`, algorithm parameters, projection semantics, engine, and `computed_at`. All algorithms run on the account projection exported from PostgreSQL for the snapshot's transaction set, with nodes inserted in ascending `account_id` order and edges in ascending `(source, destination)` order. Batch algorithms never run during interactive requests.

## 8.2 Engine

| Tier | Engine | Determinism mechanism |
|---|---|---|
| Reference (acceptance) | NetworkX in the worker process (DEC-01) | fixed insertion order; explicit seeds; pinned library version recorded in `algorithm_configuration` |
| Benchmark (full dataset, optional) | Neo4j Graph Data Science plugin | `concurrency = 1`; node projection ordered by `account_id`; distinct `analytics_version` |

Results from different engines carry different `analytics_version` values and are never mixed in one scoring run.

## 8.3 Algorithms

### Degree

- `degree`: unique adjacent accounts in the undirected simple account projection.
- `in_degree`: unique incoming counterparties.
- `out_degree`: unique outgoing counterparties.
- Parallel transactions do not increase degree.

### PageRank

```text
projection     = directed weighted simple (TRANSFERRED_TO)
weight         = total_amount per ordered pair
damping        = 0.85
max_iterations = 100
tolerance      = 1e-6
dangling nodes = uniform redistribution
```

`pagerank_norm` = min-max of raw scores within the snapshot; a constant series maps to 0.

### Betweenness centrality

```text
algorithm  = Brandes exact
projection = directed unweighted simple
normalized = true   (divide by (n−1)(n−2))
```

Exact computation is required on the reference tier. If the benchmark tier uses sampling, the run records the sampling configuration under a distinct `analytics_version`.

### Connected components

```text
algorithm  = weakly connected components
projection = undirected simple
component_id = minimum account_id in the component
```

`component_size` is the number of accounts in the component.

### Community detection

```text
algorithm  = Louvain
projection = undirected weighted simple
weight     = total_amount summed over both directions
resolution = 1.0
seed       = 42 (reference tier; passed to the NetworkX implementation)
```

`community_id` is the deterministic identifier of §6.2.3. The run records seed, resolution, engine, library version, and community count.

## 8.4 Normalization

| Input class | Method |
|---|---|
| Already bounded in [0,1] | identity |
| Non-negative skewed metrics and amounts | `log1p`, then percentile rank against the normalization reference (§12.2) |
| PageRank | feature F14: snapshot min-max (`pagerank_norm`); in risk and ring compositions: percentile rank within the snapshot |
| Betweenness | feature F15: algorithm-normalized value; in risk and ring compositions: percentile rank within the snapshot |
| Constant series | 0 |
| Unavailable | explicit `UNAVAILABLE` |

Any change to algorithm, parameter, projection, normalization, implementation, engine, or seed creates a new `analytics_version`.

"Percentile rank within the snapshot" means `(number of accounts with a strictly smaller value + 0.5 × number of other accounts with an equal value) / (n − 1)` for `n > 1`, and 0 for `n = 1`. It is in [0,1] and is deterministic.

---

# 9. Community and Potential Fraud-Ring Analysis

## 9.1 Analytical Pipeline

```text
Communities (ANALYTICS stage)
  → after SCORING: community signals (H, D, C, community_temporal_density, M)
  → candidate score → class
  → persist classes SUSPICIOUS_COMMUNITY and POTENTIAL_FRAUD_RING_CANDIDATE
  → Ring Intelligence for POTENTIAL_FRAUD_RING_CANDIDATE (§9A)
```

All signals are evaluated in the analytical context `(graph_snapshot_id, scoring_run_id)` of §3.5.

## 9.2 Deterministic Candidate Score

```text
candidate_score =
    clamp(0.35·H + 0.25·D + 0.15·C + 0.15·community_temporal_density + 0.10·M, 0, 1)
```

These are baseline engineering parameters, not calibrated AML probability weights.

| Score | Class | Persisted | Ring Intelligence |
|---|---|---|---|
| < 0.50 | NOT_SUSPICIOUS | No | No |
| 0.50 ≤ score < 0.70 | SUSPICIOUS_COMMUNITY | Yes | No |
| 0.70 ≤ score ≤ 1.00 | POTENTIAL_FRAUD_RING_CANDIDATE | Yes | Yes |

Both persisted classes are surfaced as investigative candidates. Communities with fewer than `min_candidate_community_size` members (baseline 3) are not scored.

## 9.3 Signal Definitions

| Signal | Definition | Zero denominator |
|---|---|---|
| `H` | `(members that are suspicious accounts) / member_count` | n/a (member_count ≥ 3) |
| `D` | `(amount of suspicious transactions whose source and destination are both members) / (amount of all transactions whose source and destination are both members)` | 0, unavailable |
| `C` | `mean(max member PageRank percentile, max member betweenness percentile)` | n/a |
| `community_temporal_density` | `(internal transactions that fall in at least one UTC-aligned rolling 1-hour window containing ≥ 3 internal transactions) / (internal transactions)`; windows start at each internal transaction's timestamp and include `[t, t + 3600 s)` | 0, unavailable |
| `M` | `(outgoing amount of member-sourced transactions that support at least one qualifying path whose source is a member) / (total outgoing amount of member-sourced transactions)` | 0, unavailable |

"Internal transaction" means a transaction whose source and destination are both members. Unavailable signals contribute 0 and are marked unavailable in `signal_summary`. `community_temporal_density` was called `T` in v1.3.2; it is distinct from the ring feature `TC` (§9A.2).

## 9.4 Candidate Status

Workflow status `CANDIDATE → REVIEWED` or `CANDIDATE → DISMISSED`, and `REVIEWED ↔ DISMISSED`, changed through `PATCH /rings/{id}/status` by roles holding `ring.review` (§22.2). Status does not alter any score. Every change is audited.

## 9.5 Interpretation Boundary

Community membership is not proof of a fraud ring. A potential fraud-ring candidate is not a confirmed criminal organization. APIs and UI MUST use analytical wording such as "potential fraud ring", "suspicious network", or "ring risk assessment".

---

# 9A. Ring Intelligence

## 9A.1 Purpose and Boundary

Ring Intelligence extends community analysis for candidates of class `POTENTIAL_FRAUD_RING_CANDIDATE`. A community is a structural grouping; a potential fraud ring is a suspicious-network hypothesis derived from community membership plus transaction, risk, graph, temporal, and money-flow evidence. The system MUST NOT treat community membership alone as ring evidence and MUST NOT present a ring as a confirmed criminal organization.

```text
Candidate (class POTENTIAL_FRAUD_RING_CANDIDATE)
  → ring membership
  → ring features
  → ring risk
  → ring evidence
```

## 9A.2 Ring Membership and Features

**Membership.** Ring members are all members of the source community (MVP rule). Members are persisted in `ring_memberships`. Ring constituent transactions are the snapshot transactions whose source and destination are both members. `ring_size` = member count; `transaction_count` = constituent transaction count; `start_time`/`end_time` = earliest/latest constituent timestamp; `temporal_span_seconds = end_time − start_time`, or 0 with NULL times when there are no constituent transactions.

**Features.** All values are in [0,1]. Every feature records availability.

| Feature | Definition | Zero denominator |
|---|---|---|
| `RSD` | suspicious constituent transactions / constituent transactions | 0, unavailable |
| `RC` | `k = min(3, ring_size)`; `RC = (Σ final_score of the k highest-scoring members) / (Σ final_score of all members)`; members ordered by `final_score` descending, then `account_id` ascending; members without an assessment count as 0 | 0, unavailable |
| `TC` | constituent transactions that belong to at least one motif instance (any type) whose transactions are all constituent transactions / constituent transactions; each transaction counted once | 0, unavailable |
| `MFC` | Top-k concentration of suspicious flow in ring scope. (1) For each in-scope qualifying path `p`, `path_flow(p)` = sum of amounts of the unique suspicious supporting transactions of `p`. (2) Rank paths by `path_flow` descending, then by the §16.5 path order. (3) `D` = the first `min(mfc_top_k, number of paths)` paths; baseline `mfc_top_k = 3`. (4) `MFC = (sum of amounts of the unique suspicious supporting transactions of the paths in D) / (suspicious flow)`, each transaction counted once in numerator and denominator. MFC = 1 when the ring has at most `mfc_top_k` qualifying paths, and approaches 0 when flow is spread over many paths. | 0, unavailable |
| `CS` | `mean(mean member PageRank percentile, mean member betweenness percentile)` | n/a |
| `FI` | members that are the anchor (destination) of ≥ 1 `FAN_IN` motif / ring_size | n/a |
| `FO` | members that are the anchor (source) of ≥ 1 `FAN_OUT` motif / ring_size | n/a |
| `CP` | 1 if at least one `CIRCULAR_FLOW` motif has all its accounts in the ring; else 0 | n/a |
| `SPD` | in-scope qualifying paths / eligible paths (§3.5) | 0, unavailable |

If ring-scope path enumeration reaches the analytical bound (§16.7.2), `paths_truncated = TRUE` and `MFC` and `SPD` are computed on the enumerated set and marked as lower-confidence in availability.

## 9A.3 Ring Risk

Ring risk is separate from account ML fraud probability and account analytical risk.

```text
ring_risk_score =
    clamp(
        0.25 · member_risk +
        0.20 · transaction_risk +
        0.20 · topology_signal +
        0.20 · temporal_signal +
        0.15 · money_flow_signal,
        0, 1)
```

| Component | Definition |
|---|---|
| `member_risk` | arithmetic mean of `final_score` over members that have an assessment in the ring's scoring run; members without one are excluded; if none, 0 and unavailable |
| `transaction_risk` | equals `RSD` |
| `topology_signal` | `mean(CS, FI, FO, CP, SPD)` |
| `temporal_signal` | mean of six indicators, one per motif type; each is 1 if at least one instance of that type has all its accounts in the ring, else 0 |
| `money_flow_signal` | suspicious flow / eligible flow in ring scope (§3.5); 0 and unavailable when eligible flow is 0 |

All five components and their availability flags are persisted. Unavailable components contribute 0; weights are not renormalized. The ring risk tier uses the thresholds of §12.6.

Fan-in and fan-out contribute through both `topology_signal` (as FI/FO) and `temporal_signal` (as indicators). This double contribution is intentional and documented; combined effective weight is ≈ 0.073 each.

## 9A.4 Ring Evidence

A ring assessment MUST reference members, constituent transactions, the source community, graph metrics, motifs, qualifying paths (by `path_id`), account assessments, component signals, and every applicable version (analytics, feature, model, risk logic, scoring run, snapshot). Evidence MUST be sufficient to reconstruct the assessment without AI inference.

## 9A.5 Determinism and Lineage

For the same snapshot, analytics run, scoring run, and configuration, ring extraction, features, and risk MUST be identical across runs. Identifiers follow §6.2.3. Lists are ordered: accounts by `account_id`, transactions by `(timestamp, transaction_id)`, paths by §16.5.

## 9A.6 Interpretation Boundary

The UI, API, and AI context MUST use analytical language. Ring scores, topology, motifs, and membership MUST NOT be presented as definitive criminality claims.

---

# 10. Feature Engineering

## 10.1 Normative Feature Registry (feature_version `v1`)

`T` is the observation cutoff in event time (§3.4). "Window" bounds are half-open `(T − w, T]`. `ε = 1e-9`. Direction "any" means the account is source or destination. The registry is serialized as a repository file whose SHA-256 is `definition_hash`.

| ID | Name | Definition | Window | Unavailable when | Cold-start value |
|---|---|---|---|---|---|
| F01 | transaction_count | count of transactions, any direction | lifetime ≤ T | never | 0 (ZERO) |
| F02 | incoming_transaction_count | count with destination = account | lifetime | never | 0 |
| F03 | outgoing_transaction_count | count with source = account | lifetime | never | 0 |
| F04 | incoming_amount | sum of incoming amounts | lifetime | never | 0 |
| F05 | outgoing_amount | sum of outgoing amounts | lifetime | never | 0 |
| F06 | mean_transaction_amount | mean amount, any direction | lifetime | never | 0 |
| F07 | median_transaction_amount | median amount, any direction (mean of the two middle values for even n) | lifetime | never | 0 |
| F08 | amount_stddev | sample standard deviation; 0 if fewer than 2 | lifetime | never | 0 |
| F09 | inbound_outbound_ratio | `min(incoming_amount / max(outgoing_amount, ε), 1e6)`; 0 if incoming_amount = 0 | lifetime | never | 0 |
| F10 | transaction_type_entropy | `−Σ p(type) log2 p(type)` over any-direction transactions | lifetime | never | 0 |
| F11 | degree | §8.3, from the snapshot used | snapshot | no usable snapshot | UNAVAILABLE |
| F12 | in_degree | §8.3 | snapshot | no usable snapshot | UNAVAILABLE |
| F13 | out_degree | §8.3 | snapshot | no usable snapshot | UNAVAILABLE |
| F14 | pagerank | `pagerank_norm` | snapshot | no usable snapshot | UNAVAILABLE |
| F15 | betweenness | algorithm-normalized betweenness | snapshot | no usable snapshot | UNAVAILABLE |
| F16 | component_size | accounts in the account's weak component | snapshot | no usable snapshot | UNAVAILABLE |
| F17 | community_size | members of the account's community | snapshot | no usable snapshot | UNAVAILABLE |
| F18 | network_density | `2E / (N(N−1))` of the account's **community** in the undirected simple projection; 0 if N < 2 | snapshot | no usable snapshot | UNAVAILABLE |
| F19 | suspicious_neighbor_count | distinct undirected neighbors that are suspicious accounts | snapshot | regime `RISK_FEATURES_UNAVAILABLE` | UNAVAILABLE |
| F20 | transaction_concentration | `max over counterparties of (amount exchanged with that counterparty, any direction) / (total amount, any direction)` | 7 d | never | 0 |
| F21 | velocity_24h | count of transactions, any direction | 24 h | never | 0 |
| F22 | velocity_7d | count / 7 | 7 d | never | 0 |
| F23 | volume_change_7d | `(V_cur − V_prev) / V_prev` with V = total amount any direction in `(T−7d,T]` and `(T−14d,T−7d]`; 0 if both 0; `10.0` if V_prev = 0 and V_cur > 0; capped at 10.0 | 14 d | never | 0 |
| F24 | mean_inter_transaction_time | mean successive gap in seconds after `(timestamp, transaction_id)` ordering; 0 if fewer than 2 | lifetime | never | 0 |
| F25 | short_interval_ratio | gaps ≤ 3600 s / max(gap count, 1) | 7 d | never | 0 |
| F26 | burst_score | `max(hourly count) / max(mean hourly count, 1)` over 168 UTC hour buckets including empty hours | 7 d | never | 0 |
| F27 | dormancy_to_activity | §15.5 | 30 d + 24 h | fewer than 7 active days in prior 30 d | UNAVAILABLE |
| F28 | rapid_in_out_ratio | §15.3 rapid events / max(inbound count, 1) | 24 h | never | 0 |
| F29 | cyclic_activity_score | §15.6 cycle events / max(transaction count, 1) | 7 d | never | 0 |
| F30 | short_lived_activity_score | §15.7 short-lived periods / max(completed periods, 1) | lifetime | never | 0 |
| F31 | reachable_suspicious_accounts | distinct suspicious accounts within 3 directed outgoing hops | snapshot | regime `RISK_FEATURES_UNAVAILABLE` | UNAVAILABLE |
| F32 | bounded_path_count | directed simple outgoing paths of length 1..5 from the account, counted up to 100 (value capped at 100) | snapshot | no usable snapshot | UNAVAILABLE |
| F33 | shortest_suspicious_path_length | minimum directed outgoing hops (≤ 5) to a suspicious account; 6 if none within 5 | snapshot | regime `RISK_FEATURES_UNAVAILABLE` | UNAVAILABLE |
| F34 | intermediary_count | distinct accounts strictly inside the paths counted by F32 | snapshot | no usable snapshot | UNAVAILABLE |
| F35 | flow_concentration | `max over first-hop counterparties of outgoing amount to that counterparty / outgoing amount`; 0 if outgoing amount = 0 | 7 d | never | 0 |
| F36 | suspicious_incoming_ratio | incoming amount from suspicious sources / incoming amount | 7 d | regime `RISK_FEATURES_UNAVAILABLE` | UNAVAILABLE |
| F37 | suspicious_outgoing_ratio | outgoing amount to suspicious destinations / outgoing amount | 7 d | regime `RISK_FEATURES_UNAVAILABLE` | UNAVAILABLE |
| F38 | unique_counterparty_count | distinct counterparties, any direction | 7 d | never | 0 |
| F39 | counterparty_turnover_ratio | F38 / max(transaction count in window, 1) | 7 d | never | 0 |
| F40 | incoming_outgoing_velocity_ratio | incoming count / max(outgoing count, 1) | 24 h | never | 0 |
| F41 | amount_to_count_ratio | total amount any direction / max(count, 1) | 7 d | never | 0 |
| F42 | activity_span_hours | `(max t − min t) / 3600`, any direction | lifetime | never | 0 |

"No usable snapshot" means no READY snapshot of the account's dataset has `data_cutoff ≤ T` (§10.4).

## 10.2 Formula Conventions and Feature Regime

- Ratios MUST be finite. Caps are part of the registry and covered by `definition_hash`.
- Successive gaps are computed after `(timestamp, transaction_id)` ordering.
- A **suspicious account** is defined in §3.5. No missing assessment implies suspicion.
- **Feature regime.** Under the frozen regime `RISK_FEATURES_UNAVAILABLE` (DEC-03), F19, F31, F33, F36, and F37 are `UNAVAILABLE` for every observation in training and at inference. The regime is recorded in `model_versions.feature_regime`. Introducing a regime that populates them from an earlier scoring run requires an SRS revision, a new regime value, and a retrained model.

## 10.3 Feature Value States and Encoding

```text
OBSERVED   — computed from data
ZERO       — computed and equal to 0 because there was no qualifying activity
UNAVAILABLE — cannot be computed (no snapshot, regime, insufficient history)
NOT_APPLICABLE — undefined for this account type
```

Zero is not missing. Investigator APIs return the state. Model vectors encode `UNAVAILABLE` and `NOT_APPLICABLE` as IEEE NaN (XGBoost native missing value) in both training and inference; `OBSERVED` and `ZERO` are encoded as their numeric value. No other imputation is applied.

## 10.4 Historical Cutoff

For observation time `T`, no feature may use information with event time after `T`. Graph features use the latest READY snapshot of the dataset whose `data_cutoff ≤ T` (operational or training-split). Transactional features filter `timestamp ≤ T`. If no usable snapshot exists, graph-dependent features are `UNAVAILABLE`.

## 10.5 Feature Registry Integrity

Each registry entry also records `description`, `datatype`, `unit`, `direction`, `cap`, and `leakage_risk`. Changing any formula, source, window, cutoff, aggregation, unit, cap, null or cold-start behavior, or semantics creates a new FeatureVersion.

## 10.6 Cold Start

Accounts with no history have zero transactional count/amount features. Graph and history-dependent features are `UNAVAILABLE` unless valid historical data exists. No synthetic graph or transaction evidence may be fabricated.

## 10.7 Persistence

Every generated vector is persisted in `account_feature_values` with its state array and lineage. SHAP, investigator views, and reproducibility checks read persisted vectors; they never recompute features for a historical assessment.

---

# 11. Machine Learning

## 11.1 Model Interface

The ML layer exposes `train(...)`, `evaluate(...)`, `load_model(...)`, `predict(...)`, and `get_metadata(...)`. The initial implementation is XGBoost binary classification behind this replaceable interface.

## 11.2 Account-Level Target Contract

PaySim labels transactions, not mule accounts. MuleNetX MUST retain source label semantics and MUST NOT call the resulting target a ground-truth mule label.

**Task type.** The target is **retrospective detection** (DEC-05): "given the activity of account `a` observed in window `W`, did any of that activity carry a source fraud label?" It is not prospective prediction. There is no forward horizon `H`, no label interval after the feature cutoff, and no metric of the model may be described as a forecast.

For account `a` and observation window `W = (T_start, T_end]` (§11.4), with `tx(a, W)` = the transactions with `T_start < timestamp ≤ T_end` in which `a` is source or destination:

```text
fraud_tx_count(a, W) = |{ t ∈ tx(a, W) : t.fraud_label = TRUE }|
tx_count(a, W)       = |tx(a, W)|
labelled_tx(a, W)    = |{ t ∈ tx(a, W) : t.fraud_label IS NOT NULL }|

Y(a, W) = 1            if fraud_tx_count ≥ 1
Y(a, W) = 0            if tx_count ≥ 1 and fraud_tx_count = 0 and labelled_tx = tx_count
Y(a, W) = UNLABELLED   otherwise
```

- **Positive:** at least one transaction of `a` in `W` is source-labelled fraudulent.
- **Negative:** `a` has at least one transaction in `W`, none is labelled fraudulent, and every one carries a label.
- **Unlabelled:** no transaction in `W`, or some transaction in `W` lacks a label. Unlabelled observations are dropped from training and evaluation and MUST NOT be converted to negative.
- **Excluded** (reason retained in training metadata): accounts of type `MERCHANT` (they never carry PaySim fraud labels and would inflate negatives); invalid data quality; accounts assigned to an earlier split (§11.5); synthetic-injection datasets (§7.10).

**Feature/label separation.** Features for the observation `(a, W)` are computed at cutoff `T = T_end` from history with `timestamp ≤ T_end` (§10.4). Because the task is retrospective, the transactions that determine `Y` lie inside the feature history by design. What separates features from the label is the **label column, not time**: `fraud_label` and every field derived from it (`isFlaggedFraud`, any fraud count or rate, any risk-derived feature under regime `RISK_FEATURES_UNAVAILABLE`) MUST NOT enter the feature pipeline (§11.6 checks 4–5). Features MAY use the non-label attributes (amount, type, timestamp, counterparties) of the labelled transactions.

## 11.3 Prediction Semantics

```text
fraud_probability ∈ [0, 1]
```

It is the model's estimate of `P(Y = 1 | features at T_end)`. It is not a mule probability, criminal probability, or confirmed fraud. At inference, the operational scoring run applies the same definition with `W` = the dataset's observation window up to the snapshot's `data_cutoff`: it scores activity already observed, not future behavior.

## 11.4 Observation Construction

Split boundaries are event times `T_0 < T_train < T_val < T_test`, where `T_0` is the dataset's earliest timestamp and `T_test` its latest. The baseline sets `T_train` and `T_val` at the 70th and 85th percentiles of transaction timestamps, rounded down to the dataset timestamp resolution `r`.

| Split | Window `W_k` | Feature cutoff | Graph snapshot |
|---|---|---|---|
| train | `(T_0 − r, T_train]` | `T_train` | TRAINING_SPLIT, `data_cutoff = T_train` |
| val | `(T_train, T_val]` | `T_val` | TRAINING_SPLIT, `data_cutoff = T_val` |
| test | `(T_val, T_test]` | `T_test` | TRAINING_SPLIT, `data_cutoff = T_test` |

- The label of every observation in split `k` uses only transactions in `W_k`.
- The population of split `k` is the accounts with at least one transaction in `W_k`, minus exclusions and minus accounts already assigned to an earlier split (§11.5). Consequently an account's feature history and its label window both start at its first transaction in `W_k`, and no label from a later split can reach an earlier split's model inputs.
- Each account contributes exactly one observation.

ModelVersion records `target_definition_id`, `target_semantics = RETROSPECTIVE_DETECTION`, the window table above, `positive_rule`, `negative_rule`, `unlabelled_rule`, `exclusion_rules`, `label_source`, and per-split class distribution.

## 11.5 Dataset Splitting and Entity Separation

The split is chronological (§11.4). Each account is assigned to the **first** split in which it has a transaction and is excluded from later splits, so no account contributes observations to more than one split. Random account splitting is permitted only as a separately versioned configuration with recorded justification.

## 11.6 Leakage Controls

Training MUST run and record these checks; any failure blocks model registration:

1. no feature input has event time after its observation's `T_end`;
2. every graph feature comes from a snapshot with `data_cutoff ≤ T`;
3. no account appears in more than one split;
4. `fraud_label`, `isFlaggedFraud`, and balance columns are absent from the feature pipeline;
5. no risk-derived feature is populated under regime `RISK_FEATURES_UNAVAILABLE`;
6. test-split rows were not used for training or early stopping;
7. no observation's label uses a transaction outside its split window `W_k`.

## 11.7 Imbalance

The baseline uses `scale_pos_weight = negatives / positives` computed on the training partition only. Resampling requires a new model configuration and version.

## 11.8 Baseline XGBoost Configuration

```text
objective        = binary:logistic
eval_metric      = logloss
n_estimators     = 300
max_depth        = 6
learning_rate    = 0.05
subsample        = 0.8
colsample_bytree = 0.8
random_seed      = 42
tree_method      = hist
nthread          = 1   (reference tier, for bit-reproducibility)
missing          = NaN
```

These are engineering defaults, not claims of optimality. No early stopping in the baseline.

## 11.9 Reproducibility

ModelVersion retains seed, dataset, feature version, feature regime, target definition, hyperparameters, runtime and library versions, implementation version, evaluation metrics, artifact reference and SHA-256, split boundaries, snapshot IDs, and class distribution. Retraining with identical inputs on the reference tier MUST produce an artifact whose predictions match to 1e-9 on the test split.

## 11.10 Model Evaluation

Required on the validation and test splits: prevalence, precision, recall, F1, ROC-AUC, PR-AUC (with prevalence shown as its baseline), precision at the top 100 and top 1% of scores, confusion matrix, false-positive rate, and false-negative rate. The operating threshold is chosen on the validation split (baseline: maximize F1) and recorded. It is not a criminality threshold.

## 11.11 Artifact Compatibility

At load, MLService verifies `artifact_sha256`, `feature_version`, `feature_regime`, target definition, and interface version against the scoring request. Any mismatch rejects inference (`ml_score` unavailable, reason `MODEL_INCOMPATIBLE`).

## 11.12 Inference Failure

If inference fails or no compatible model exists:

```text
ml_score = NULL, signal_availability.ml = UNAVAILABLE
```

The assessment is still produced with the remaining components (§12.8). Historical scores remain explicitly historical and are never substituted as current.

---

# 12. Risk Scoring

## 12.1 Score Layers and Evaluation Order

Within one scoring run, for every account, in this order:

```text
1. ml_score                 (§11)
2. graph_signal_score       (§12.3)
3. behavioral_signal_score  (§12.3)
4. rule_signal_score        (§12.5)
5. pre_propagation_score    (§12.4)
6. propagated_risk          (§13, using pre_propagation_score of sources)
7. final_score              (§12.4)
8. risk_tier                (§12.6)
```

No step reads the output of a later step. Steps 1–5 are independent per account; step 6 reads step 5 of other accounts in the same run.

## 12.2 Baseline Configuration

These values are baseline engineering parameters, not calibrated real-world AML truth, regulatory thresholds, or claims of effectiveness.

### Weights

```text
w_ml = 0.50   w_g = 0.20   w_b = 0.15   w_p = 0.10   w_r = 0.05     Σw = 1.00
```

### Component normalization

| Input | Normalization to [0,1] |
|---|---|
| Bounded ratios (F20, F25, F28, F29, F30, F35, F39) | identity |
| Non-negative counts and rates (F21, F22, F32, F38) | `x / (x + m)` where `m` is the median of the strictly positive values of that feature over the training population; if there are no positive values, the input is 0 |
| Degree, component size, community size (F11, F12, F13, F16, F17) | `log1p(x)`, then percentile rank against the normalization reference |
| Unbounded non-negative ratios (F09, F26, F40) | `log1p(x)`, then percentile rank against the normalization reference |
| PageRank, betweenness (F14, F15) | percentile rank within the snapshot (§8.4) |
| Binary rules | 0 or 1 contribution |
| Unavailable input | excluded from its component's mean; the component's availability records it |

The **normalization reference** is the per-feature empirical distribution over the training population at `T_train`, stored as a 101-point quantile table (and the median `m`) in `risk_logic_versions.normalization_reference`. Percentile rank against the reference is linear interpolation between the bracketing quantiles, clamped to [0,1].

## 12.3 Component Scores

```text
graph_signal_score      = mean of normalized available inputs in G_SET
behavioral_signal_score = mean of normalized available inputs in B_SET

G_SET = {F11, F12, F13, F14, F15, F16, F17, F32}
B_SET = {F09, F20, F21, F22, F25, F26, F28, F29, F30, F35, F38, F39, F40}
```

Each input has equal weight within its component. If every input of a component is unavailable, the component is 0 and marked `UNAVAILABLE`. Risk-derived features (F19, F31, F33, F36, F37) are not part of G_SET or B_SET. Flow features are part of the behavioral layer; a new independent risk component requires an SRS revision.

## 12.4 Deterministic Composition

```text
pre_propagation_score = 0.50·ml_score + 0.20·graph_signal_score
                      + 0.15·behavioral_signal_score + 0.05·rule_signal_score

final_score = clamp(pre_propagation_score + 0.10·propagated_risk, 0, 1)
```

An unavailable `ml_score` contributes 0. This is algebraically identical to the v1.3.2 formula:

```text
final_score = clamp(0.50·ml + 0.20·g + 0.15·b + 0.10·p + 0.05·r, 0, 1)
```

Formula identifier: `weighted-normalized-v1`.

Arithmetic is performed in decimal and rounded half-even to 7 decimal places **before** tier assignment, so that boundary values are assigned identically by every implementation. Because `propagated_risk ≤ 0.50`, the maximum attainable `final_score` for valid inputs is 0.95.

## 12.5 Rule Configuration

| Rule | Condition | Contribution | Priority |
|---|---|---|---|
| R01 | `rapid_in_out_ratio (F28) ≥ 0.80` AND outgoing amount in the 24 h window > 0 | 0.80 | 30 |
| R02 | `short_interval_ratio (F25) ≥ 0.75` AND `velocity_24h (F21) ≥ 10` | 0.70 | 20 |
| R03 | `suspicious_incoming_ratio (F36) ≥ 0.60` | 0.60 | 10 |
| R04 | `suspicious_outgoing_ratio (F37) ≥ 0.60` | 0.60 | 10 |
| R05 | `reachable_suspicious_accounts (F31) ≥ 5` | 0.50 | 5 |

A rule whose input is `UNAVAILABLE` does not fire. Under regime `RISK_FEATURES_UNAVAILABLE`, R03–R05 never fire. `rule_signal_score` is the maximum contribution among fired rules (0 if none), capped at 1.0. Priority only orders explanations.

## 12.6 Risk Tiers

```text
LOW       [0.00, 0.25)
MEDIUM    [0.25, 0.50)
HIGH      [0.50, 0.75)
CRITICAL  [0.75, 1.00]
```

Baseline engineering thresholds. Boundaries are acceptance-tested on the rounded value (§12.4).

## 12.7 Risk Logic Version

`RiskLogicVersion` contains the formula identifier, weights, G_SET and B_SET, normalization methods and reference, rules, tier thresholds, propagation parameters, and ring/candidate parameters. Any change creates a new version.

## 12.8 Cold Start and Missing Signals

Unavailable components contribute 0 under the baseline; weights are not renormalized. Raw feature and assessment metadata retain `UNAVAILABLE`; no fabricated observation is inserted. The risk API returns `signal_coverage` (weight share of available components) and `max_attainable_score` (the score the account would have with every unavailable component at 1) so that a low score caused by missing data is visible.

## 12.9 Historical Risk

RiskAssessment is append-only. Re-scoring creates a new scoring run and new assessments. The account projection points to the assessment of the active scoring run (§6.9).

## 12.10 Risk Terminology

| Name | Meaning |
|---|---|
| `ml_score` | model fraud probability in [0,1] |
| `graph_signal_score` | normalized graph-derived signal |
| `behavioral_signal_score` | normalized temporal/behavioral signal |
| `rule_signal_score` | normalized configured-rule signal |
| `pre_propagation_score` | composition without the propagated term |
| `propagated_risk` | bounded propagated analytical risk |
| `final_score` | analytical risk score after composition and clamping |
| `risk_tier` | categorical interpretation of `final_score` |

The legacy names `graph_adjustment`, `behavioral_adjustment`, and `rule_adjustment` MUST NOT be used in code, APIs, or columns.

---

# 13. Risk Propagation

## 13.1 Purpose

Risk propagation provides bounded network context. It never replaces or modifies `ml_score`.

## 13.2 Parameters and Algorithm

```text
maximum_distance      = 3
decay                 = 1 / (1 + d)
maximum_contribution  = 0.50
source_condition      = pre_propagation_score ≥ 0.50 in the same scoring run
source_signal s       = the source's pre_propagation_score
adjacency             = undirected account projection of the scoring run's snapshot
```

```text
contribution(source, d) = min(s · 1/(1+d), 0.50)
propagated_risk(a)      = max over sources ≠ a within distance ≤ 3 of contribution(source, d_min(source, a))
                          (0 if none)
```

`d_min` is the shortest-path hop distance. Because `s/(1+d)` decreases in `d`, the maximum over all simple paths is attained at `d_min`; the implementation therefore uses one bounded breadth-first search per source (depth ≤ 3), keeping per receiving account the best contribution. Ties in contribution are broken by smaller `d`, then smaller `source_account_id`. An account is never its own source.

The max-based aggregation prevents additive amplification. With `s ≤ 0.95` and `d ≥ 1`, the 0.50 cap does not bind for valid inputs; it is retained as a safety bound.

## 13.3 Provenance

For each receiving account with `propagated_risk > 0`, up to `propagation_provenance_top_n` contributions are persisted in `propagation_contributions` (source account, source assessment, distance, source score, decay, contribution, rank). Rank 1 is the winning source.

## 13.4 Safety

Propagation MUST terminate on cyclic graphs, remain bounded, preserve source provenance, and never overwrite the ML score.

---

# 14. Explainability

## 14.1 SHAP

SHAP (TreeSHAP for the XGBoost model) is the model-level explanation mechanism. An explanation exposes, for each of the 42 features: feature ID and name, value and state, SHAP contribution, direction, and relative importance (`|shap| / Σ|shap|`). The explainer variant and output space (log-odds) are frozen per model version.

## 14.2 Computation and Persistence

Explanations are computed **on demand** from the persisted feature vector of the assessment (`account_feature_values`) and the assessment's model artifact, then cached in `shap_explanations`. Computing an explanation never recomputes features. A missing model artifact returns `503 MODEL_UNAVAILABLE`; an assessment without an ML score returns `404 EXPLANATION_NOT_AVAILABLE`.

## 14.3 Version Consistency

An explanation MUST reference the same `model_version`, `feature_version`, and `assessment_id` as the prediction it explains. Mismatch returns `409 EXPLANATION_VERSION_MISMATCH`.

## 14.4 Semantics

SHAP explains the model's `ml_score`, which carries 50% of `pre_propagation_score`. It does not explain the other risk components and is not proof of fraud or criminality. The UI MUST show the SHAP panel as an explanation of the ML component only.

---

# 15. Temporal and Behavioral Intelligence

## 15.1 Timestamp Convention

Canonical timestamps are UTC `TIMESTAMPTZ` event times (§3.4). Ordering is always `(timestamp, transaction_id)`. Hour buckets are UTC-aligned.

## 15.2 Temporal Formula Contract

The temporal features are F21–F30 of §10.1, which is the single normative definition. Windows are half-open `(T − w, T]`. No comparison window extends beyond `T`.

## 15.3 Rapid In/Out

An inbound transaction at time `t` is **rapidly followed** when an outbound transaction from the same account occurs in `[t, t + 3600 s]`. Matching is greedy in `(timestamp, transaction_id)` order: each inbound event is matched to the earliest unmatched eligible outbound event, and each outbound event is matched at most once. `rapid_events` is the number of matched inbound events whose inbound timestamp lies in the 24 h window.

## 15.4 Burst

Transactions are bucketed by UTC hour. The 7-day window contains exactly 168 buckets ending with the bucket that contains `T`; empty buckets are included in the mean.

## 15.5 Dormancy

`dormancy_to_activity = activity_24h / max(mean_daily_activity_prev30d, 1)`, where `activity_24h` is the transaction count in `(T − 24 h, T]` and `mean_daily_activity_prev30d` is the count in `(T − 31 d, T − 24 h]` divided by 30. The feature is `UNAVAILABLE` unless the prior 30-day period has at least 7 distinct active UTC days.

## 15.6 Cyclic Activity

A **cycle event** for account `a` is a transaction involving `a` that belongs to a time-ordered directed simple cycle through `a` of length 2 to 5 hops, with non-decreasing timestamps along the cycle and total span ≤ 24 h, lying wholly inside the 7-day window. Each transaction is counted once regardless of how many cycles contain it.

## 15.7 Short-Lived Activity

An active period starts at an account's first transaction, or at a transaction preceded by at least 24 h of inactivity. It ends at the last transaction before a gap of at least 24 h. A period is **completed** if a gap of at least 24 h follows it before `T`. A completed period is short-lived when its duration is ≤ 72 h.

## 15.8 Investigator Exposure

Temporal outputs include feature ID and name, value, state, window, cutoff `T`, `computed_at`, feature version, and availability.

## 15.9 Temporal Behavioral Motifs

Motifs are explicit, interpretable pattern detections computed in the ANALYTICS stage over all transactions of the snapshot. Temporal features remain the quantitative signals. A motif is an analytical pattern, not a criminality classification.

### 15.9.1 Common Detection Contract

1. **Ordering.** Transactions are processed in `(timestamp, transaction_id)` order.
2. **Path motifs** (`RAPID_PASS_THROUGH`, `CIRCULAR_FLOW`, `LAYERED_MOVEMENT`) are sequences of transactions `t_1 … t_k` where the destination of `t_i` is the source of `t_{i+1}`, timestamps are **non-decreasing** (equal timestamps allowed), and accounts are distinct except where the motif closes a cycle.
3. **Ambiguous order.** If two consecutive hops have equal timestamps, the instance is still emitted and `order_ambiguous = TRUE`, because the source data cannot establish their true order (for PaySim, all transactions within one `step` share a timestamp).
4. **Maximality** (path motifs). All qualifying sequences are enumerated; a sequence is then discarded if its transaction sequence is a contiguous subsequence of another qualifying sequence of the same type. Only maximal sequences are persisted.
5. **Window motifs** (`FAN_IN`, `FAN_OUT`) use greedy non-overlapping segmentation per anchor account (§15.9.3).
6. **Bounds.** Enumeration uses `analytic_max_depth` (5) and a deterministic budget of `motif_max_expansions_per_anchor` (baseline 100,000) expansions per anchor account. Exhausting the budget stops enumeration for that anchor deterministically and sets `evidence.truncated = TRUE`. No detector performs unbounded traversal.
7. **Identity.** `motif_id` is deterministic (§6.2.3); identical instances collapse.
8. **Anchor.** Each instance has one `anchor_account_id`, defined per type below. Investigator queries by account match any participating account.

### 15.9.2 Rapid Pass-Through

```text
A → B → C (→ …)
```

A path motif of 2 to 5 hops in which every successive gap `ts_{i+1} − ts_i` is between 0 and 900 seconds. Anchor: first source account. Window: 900 s per hop.

### 15.9.3 Fan-In and Fan-Out

```text
A ─┐                    → B
B ─┼→ D           A ───→ C
C ─┘                    → D
```

For each destination account `d` (fan-in) or source account `s` (fan-out), take its inbound (or outbound) transactions in order and segment them greedily:

1. Let `i` be the first unprocessed transaction, at time `t_i`.
2. Let `S` be the transactions in `[t_i, t_i + 3600 s]`.
3. If `S` contains at least 3 distinct counterparties, emit one instance containing, for each counterparty, its earliest transaction in `S`; mark every transaction in `S` processed; continue from the first transaction after `t_i + 3600 s`.
4. Otherwise mark only transaction `i` processed and continue.

Anchor: `d` for fan-in, `s` for fan-out. Window: 3600 s.

### 15.9.4 Circular Flow

```text
A → B → C → A
```

A path motif of 3 to 5 hops that returns to its first account, with all intermediate accounts distinct and total span ≤ 86,400 s. Anchor: first account. Cycle existence alone is not proof of suspiciousness.

### 15.9.5 Layered Movement

```text
A → B → C → D → E
```

A path motif of 4 or 5 hops through distinct accounts with total span ≤ 86,400 s. Anchor: first account. The system MUST NOT state that the accounts intended to obscure funds unless independent evidence supports it.

### 15.9.6 Burst Activity

For each account and each UTC hour bucket `h`, an instance is emitted when the account's transaction count in `h` is at least 5 **and** at least `3 × max(mean, 1)`, where `mean` is the mean hourly count over the 168 buckets ending with `h`, empty buckets included. Participants are the account and its distinct counterparties in `h`. Anchor: the account. Window: 3600 s.

### 15.9.7 Motif Confidence

`motif_confidence` is a deterministic pattern-strength score in [0,1]. It is NOT a fraud probability, mule probability, account-risk score, or criminality probability.

```text
structural_match  = min(1, observed_required_structure / required_structure)
temporal_match    = max(0, 1 − observed_span_seconds / configured_window_seconds)
participant_match = min(1, distinct_participants / expected_minimum_participants)
motif_confidence  = mean(structural_match, temporal_match, participant_match)
```

| Motif type | required_structure | expected_minimum_participants | configured_window_seconds | observed_required_structure |
|---|---:|---:|---:|---|
| RAPID_PASS_THROUGH | 2 hops | 3 | 900 per hop | hops, capped at 5 |
| FAN_IN | 3 inbound relationships | 4 | 3600 | distinct sources |
| FAN_OUT | 3 outbound relationships | 4 | 3600 | distinct destinations |
| CIRCULAR_FLOW | 3 hops | 3 | 86400 | hops, capped at 5 |
| LAYERED_MOVEMENT | 4 hops | 5 | 86400 | hops, capped at 5 |
| BURST_ACTIVITY | 5 transactions | 3 | 3600 | transactions in the bucket; `temporal_match = 1` |

For `RAPID_PASS_THROUGH`, `temporal_match` is the mean over hops of `max(0, 1 − g_i / 900)`. Zero denominators yield 0 with an unavailable flag. All values are clamped to [0,1].

**Interpretation note.** Every instance that passes detection already satisfies the structural and participant minimums, so for five of the six types confidence equals `(2 + temporal_match) / 3` and lies in [2/3, 1]. Instances whose transactions share one timestamp have confidence 1. The UI MUST display the temporal component next to the confidence and MUST NOT present confidence as a discriminating risk measure.

**Evidence** includes selected transactions, participating accounts, timestamp sequence, configured thresholds, the parameter values above, component values, final confidence, `order_ambiguous`, `truncated`, and detector version.

### 15.9.8 Multiple Motifs

A transaction or account may participate in several motif instances and types. Distinct patterns are not deduplicated merely because they share accounts. Only identical instances (same type, window, and transaction set) collapse.

---

# 16. Money-Flow Analysis

## 16.1 Graph Representation

Traversal operates over the `TRANSFERRED_TO` account projection of one snapshot (§6.8.1). Supporting transactions are read from `Transaction` nodes or PostgreSQL.

## 16.2 Path Algorithm

- Shortest-path mode: breadth-first search by hop count.
- Multi-path mode: depth-first enumeration of simple paths, expanding neighbors in ascending `account_id` order.
- Path length counts account-to-account hops.

Client-supplied Cypher is never accepted.

## 16.3 Simple-Path Rule

A path is simple: no account occurs twice. Source-to-destination queries reject identical source and destination IDs (`400 INVALID_PATH_REQUEST`).

## 16.4 Duplicate Handling

Parallel transactions between the same ordered pair collapse to one hop for traversal. All supporting transaction IDs are retained as evidence in `(timestamp, transaction_id)` order.

## 16.5 Ordering

Paths are ordered by:

1. path length ascending;
2. total supporting amount descending (sum over hops of the hop's total amount);
3. lexicographic account-ID sequence;
4. lexicographic sequence of the first supporting transaction ID of each hop.

## 16.6 Weighted vs Unweighted

Traversal is unweighted: every hop costs one. Amount ranks equal-length paths but never changes path length. Amount-weighted traversal requires a new algorithm version and SRS revision.

## 16.7 Bounds

### 16.7.1 Interactive bounds (API)

```text
max_depth     = 5
max_results   = 50
query_timeout = 5 seconds
```

These apply to `/graph/path`. A request above a limit is rejected with `400 LIMIT_EXCEEDED` (reject policy; no silent clamping). A timeout returns `408 QUERY_TIMEOUT` with no partial result.

### 16.7.2 Analytical bounds (ring, intervention, motif, feature computation)

```text
analytic_max_depth       = 5
analytic_max_paths       = 10,000 per scope
analytic_max_expansions  = 1,000,000 per scope
```

Analytical enumeration is bounded only by these deterministic counters, never by wall-clock time. When a counter is exhausted, enumeration stops at a deterministic point (enumeration order of §16.2) and the result records `truncated = TRUE`. The job's wall-clock limit (§7.8) aborts the job to `FAILED`; it never yields partial results. Interactive limits MUST NOT be applied to analytical computations.

## 16.8 Response

Each returned path includes `path_id` (§6.2.3), `source_account_id`, `destination_account_id`, `path_length`, `accounts[]`, per-hop `transactions[]` (supporting IDs, truncated to `max_hop_evidence` (baseline 20) per hop with a total count), `timestamps[]`, `amounts[]`, `transaction_types[]`, `graph_snapshot_id`, `algorithm_version`, `applied_limits`, and `computed_at`.

## 16.9 Evidence Semantics

A path establishes topological connectivity only. Hops are not required to be time-ordered, so a path does not by itself establish that funds moved along it. It does not establish criminal intent, fraud, mule status, or collusion.

---

# 16A. Network Intervention Analysis

## 16A.1 Purpose and Boundary

Network Intervention Analysis is a deterministic counterfactual graph analysis. It evaluates bounded hypothetical graph modifications and estimates their analytical effect on suspicious flow, paths, connectivity, and network risk. Its outputs are decision support, not enforcement.

> **Network Intervention Analysis is simulation-only. MuleNetX MUST NOT block, freeze, disable, reject, reroute, modify, or otherwise interfere with any real account, transaction, payment activity, financial instrument, or external financial system.**

## 16A.2 Pipeline

```text
Ring (target) + analytical context (snapshot, scoring run)
  → enumerate the baseline set P of in-scope qualifying paths (§3.5, bounds §16.7.2)
  → baseline metrics
  → candidate generation (RANK) or validated target (EVALUATE)
  → for each candidate: residual paths = paths of P not touching the target
  → residual metrics → normalization → intervention score → deterministic rank
  → evidence and reproducibility record
```

Scenarios are always executed asynchronously as `INTERVENTION` jobs (§7.8).

## 16A.3 Operations and Modes

Four hypothetical operation types:

1. `ACCOUNT_REMOVAL` — remove one account and its incident edges from the simulated graph.
2. `INTERMEDIARY_REMOVAL` — the same operation for an account that is a non-endpoint on at least one baseline qualifying path; the type records that provenance.
3. `ACCOUNT_SET_REMOVAL` — remove 1 to `k_max` distinct accounts.
4. `EDGE_REMOVAL` — remove one account-projection edge `(u, v)`; its identifier is `edge_id = "{u}>{v}"`. All canonical transactions are unchanged.

Two modes:

- **`RANK`**: the server generates every eligible single-account and single-edge candidate and ranks them. `ACCOUNT_SET_REMOVAL` is not generated in this mode.
- **`EVALUATE`**: the request names one operation type and its targets; the server validates eligibility and computes that candidate only (`rank_position = 1`).

Mixed account-plus-edge interventions and network-scoped (non-ring) scenarios are out of MVP scope.

## 16A.4 Candidate Generation and Budget

### 16A.4.1 Candidate pool (RANK)

From the baseline path set `P`:

- **Account candidates:** every account that appears on at least one path of `P` (members and non-members). Each account yields exactly one candidate: `INTERMEDIARY_REMOVAL` if it is a non-endpoint on at least one path of `P`, otherwise `ACCOUNT_REMOVAL`.
- **Edge candidates:** every account-projection edge used by at least one path of `P`.

No account or edge outside `P` is eligible. If the pool exceeds `intervention_max_candidates` (baseline 5,000), the scenario fails with `failure_category = LIMIT_EXCEEDED`; no heuristic filter is applied.

### 16A.4.2 Validation (EVALUATE)

`ACCOUNT_REMOVAL` and `INTERMEDIARY_REMOVAL` take exactly one account that is eligible under §16A.4.1 for that type. `ACCOUNT_SET_REMOVAL` takes 1 to `k_max` distinct accounts, each appearing on at least one path of `P`. `EDGE_REMOVAL` takes exactly one edge used by a path of `P`. The server rejects empty targets, duplicates, ineligible targets, or more than `k_max` accounts with `400 INTERVENTION_TARGET_INVALID` before creating a scenario.

### 16A.4.3 Enumeration order

Before scoring, candidates are enumerated in this order (recorded as `eligible_candidate_ids`); this order does not affect ranking:

1. operation type: `ACCOUNT_REMOVAL`, `INTERMEDIARY_REMOVAL`, `ACCOUNT_SET_REMOVAL`, `EDGE_REMOVAL`;
2. account candidates: `final_score` descending (unavailable as 0), then number of paths in `P` containing the account descending, then `account_id` ascending;
3. edge candidates: `(source_account_id, destination_account_id)` ascending.

### 16A.4.4 Budget

`k_max = 3` (invariant `k_max ≤ 3`). `ACCOUNT_REMOVAL` and `INTERMEDIARY_REMOVAL` target exactly one account; `ACCOUNT_SET_REMOVAL` targets `1 ≤ |targets| ≤ k_max`; `EDGE_REMOVAL` targets one edge and consumes no account budget. No combinatorial search is performed: account-set combinations are never enumerated. A scenario evaluates at most `intervention_max_candidates` candidates in RANK mode and exactly one in EVALUATE mode.

## 16A.5 Baseline

Every scenario binds to the active (or explicitly requested) `baseline_graph_snapshot_id` and to the scoring run of that snapshot. Suspicion uses that scoring run's assessments only (§3.5). For the baseline:

- `baseline_suspicious_paths = |P|`;
- `baseline_suspicious_flow` = suspicious flow of `P` (§3.5);
- `baseline_reachable_suspicious_pairs` = distinct ordered `(first, last)` account pairs over `P`;
- `baseline_risk_mass = Σ final_score` over the suspicious account set (the suspicious accounts on at least one path of `P`);
- `baseline_paths_truncated` = whether enumeration of `P` hit an analytical bound.

If `baseline_paths_truncated` is TRUE, every candidate metric is a lower bound and every response states this.

## 16A.6 Hypothetical Graph Semantics

`G_simulated` is disposable analytical state held in worker memory. It MUST NOT modify PostgreSQL canonical records, the Neo4j graph, risk assessments, cases, findings, audit history, or external systems.

## 16A.7 Residual Computation

Removing accounts or edges cannot create new paths: every simple path of `G − X` is a simple path of `G` that avoids `X`. Therefore, for a candidate with target `X`:

```text
P_residual(X) = { p ∈ P : p contains no account in X and no edge in X }
```

Removed accounts are excluded from every residual quantity. Residual metrics are computed from `P_residual` with the same definitions as the baseline. The simulation MUST NOT recompute PageRank, betweenness, communities, graph construction, ML training, SHAP, or inference.

- **Affected paths:** `P \ P_residual(X)`.
- **Alternative paths:** paths of `P_residual(X)` whose `(first, last)` pair also occurs in an affected path.
- **Affected accounts:** accounts on affected paths, excluding `X`.

## 16A.8 Determinism

Path identity is the ordered account sequence. Supporting transactions are ordered `(timestamp, transaction_id)`. For a fixed snapshot, scoring run, ring, mode, targets, and configuration, scenario results are identical across runs and machines.

## 16A.9 Suspicious-Flow Disruption

```text
flow_disruption            = baseline_suspicious_flow − residual_suspicious_flow   (≥ 0 by §16A.7)
flow_disruption_percentage = flow_disruption / baseline_suspicious_flow
```

If `baseline_suspicious_flow = 0`: both are 0 and `flow_disruption` is listed in `unavailable_metrics`.

## 16A.10 Path Disruption

```text
normalized_path_disruption = (baseline_suspicious_paths − residual_suspicious_paths) / baseline_suspicious_paths
```

0 and unavailable when the baseline count is 0.

## 16A.11 Connectivity Disruption

Connectivity is measured on reachable suspicious pairs (§3.5).

```text
normalized_connectivity_disruption =
    (baseline_reachable_suspicious_pairs − residual_reachable_suspicious_pairs) / baseline_reachable_suspicious_pairs
```

0 and unavailable when the baseline count is 0. Connected-component membership is not an alternative MVP metric.

## 16A.12 Residual Network Risk and Risk Reduction

```text
residual_risk_mass    = Σ final_score over suspicious accounts not in X that lie on ≥ 1 path of P_residual(X)
residual_network_risk = residual_risk_mass / baseline_risk_mass
normalized_risk_reduction = clamp(1 − residual_network_risk, 0, 1)
```

If `baseline_risk_mass = 0`: `residual_network_risk = 0`, `normalized_risk_reduction = 0`, and `risk_reduction` is listed in `unavailable_metrics`. The baseline network risk is 1 by construction. This measure is monotone: removing more targets never increases residual risk. It is an analytical measure, not reduction in actual fraud or criminality.

## 16A.13 Intervention Cost

Cost is an analytical complexity proxy, not a monetary, legal, operational, or enforcement cost.

```text
ACCOUNT_REMOVAL      = 1
INTERMEDIARY_REMOVAL = 1
EDGE_REMOVAL         = 1
ACCOUNT_SET_REMOVAL  = number of removed accounts

normalized_intervention_cost = clamp(intervention_cost / k_max, 0, 1)
```

## 16A.14 Candidate Ranking

```text
intervention_score =
    clamp(
        0.45 · flow_disruption_percentage +
        0.25 · normalized_risk_reduction +
        0.20 · normalized_connectivity_disruption +
        0.10 · normalized_path_disruption −
        0.10 · normalized_intervention_cost,
        0, 1)
```

Candidates are sorted by:

1. `intervention_score` descending;
2. `flow_disruption_percentage` descending;
3. `normalized_risk_reduction` descending;
4. `intervention_cost` ascending;
5. `candidate_id` ascending (deterministic UUIDv5, §6.2.3).

All weights, bounds, and normalization semantics are recorded in `ranking_configuration` and its hash.

## 16A.15 Required Outputs

Every candidate reports: target IDs; operation type; baseline (from the scenario) and residual suspicious flow; flow disruption and percentage; baseline and residual path counts; normalized path disruption; baseline and residual reachable pairs; normalized connectivity disruption; baseline and residual risk mass, residual network risk, and normalized risk reduction; affected accounts; affected and alternative path IDs; cost and normalized cost; intervention score; rank; unavailable metrics; truncation state; evidence; and version lineage.

## 16A.16 Evidence and Reproducibility

Every scenario retains `scenario_id`, mode, `baseline_graph_snapshot_id`, `scoring_run_id`, target ring, targets, the eligible candidate list, baseline metrics, ranking configuration and hash, `analytics_version`, `risk_logic_version`, and timestamps. A result is valid only relative to its recorded baseline and versions.

## 16A.17 Safety and Non-Interference

The simulation layer has no write path to canonical account or transaction state, payment activity, external systems, or enforcement systems; InterventionService receives read-only repositories plus write access to its own two tables only. UI labels MUST identify outputs as `Hypothetical Simulation`. The copilot may summarize results but MUST NOT execute, authorize, or convert a hypothetical candidate into a real-world action.

---

# 17. Investigation Workflow

## 17.1 Golden Investigation Flow

```text
Flagged account → Account review → Graph exploration → Risk / SHAP
 → Temporal analysis → Behavioral motifs → Money flow
 → Related accounts / community → Ring intelligence → Ring evidence review
 → Intervention simulation (hypothetical) → Ranked hypothetical interventions
 → Findings → Case (with subjects) → Resolution
```

## 17.2 Case State Machine

```text
OPEN → IN_REVIEW
IN_REVIEW → ESCALATED | RESOLVED | FALSE_POSITIVE
ESCALATED → IN_REVIEW | RESOLVED | FALSE_POSITIVE
RESOLVED → CLOSED
FALSE_POSITIVE → CLOSED
```

`CLOSED` is terminal and sets `closed_at`. The backend MUST enforce valid transitions; invalid ones return `409 INVALID_CASE_TRANSITION`.

## 17.3 Transition and Field Authorization

Every case mutation validates the current state, target state, authenticated principal, role, and the ownership rules of §22.2. A principal is a case's **participant** if it created the case or is its assignee.

## 17.4 Case Subjects

Accounts, transactions, rings, and intervention scenarios are linked to a case as subjects (`case_subjects`). Adding validates that the subject exists. Removal is soft and keeps history. Subjects cannot be changed on a `CLOSED` case.

## 17.5 Findings and Evidence

Findings are investigator-authored, append-only records. They MUST remain distinct from model predictions and analytical signals. Evidence references are validated to exist at creation. Findings cannot be added to a `CLOSED` case.

---

# 18. Backend Architecture

## 18.1 Service Ownership

| Service | Owns | Reads | Writes |
|---|---|---|---|
| IngestionService | validation, normalization, staging, canonical insert | upload, PG | `datasets`, `ingestion_runs`, `accounts`, `transactions` |
| ProfilingService | dataset profile | PG | `dataset_profiles` |
| JobService | job queue, leases, pipeline state machine | PG | `jobs`, `pipeline_runs` |
| AccountService | account read model | PG | none (projection written only by activation) |
| TransactionService | transaction read model | PG | none |
| GraphService | Neo4j build, validation, retirement, bounded traversal | PG, Neo4j | Neo4j, `graph_snapshots` |
| AnalyticsService | graph algorithms, communities | PG (projection export), Neo4j (benchmark tier) | `analytics_runs`, `account_graph_metrics`, `communities`, `community_memberships` |
| TemporalMotifService | motif detection | PG | `temporal_motifs` |
| FeatureService | feature vectors | PG | `feature_versions`, `account_feature_values` |
| MLService | training, inference, artifact compatibility | PG, artifacts | `model_versions`, artifacts |
| ExplainabilityService | on-demand SHAP | PG, artifacts | `shap_explanations` |
| RiskService | component scores, composition, tiers | PG | `scoring_runs`, `risk_assessments` |
| PropagationService | bounded propagation | PG (projection) | `propagation_contributions` |
| MoneyFlowService | path queries and analytical enumeration | Neo4j or in-memory projection | none |
| RingIntelligenceService | candidates, rings, ring features, ring risk | PG | candidate and ring tables |
| InterventionService | scenarios and candidates | PG, in-memory projection | `intervention_scenarios`, `intervention_candidates` only |
| EvaluationService | multi-level evaluation | PG | `evaluation_runs`, `evaluation_metrics` |
| InvestigationService | cases, subjects, findings | PG | `cases`, `case_subjects`, `findings` |
| AIService | context assembly, LLM orchestration, output validation | other services (read) | none |
| AuthService | login, sessions, users | PG | `users`, `auth_sessions` |
| AuditService | audit events | — | `audit_events` |

API routes call application services only. Routes MUST NOT implement analytical formulas.

## 18.2 Repository Boundaries

Each table group has a repository interface. Graph access is isolated behind GraphService's adapter. InterventionService and AIService receive read-only repository facades.

## 18.3 Route Responsibilities

API routes MUST: authenticate; authorize; validate input; call the application service; serialize output; map errors to the envelope of §19.3; maintain request correlation.

---

# 19. API Specification

## 19.1 Conventions

- Base path `/api/v1`. `/health` and `/ready` are outside the base path and public.
- All other endpoints require authentication.
- Every request receives a `request_id` (client-supplied `X-Request-ID` if it is a valid UUID, otherwise generated), returned in the `X-Request-ID` header and in error bodies.
- Unless stated, read endpoints default to the active context (§6.9). Endpoints returning analytical data accept optional lineage parameters (`scoring_run_id`, `analytics_run_id`, `graph_snapshot_id`) to read history.
- Asynchronous operations return `202` with a resource or job identifier and are polled.
- Above-limit parameters are rejected with `400 LIMIT_EXCEEDED`; the server never silently clamps.

## 19.2 Endpoint Contract Matrix

Permission names refer to §22.2. Timeouts are server-side targets; exceeding one returns `408`.

### Operations and authentication

| Method | Path | Permission | Request | Success | Errors | Limits | Timeout |
|---|---|---|---|---|---|---|---|
| GET | `/health` | public | — | 200 | — | — | 250 ms |
| GET | `/ready` | public | — | 200 | 503 | — | 250 ms |
| POST | `/api/v1/auth/login` | public | username, password | 200 | 400, 401, 429 | body ≤ 4 KB | 2 s |
| POST | `/api/v1/auth/logout` | authenticated | — | 204 | 401 | — | 2 s |
| GET | `/api/v1/auth/me` | authenticated | — | 200 | 401 | — | 1 s |
| GET | `/api/v1/users` | user.read | page, page_size | 200 | 403 | page ≤ 100 | 2 s |
| POST | `/api/v1/users` | user.manage | username, role, initial password | 201 | 400, 403, 409 | body ≤ 4 KB | 2 s |
| PATCH | `/api/v1/users/{id}` | user.manage / role.manage | role?, is_active?, password? | 200 | 400, 403, 404 | body ≤ 4 KB | 2 s |

### Datasets, ingestion, pipelines, models

| Method | Path | Permission | Request | Success | Errors | Limits | Timeout |
|---|---|---|---|---|---|---|---|
| POST | `/api/v1/ingestion` | ingestion.create | multipart file + name, source, dataset_version, schema_version, adapter, adapter_config | 202 | 400, 409, 413, 415 | file ≤ `max_upload_bytes` | 30 s (acceptance only) |
| GET | `/api/v1/ingestion` | ingestion.read | filters, page, page_size | 200 | 400 | page ≤ 100 | 2 s |
| GET | `/api/v1/ingestion/{id}` | ingestion.read | — | 200 | 404 | — | 2 s |
| GET | `/api/v1/datasets/{id}/profile` | ingestion.read | — | 200 | 404 | — | 2 s |
| GET | `/api/v1/pipeline-runs` | pipeline.read | dataset_id?, state?, page | 200 | 400 | page ≤ 100 | 2 s |
| GET | `/api/v1/pipeline-runs/{id}` | pipeline.read | — | 200 | 404 | — | 2 s |
| POST | `/api/v1/pipeline-runs` | pipeline.control | dataset_id | 202 | 400, 409 | — | 2 s |
| POST | `/api/v1/pipeline-runs/{id}/retry` | pipeline.control | — | 202 | 404, 409 | — | 2 s |
| GET | `/api/v1/models` | model.read | page | 200 | — | page ≤ 100 | 2 s |
| GET | `/api/v1/models/{version}` | model.read | — | 200 | 404 | — | 2 s |
| GET | `/api/v1/context` | account.read | — | 200 | — | — | 1 s |

`POST /api/v1/ingestion` streams the upload to the staging volume, computes the checksum, checks the header, creates the dataset, ingestion run, and pipeline run, enqueues the INGEST job, and returns `202` with `dataset_id`, `ingestion_run_id`, `pipeline_run_id`, and status. Large reference files MAY instead be registered with the CLI command `mulenetx ingest --path …`, which follows the same contract. `GET /api/v1/context` returns the active context (§6.9).

### Accounts, transactions, risk

| Method | Path | Permission | Request | Success | Errors | Limits | Timeout |
|---|---|---|---|---|---|---|---|
| GET | `/api/v1/accounts` | account.read | q (exact or prefix of source ref), risk_tier, account_type, page, page_size, sort, order | 200 | 400 | page ≤ 100 | 2 s |
| GET | `/api/v1/accounts/{id}` | account.read | — | 200 | 404 | — | 1 s |
| GET | `/api/v1/accounts/{id}/transactions` | transaction.read | start, end, type, direction, page_size, cursor | 200 | 400, 404 | page ≤ 100; range ≤ `max_transaction_range` | 2 s |
| GET | `/api/v1/accounts/{id}/risk` | risk.read | scoring_run_id? | 200 | 404, 503 | — | 2 s |
| GET | `/api/v1/accounts/{id}/risk/history` | risk.read | page | 200 | 404 | page ≤ 100 | 2 s |
| GET | `/api/v1/accounts/{id}/risk/propagation` | risk.read | scoring_run_id? | 200 | 404 | ≤ top_n | 2 s |
| GET | `/api/v1/accounts/{id}/shap` | shap.read | assessment_id?, top_n? | 200 | 404, 409, 503 | top_n ≤ 50 | 3 s |
| GET | `/api/v1/accounts/{id}/features` | risk.read | scoring_run_id? | 200 | 404 | — | 2 s |
| GET | `/api/v1/accounts/{id}/temporal` | temporal.read | scoring_run_id? | 200 | 404 | — | 2 s |
| GET | `/api/v1/accounts/{id}/motifs` | motif.read | type?, start?, end?, page | 200 | 400, 404 | page ≤ 100 | 3 s |
| GET | `/api/v1/accounts/{id}/community` | community.read | analytics_run_id?, page | 200 | 404 | members page ≤ 100 | 3 s |

`/accounts/{id}/temporal` returns the persisted F21–F30 values with states and windows from the assessment's feature snapshot; it does not accept arbitrary cutoffs.

### Graph and money flow

| Method | Path | Permission | Request | Success | Errors | Limits | Timeout |
|---|---|---|---|---|---|---|---|
| GET | `/api/v1/graph/neighborhood` | graph.read | account_id, depth, max_nodes, max_edges, graph_snapshot_id? | 200 | 400, 404, 408, 410, 503 | §25.2 | 5 s |
| GET | `/api/v1/graph/path` | money_flow.read | source_account_id, destination_account_id, mode (SHORTEST/ALL), max_depth, max_results, graph_snapshot_id? | 200 | 400, 404, 408, 410, 503 | §16.7.1 | 5 s |
| GET | `/api/v1/graph/metrics` | graph.analytics.read | account_id, analytics_run_id? | 200 | 404 | — | 2 s |
| GET | `/api/v1/graph/paths/{path_id}` | money_flow.read | — | 200 | 404 | evidence page ≤ 100 | 2 s |

`/graph/path` is the single path implementation; `/money-flow` is retained as an alias (§19.2.1). Neighborhood results count accounts toward `max_nodes` and aggregated `TRANSFERRED_TO` edges toward `max_edges`; when a limit is reached the response is truncated in breadth-first order by `(hop, total_amount descending, account_id)` and reports `truncated = true`. Transaction IDs of an edge are fetched separately and paginated.

### Communities, rings, motifs, interventions

| Method | Path | Permission | Request | Success | Errors | Limits | Timeout |
|---|---|---|---|---|---|---|---|
| GET | `/api/v1/communities` | community.read | analytics_run_id?, page | 200 | 400 | page ≤ 100 | 3 s |
| GET | `/api/v1/communities/{id}` | community.read | analytics_run_id?, page | 200 | 404 | members page ≤ 100 | 3 s |
| GET | `/api/v1/rings` | ring.read | class?, status?, min_score?, scoring_run_id?, page | 200 | 400 | page ≤ 100 | 3 s |
| GET | `/api/v1/rings/{id}` | ring.read | — | 200 | 404 | — | 3 s |
| PATCH | `/api/v1/rings/{id}/status` | ring.review | status | 200 | 400, 403, 404, 409 | — | 2 s |
| GET | `/api/v1/rings/{id}/accounts` | ring.read | page | 200 | 404 | page ≤ 100 | 3 s |
| GET | `/api/v1/rings/{id}/transactions` | ring.read | page_size, cursor | 200 | 404 | page ≤ 100 | 3 s |
| GET | `/api/v1/rings/{id}/features` | ring.read | — | 200 | 404 | — | 3 s |
| GET | `/api/v1/rings/{id}/risk` | ring.read | — | 200 | 404 | — | 3 s |
| GET | `/api/v1/rings/{id}/evidence` | ring.read | section?, page | 200 | 404 | page ≤ 100 | 3 s |
| GET | `/api/v1/rings/{id}/motifs` | motif.read | type?, start?, end?, page | 200 | 400, 404 | page ≤ 100 | 3 s |
| POST | `/api/v1/rings/{id}/interventions/simulate` | intervention.simulate | mode, intervention_type?, target_ids? | 202 | 400, 403, 404, 409, 429 | targets ≤ k_max | 2 s |
| GET | `/api/v1/rings/{id}/interventions` | ring.read | page | 200 | 404 | page ≤ 100 | 2 s |
| GET | `/api/v1/interventions/{id}` | ring.read | — | 200 | 404 | — | 2 s |
| GET | `/api/v1/interventions/{id}/candidates` | ring.read | page | 200 | 404, 409 | page ≤ 100 | 3 s |

`/rings` covers both candidate classes; `/fraud-ring-candidates` is retained as an alias (§19.2.1). `/rings/{id}/features`, `/risk`, `/evidence`, and `/interventions` return `409 RING_INTELLIGENCE_NOT_APPLICABLE` for class `SUSPICIOUS_COMMUNITY`. `/interventions/{id}/candidates` returns `409 SCENARIO_NOT_COMPLETED` until the scenario completes.

### Evaluation

| Method | Path | Permission | Request | Success | Errors | Limits | Timeout |
|---|---|---|---|---|---|---|---|
| POST | `/api/v1/evaluation/runs` | pipeline.control | model_version?, configuration? | 202 | 400, 409 | — | 2 s |
| GET | `/api/v1/evaluation/runs` | evaluation.read | page | 200 | — | page ≤ 100 | 2 s |
| GET | `/api/v1/evaluation/runs/{id}` | evaluation.read | — | 200 | 404 | — | 3 s |
| GET | `/api/v1/evaluation/runs/{id}/{level}` | evaluation.read | level ∈ TRANSACTION, ACCOUNT, RING, NETWORK | 200 | 400, 404, 409 | — | 3 s |

`GET /evaluation/summary` and `GET /evaluation/{level}` from v1.3.2 are retained as aliases that read the most recent completed evaluation run (§19.2.1).

### Cases, findings, copilot, audit

| Method | Path | Permission | Request | Success | Errors | Limits | Timeout |
|---|---|---|---|---|---|---|---|
| GET | `/api/v1/cases` | case.read | status, assigned_to, page | 200 | 400 | page ≤ 100 | 2 s |
| POST | `/api/v1/cases` | case.create | title, priority, assigned_to? | 201 | 400, 403 | body ≤ 16 KB | 2 s |
| GET | `/api/v1/cases/{id}` | case.read | — | 200 | 404 | — | 1 s |
| PATCH | `/api/v1/cases/{id}` | case.update (+ field rules §22.2) | version, status?, title?, priority?, assigned_to? | 200 | 400, 403, 404, 409 | body ≤ 16 KB | 2 s |
| GET | `/api/v1/cases/{id}/subjects` | case.read | page | 200 | 404 | page ≤ 100 | 2 s |
| POST | `/api/v1/cases/{id}/subjects` | case_subject.manage | subject_type, subject_id | 201 | 400, 403, 404, 409 | — | 2 s |
| DELETE | `/api/v1/cases/{id}/subjects/{type}/{subject_id}` | case_subject.manage | — | 204 | 403, 404, 409 | — | 2 s |
| POST | `/api/v1/cases/{id}/findings` | finding.create | type, description, evidence, source | 201 | 400, 403, 404, 409 | body ≤ 64 KB | 2 s |
| GET | `/api/v1/cases/{id}/findings` | case.read | page | 200 | 404 | page ≤ 100 | 2 s |
| POST | `/api/v1/copilot/query` | copilot.use | question, account_id?, case_id?, ring_id?, context_options? | 200 | 400, 403, 404, 408, 413, 429, 503 | question ≤ 4000 chars | 20 s |
| GET | `/api/v1/audit` | audit.read | filters, page | 200 | 403 | page ≤ 100 | 3 s |

### 19.2.1 Compatibility Aliases

v1.3.2 paths are preserved. Each alias has the same permission, parameters, response, and errors as its target; the response adds the header `Deprecation: true` and a `Link` header naming the target. Aliases are not separately implemented.

| v1.3.2 path | Target |
|---|---|
| `GET /api/v1/money-flow` | `GET /api/v1/graph/path` |
| `GET /api/v1/fraud-ring-candidates` | `GET /api/v1/rings` |
| `GET /api/v1/fraud-ring-candidates/{id}` | `GET /api/v1/rings/{id}` |
| `POST /api/v1/ingestion/{id}/retry` | `POST /api/v1/pipeline-runs/{pipeline_run_id}/retry` for the ingestion's pipeline run |
| `GET /api/v1/evaluation/summary` | `GET /api/v1/evaluation/runs/{latest}` |
| `GET /api/v1/evaluation/{level}` | `GET /api/v1/evaluation/runs/{latest}/{level}` |

`{latest}` is the most recently completed evaluation run; if none exists the alias returns `404 EVALUATION_NOT_AVAILABLE`.

## 19.3 Standard Error Envelope

```json
{"error": {"code": "LIMIT_EXCEEDED", "message": "The requested operation exceeds the permitted limit.", "request_id": "…", "details": {}}}
```

Stable error codes are normative and listed in the API reference generated from the implementation. Stack traces, credentials, raw SQL/Cypher, file paths, and dependency internals are never returned. `details` contains only field names and limit values.

## 19.4 Authentication Contract

Request `{"username": "string", "password": "string"}`. Response:

```json
{"access_token": "…", "token_type": "bearer", "expires_in": 1800,
 "user": {"user_id": "uuid", "username": "string", "role": "ADMIN|INVESTIGATOR|ANALYST"}}
```

The token is opaque (§22.1). Failed login returns a generic `401 INVALID_CREDENTIALS`; inactive users receive the same response. Throttling returns `429`.

## 19.5 Ingestion Contract

The server validates content type (`text/csv`), size (`max_upload_bytes`, baseline 1 GiB), and header before accepting. Same checksum and `dataset_version` returns `409 DATASET_ALREADY_REGISTERED`. Parsing and loading happen in the INGEST job.

## 19.6 Account and Transaction Contracts

Account responses include canonical identity, `source_account_ref`, dataset, current projection, and staleness. Transaction queries use keyset pagination on `(timestamp DESC, transaction_id DESC)` with an opaque `cursor`; `start ≤ end` is required and the range may not exceed `max_transaction_range` (baseline 31 days; `400 LIMIT_EXCEEDED`).

## 19.7 Risk Contract

`GET /accounts/{id}/risk` returns the assessment of the requested (default: active) scoring run, with all components, availability, fired rules, `signal_coverage`, `max_attainable_score`, lineage, and staleness. If none exists, `404 RISK_NOT_AVAILABLE`. A non-active assessment is marked stale, never relabelled current.

## 19.8 SHAP Contract

Optional `assessment_id` selects an assessment; default is the active one. `top_n` ≤ 50. Version mismatch returns `409 EXPLANATION_VERSION_MISMATCH`. Responses state that the explanation covers the ML component only (§14.4).

## 19.9 Graph and Path Contracts

Neighborhood: `account_id` required; `depth` 1..`max_depth`; `max_nodes` 1..server max; `max_edges` 1..server max. Path: `source_account_id`, `destination_account_id` required; `max_depth` 1..5; `max_results` 1..50. Above-limit values return `400 LIMIT_EXCEEDED`. Timeout returns `408`; Neo4j unavailable returns `503 GRAPH_UNAVAILABLE`; a retired snapshot returns `410 SNAPSHOT_RETIRED`.

## 19.10 Case Contract

Creation requires title and priority; status is always `OPEN`; `created_by` is the principal. PATCH requires the current `version`; a mismatch returns `409 CASE_VERSION_CONFLICT`. Fields and transitions are restricted by §22.2. Invalid transitions return `409 INVALID_CASE_TRANSITION`.

## 19.11 Pagination Contract

Offset-paginated collections return:

```json
{"items": [], "page": 1, "page_size": 25, "total": 0, "total_is_capped": false}
```

`total` is exact up to `pagination_count_cap` (baseline 10,000); above it, `total = 10000` and `total_is_capped = true`. Cursor-paginated collections return `{"items": [], "next_cursor": "…"}`. Default page size is 25; maximum 100.

## 19.12 Staleness Contract

Risk, graph, community, ring, motif, temporal, SHAP, path, and intervention responses include:

```json
{"lineage": {"graph_snapshot_id": "…", "analytics_run_id": "…", "scoring_run_id": "…",
             "model_version": "…", "risk_logic_version": "…"},
 "computed_at": "…", "is_stale": false}
```

`is_stale` is true when any lineage element differs from the active context. Historical requests intentionally return stale data and say so.

## 19.13 Ring Intelligence Contract

Ring responses include ring ID, class, status, community ID, membership counts, features with availability, risk components, truncation state, lineage, computed timestamps, and evidence references. Collections use the pagination contract.

## 19.14 Temporal Motif Contract

Responses include motif type, anchor, participating accounts and transactions, temporal span, confidence with its components, `order_ambiguous`, truncation, evidence, and detector version. Account queries match any participating account.

## 19.15 Network Intervention Contract

`POST /rings/{id}/interventions/simulate` body: `{"mode": "RANK"}` or `{"mode": "EVALUATE", "intervention_type": "…", "target_ids": [...]}`. Validation per §16A.4.2 occurs before the job is created. The response is `202` with `scenario_id` and status `QUEUED`. The request MUST NOT contain any field that maps to a real blocking or freezing action. Every scenario and candidate response carries `"hypothetical": true` and the baseline truncation state. At most `max_concurrent_scenarios_per_user` (baseline 2) scenarios per user may be queued or running; more return `429`.

## 19.16 Multi-Level Evaluation Contract

Responses identify the evaluation run, dataset, reference construction version, test snapshot, model/feature/analytics/risk versions, metrics with sample counts and availability, the dataset profile, and limitations (including the PaySim ground-truth limitation of §28.7).

---

# 20. Frontend Contract

## 20.1 Responsibilities

The dashboard owns presentation, interaction, local UI state, request orchestration, graph visualization, and display semantics. It does not own canonical persistence, authorization, risk calculation, graph query security, or case-transition authority.

## 20.2 API Client Boundary

API calls are isolated behind a client layer (api-client, auth, account, graph, risk, ring, intervention, evaluation, case, pipeline, copilot services). Components do not construct arbitrary HTTP requests. The access token is held in memory only (not `localStorage`); a page reload requires login.

## 20.3 Capability-to-API Mapping

All paths in this table are relative to the base path `/api/v1` (§19.1).

| UI capability | API |
|---|---|
| Login, current user | `/auth/login`, `/auth/logout`, `/auth/me` |
| Active context banner | `/context` |
| Account search | `/accounts` |
| Account profile | `/accounts/{id}` |
| Transactions | `/accounts/{id}/transactions` |
| Risk and history | `/accounts/{id}/risk`, `/risk/history`, `/risk/propagation` |
| SHAP | `/accounts/{id}/shap` |
| Features and temporal | `/accounts/{id}/features`, `/accounts/{id}/temporal` |
| Account motifs | `/accounts/{id}/motifs` |
| Graph explorer | `/graph/neighborhood`, `/graph/metrics` |
| Path / money flow | `/graph/path`, `/graph/paths/{path_id}` |
| Community | `/communities`, `/communities/{id}`, `/accounts/{id}/community` |
| Rings list and review | `/rings`, `/rings/{id}`, `/rings/{id}/status` |
| Ring workspace | `/rings/{id}/accounts`, `/transactions`, `/features`, `/risk`, `/evidence`, `/motifs` |
| Intervention simulation | `/rings/{id}/interventions/simulate`, `/rings/{id}/interventions`, `/interventions/{id}`, `/interventions/{id}/candidates` |
| Evaluation | `/evaluation/runs`, `/evaluation/runs/{id}`, `/evaluation/runs/{id}/{level}` |
| Cases, subjects, findings | `/cases`, `/cases/{id}`, `/cases/{id}/subjects`, `/cases/{id}/findings` |
| Copilot | `/copilot/query` |
| Ingestion and pipelines (ADMIN) | `/ingestion`, `/datasets/{id}/profile`, `/pipeline-runs` |
| Models | `/models` |
| Users (ADMIN) | `/users` |
| Audit (ADMIN) | `/audit` |

## 20.4 UI States

Every major data view supports `LOADING`, `SUCCESS`, `EMPTY`, `ERROR`, `UNAUTHORIZED`, `UNAVAILABLE`, `STALE`, and, for asynchronous operations, `QUEUED`/`RUNNING`. `STALE` is driven only by `is_stale`; `UNAVAILABLE` only by availability fields or `503`. The UI never infers readiness from an ingestion response; it reads pipeline state.

## 20.5 Evidence Labels

The UI distinguishes `FACT`, `ANALYTICAL SIGNAL`, `MODEL OUTPUT`, `ANALYTICAL CANDIDATE`, `HYPOTHETICAL SIMULATION`, `INVESTIGATOR FINDING`, and `AI INTERPRETATION`.

## 20.6 Ring and Network Intelligence UI

The investigation workspace includes: ring summary (identity, class, status, source community, member count, span, transaction count); ring risk with component signals and availability; ring evidence (accounts, transactions, relationships, motifs, paths, lineage); motif panel (with confidence components and `order_ambiguous`); and intervention simulation (mode selection, candidates, disruption, residual risk, alternative paths, cost, rank, truncation warnings). Intervention results are visually and textually labelled `Hypothetical Simulation`. No UI control performs a real blocking action. Data from a synthetic-injection dataset is labelled `SYNTHETIC DATA` (§7.10).

---

# 21. AI Investigation Copilot

## 21.1 Flow

```text
Question → authentication/authorization → rule-based intent classification
 → authorized context retrieval → evidence assembly → structured prompt
 → Ollama/Qwen (JSON-schema constrained) → response validation → investigator
```

## 21.2 Request Contract

```text
question:        required, UTF-8, 1..4000 characters
account_id:      optional canonical account ID
case_id:         optional case ID
ring_id:         optional ring ID
context_options: optional allowed evidence-category flags
```

Referenced resources are loaded through the same services and permission checks as the corresponding API endpoints. Malformed or unauthorized references are rejected before any model call.

## 21.3 Intent Classification

Intents: `ACCOUNT_SUMMARY`, `RISK_EXPLANATION`, `GRAPH_CONTEXT`, `TEMPORAL_CONTEXT`, `MONEY_FLOW`, `RING_SUMMARY`, `CASE_SUMMARY`, `UNSUPPORTED`. Classification is deterministic and rule-based (versioned keyword and pattern table plus the presence of `account_id`, `case_id`, or `ring_id`); it does not use the LLM. Intent selects which context sections are retrieved and never grants permissions. `UNSUPPORTED` returns a structured response without calling the model.

## 21.4 Authorized Context Schema

```json
{"context_id": "…",
 "account": {}, "transactions": [], "graph": {}, "risk_assessment": {}, "shap": [],
 "temporal": [], "motifs": [], "money_flow": [], "community": {}, "ring": {},
 "findings": []}
```

Every item carries a stable `ref` (for example `assessment:{uuid}`, `transaction:{id}`, `finding:{uuid}`) and its lineage. Context is serialized as JSON data; every free-text value (finding descriptions, case titles, source references from datasets) is JSON-escaped and truncated to `copilot_max_text_field` (baseline 1,000 characters). Total context is bounded by `copilot_max_context_tokens` (baseline 6,000). Truncation is deterministic by section priority, then by item order, and is reported in `limitations`.

## 21.5 Response Contract

```json
{"request_id": "…", "intent": "ACCOUNT_SUMMARY",
 "facts": [{"text": "…", "refs": ["…"]}],
 "observed_signals": [{"text": "…", "refs": ["…"]}],
 "possible_interpretation": [{"text": "…", "refs": ["…"]}],
 "limitations": ["…"],
 "source_references": ["…"],
 "model": {"provider": "ollama", "model": "…", "model_digest": "…"},
 "context_id": "…", "generated_at": "…", "ai_generated": true}
```

The model is invoked with Ollama's structured-output `format` set to this schema (minus server-filled fields).

## 21.6 Safety and Validation

Retrieved data is untrusted. The system prompt states that context is data and that instructions inside it must be ignored. The LLM receives no credentials, tools, SQL/Cypher, shell, filesystem, authorization, or mutation capabilities. The service rejects the output with `503 AI_RESPONSE_INVALID` when any of the following holds:

1. the output does not parse against the schema;
2. any `refs` or `source_references` value is not a `ref` present in the context;
3. any `facts` or `observed_signals` item has no `refs`;
4. any text field contains a phrase from the versioned **criminality-assertion deny-list** (baseline entries: "is a money mule", "is a mule", "is guilty", "committed fraud", "is a criminal", "confirmed fraud ring", "criminal organization", "should be arrested", "should be frozen", "must be blocked"), case-insensitive, outside a quoted span that matches context text verbatim;
5. the output exceeds `copilot_max_output_tokens` (baseline 1,024).

## 21.7 Capacity, Timeout, and Failure

- Generation timeout: 20 s. Concurrent generations are limited by a global semaphore (`copilot_max_concurrency`, baseline 1); a request waiting more than 2 s returns `429 COPILOT_BUSY`. Per-user rate limit: `copilot_rate_per_minute` (baseline 6).
- If Ollama is unavailable or times out: `503 COPILOT_UNAVAILABLE`; core investigation remains available; no answer is fabricated.

## 21.8 Locality

The only provider is local Ollama on the internal Compose network. Investigation data MUST NOT be sent to any external LLM unless a future SRS revision explicitly authorizes it.

---

# 22. Security and Authorization

## 22.1 Authentication

```text
token type          = opaque random 256-bit token (base64url), bearer header
storage             = SHA-256 hash in auth_sessions; plaintext never stored or logged
idle lifetime       = 30 minutes (sliding, renewed on use)
absolute lifetime   = 12 hours
password hashing    = Argon2id (parameters recorded in configuration)
inactive users      = authentication denied; sessions revoked on deactivation
role change         = all sessions of the user revoked
logout              = session revoked
login throttling    = per username and per client IP (baseline 5 failures / 15 min → 429)
```

The initial administrator is created by a one-time bootstrap command reading `MULENETX_BOOTSTRAP_ADMIN_USERNAME` and `MULENETX_BOOTSTRAP_ADMIN_PASSWORD` from the environment; it refuses to run if any ADMIN exists. No default or plaintext password is committed.

## 22.2 Permission Matrix

Every permission is explicitly ALLOW or DENY.

| Permission | ADMIN | INVESTIGATOR | ANALYST |
|---|---|---|---|
| account.read | ALLOW | ALLOW | ALLOW |
| transaction.read | ALLOW | ALLOW | ALLOW |
| graph.read | ALLOW | ALLOW | ALLOW |
| graph.analytics.read | ALLOW | ALLOW | ALLOW |
| risk.read | ALLOW | ALLOW | ALLOW |
| shap.read | ALLOW | ALLOW | ALLOW |
| temporal.read | ALLOW | ALLOW | ALLOW |
| motif.read | ALLOW | ALLOW | ALLOW |
| money_flow.read | ALLOW | ALLOW | ALLOW |
| community.read | ALLOW | ALLOW | ALLOW |
| ring.read | ALLOW | ALLOW | ALLOW |
| ring.review | ALLOW | ALLOW | DENY |
| intervention.simulate | ALLOW | ALLOW | ALLOW |
| evaluation.read | ALLOW | ALLOW | ALLOW |
| model.read | ALLOW | ALLOW | ALLOW |
| case.read | ALLOW | ALLOW | ALLOW |
| case.create | ALLOW | ALLOW | ALLOW |
| case.update | ALLOW | ALLOW | ALLOW (restricted below) |
| case.assign | ALLOW | ALLOW | DENY |
| case.resolve | ALLOW | ALLOW | DENY |
| case_subject.manage | ALLOW | ALLOW | ALLOW (participant only) |
| finding.create | ALLOW | ALLOW | ALLOW (participant only) |
| copilot.use | ALLOW | ALLOW | ALLOW |
| ingestion.create | ALLOW | DENY | DENY |
| ingestion.read | ALLOW | ALLOW | ALLOW |
| pipeline.read | ALLOW | ALLOW | ALLOW |
| pipeline.control | ALLOW | DENY | DENY |
| audit.read | ALLOW | DENY | DENY |
| user.read | ALLOW | DENY | DENY |
| user.manage | ALLOW | DENY | DENY |
| role.manage | ALLOW | DENY | DENY |
| system_config.read | ALLOW | DENY | DENY |
| system_config.write | ALLOW | DENY | DENY |

**Case field and transition rules** (participant = creator or assignee, §17.3):

| Change | ADMIN | INVESTIGATOR | ANALYST |
|---|---|---|---|
| title, priority | any case | any case | participant only |
| assigned_to | any case | any case | DENY |
| OPEN → IN_REVIEW | any case | any case | participant only |
| IN_REVIEW → ESCALATED | any case | any case | participant only |
| → RESOLVED, → FALSE_POSITIVE, → CLOSED, ESCALATED → IN_REVIEW | any case | any case | DENY |

All roles can read all cases (single-team deployment). Denied changes return `403` and are audited.

## 22.3 Security Requirements

| ID | Requirement | Priority |
|---|---|---|
| SR-01 | Protected operations require authentication. | MUST |
| SR-02 | Authorization is enforced server-side for every endpoint and field rule. | MUST |
| SR-03 | RBAC supports ADMIN, INVESTIGATOR, ANALYST per §22.2. | MUST |
| SR-04 | Frontend visibility is not a security control. | MUST |
| SR-05 | Database and Neo4j credentials never reach the frontend. | MUST |
| SR-06 | SQL uses parameterized inputs; identifiers come from allow-lists. | MUST |
| SR-07 | Arbitrary Cypher is prohibited; Cypher is parameterized with allow-listed labels and types. | MUST |
| SR-08 | Graph bounds are server-enforced. | MUST |
| SR-09 | Money-flow and analytical bounds are server-enforced. | MUST |
| SR-10 | AI output is never an authorization decision. | MUST |
| SR-11 | The copilot receives no database credentials. | MUST |
| SR-12 | The copilot cannot execute SQL, Cypher, shell, or filesystem operations. | MUST |
| SR-13 | Investigation data remains local; Ollama is reachable only on the internal network. | MUST |
| SR-14 | Security-sensitive operations create audit events (§24.3). | MUST |
| SR-15 | Secrets come from environment or secret files, never source control; startup fails on missing or default secrets. | MUST |
| SR-16 | Errors do not expose secrets, stack traces, queries, or internals. | MUST |
| SR-17 | Request, upload, and result limits are server-enforced. | MUST |
| SR-18 | Authorization failures do not reveal whether a protected resource exists beyond the 403/404 contract. | MUST |
| SR-19 | Authentication and authorization events are logged and audited. | MUST |
| SR-20 | Administrative actions are attributable to a user. | MUST |
| SR-21 | Session revocation (logout, deactivation, role change) takes effect on the next request. | MUST |
| SR-22 | Only `dashboard` and `backend` ports are published by Compose; PostgreSQL, Neo4j, and Ollama are on the internal network only. | MUST |
| SR-23 | Uploads are streamed to disk with a size cap, validated by header before parsing, and never executed. | MUST |
| SR-24 | Append-only tables are protected by database privileges and triggers (§6.5). | MUST |

## 22.4 Threat Model Summary

| Threat | Mitigation |
|---|---|
| Credential stuffing | Argon2id, throttling, generic errors (SR-01, §22.1) |
| Stolen token reuse after deactivation | Opaque sessions with immediate revocation (SR-21) |
| Broken function-level authorization | Explicit permission matrix and field rules, negative tests per role (§22.2, AT-SEC-04) |
| SQL/Cypher injection | Parameterization and allow-lists (SR-06, SR-07) |
| Expensive traversal / path explosion | Interactive and analytical bounds, reject policy, rate limits (§16.7, §25.2) |
| Oversized uploads | Size cap, streaming, header check (SR-23) |
| Prompt injection via dataset IDs, findings, case titles | JSON-escaped, truncated context; instruction isolation; schema and reference validation; deny-list (§21) |
| Copilot resource exhaustion | Semaphore, timeout, per-user rate limit (§21.7) |
| Direct access to data stores or the LLM | Internal-only network (SR-22) |
| Audit tampering by the application | Privileges and triggers (SR-24) |
| Misreading analytics as accusations | Interpretation boundaries and labels (§9.5, §9A.6, §20.5) |

---

# 23. Configuration Specification

## 23.1 Configuration Rules

Every configuration value has a documented name, type, validation rule, default, and secret classification. Required values that are missing, malformed, or (for secrets) equal to a known default MUST fail startup. Secrets MUST NOT be committed to source control. Values that change analytical results (marked **V** below) are not runtime-tunable: they are recorded in the corresponding version record (`analytics_runs.algorithm_configuration`, `feature_versions`, `model_versions`, `risk_logic_versions`), and changing one requires a new version.

## 23.2 Configuration Catalogue

### Infrastructure and secrets

| Name | Type | Baseline | Secret | Notes |
|---|---|---|---|---|
| `POSTGRES_DSN` | string | — (required) | yes | |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | string | — (required) | password: yes | default `neo4j/neo4j` rejected |
| `OLLAMA_URL` | URL | `http://ollama:11434` | no | internal network only |
| `OLLAMA_MODEL` | string | pinned Qwen tag | no | digest recorded per response |
| `MULENETX_BOOTSTRAP_ADMIN_USERNAME`, `…_PASSWORD` | string | — | password: yes | one-time use (§22.1) |
| `CORS_ALLOWED_ORIGINS` | list | dashboard origin | no | no wildcard |
| `ARTIFACT_DIR`, `STAGING_DIR` | path | volume mounts | no | |
| `LOG_LEVEL` | enum | INFO | no | |

### Authentication

| Name | Baseline | Section |
|---|---|---|
| `session_idle_minutes` | 30 | §22.1 |
| `session_absolute_hours` | 12 | §22.1 |
| `login_max_failures`, `login_window_minutes` | 5, 15 | §22.1 |
| `argon2_time_cost`, `argon2_memory_kib`, `argon2_parallelism` | library defaults, recorded | §22.1 |

### Ingestion, jobs, snapshots

| Name | Baseline | Section |
|---|---|---|
| `max_upload_bytes` | 1 GiB | §19.5 |
| `reference_slice_max_rows` (**V**) | 1,000,000 | §7.1 |
| `paysim_epoch_anchor` (**V**) | 2020-01-01T00:00:00Z | §3.4 |
| `job_lease_seconds` | 60 | §7.8 |
| `job_heartbeat_seconds` | 15 | §7.8 |
| `job_timeout_seconds` | per job kind | §7.8 |
| `job_max_attempts` (default for `jobs.max_attempts`) | 3 | §7.8 |
| `graph_build_batch_size` | 10,000 | §6.8 |
| `synthetic_injection_enabled` | false | §7.10 |

### Graph and analytics (**V** unless noted)

| Name | Baseline | Section |
|---|---|---|
| `analytics_engine` | REFERENCE (NetworkX) | §8.1 |
| PageRank `damping`, `max_iterations`, `tolerance` | 0.85, 100, 1e-6 | §8.2 |
| Louvain `resolution`, `seed` | 1.0, 42 | §8.2 |
| `min_candidate_community_size` | 3 | §9 |
| ring parameters (thresholds and windows) | per §9, §9A | §9A |
| `mfc_top_k` | 3 | §9A.2 |

### Features, ML, risk, propagation (**V**)

| Name | Baseline | Section |
|---|---|---|
| feature windows and caps | per registry | §10.1 |
| XGBoost hyperparameters | per §11 | §11 |
| split percentiles | 70th / 85th | §11 |
| risk weights | 0.50 / 0.20 / 0.15 / 0.10 / 0.05 | §12 |
| tier thresholds | per §12 | §12 |
| `suspicious_threshold` | 0.50 | §3.5 |
| propagation `maximum_distance`, `maximum_contribution` | 3, 0.50 | §13 |
| `propagation_provenance_top_n` | 5 | §13 |

### Motifs, money flow, intervention

| Name | Baseline | Section |
|---|---|---|
| motif windows, minimum participants (**V**) | per §15.9 | §15.9 |
| `motif_max_expansions_per_anchor` (**V**) | 100,000 | §15.9.1 |
| interactive `max_depth`, `max_results`, `query_timeout` | 5, 50, 5 s | §16.7.1 |
| `analytic_max_depth`, `analytic_max_paths`, `analytic_max_expansions` (**V**) | 5, 10,000, 1,000,000 | §16.7.2 |
| `max_hop_evidence` | 20 | §16.8 |
| `k_max` (**V**) | 3 | §16A |
| `intervention_max_candidates` (**V**) | 5,000 | §16A |
| intervention ranking weights (**V**) | per §16A | §16A |
| `max_concurrent_scenarios_per_user` | 2 | §19.15 |

### API and copilot

| Name | Baseline | Section |
|---|---|---|
| graph `max_depth`, `max_nodes`, `max_edges` | 3, 500, 2,000 | §25.2 |
| `default_page_size`, `max_page_size` | 25, 100 | §19.11 |
| `pagination_count_cap` | 10,000 | §19.11 |
| `max_transaction_range` | 31 days | §19.6 |
| `copilot_timeout_seconds` | 20 | §21.7 |
| `copilot_max_concurrency` | 1 | §21.7 |
| `copilot_rate_per_minute` | 6 | §21.7 |
| `copilot_max_context_tokens` | 6,000 | §21.4 |
| `copilot_max_text_field` | 1,000 characters | §21.4 |
| `copilot_max_output_tokens` | 1,024 | §21.6 |
| `copilot_deny_list_version` | 1 | §21.6 |

---

# 24. Observability and Audit

## 24.1 Request Correlation

Every request log line includes `request_id`, timestamp, `user_id` (if authenticated), endpoint, operation, status, latency, and error category. Logs are structured JSON. Logs never contain passwords, tokens, token hashes, or copilot question/answer text.

## 24.2 Pipeline and Job Metrics

Recorded per pipeline run and job, and exposed in `GET /pipeline-runs/{id}`:

```text
records_seen, records_accepted, records_rejected (by reason code), records_duplicate
graph_nodes, graph_edges, graph_build_duration, validation_digest
analytics_duration, motif_duration, feature_generation_duration
training_duration, inference_duration, scoring_duration, ring_analysis_duration
job attempts, lease expirations, failure_stage, failure_category
paths_truncated counts per ring
SHAP_duration (on demand), copilot_retrieval_latency, copilot_generation_latency, copilot_rejections by reason
```

## 24.3 Audit Events

Audited at minimum, each with principal, action, resource type and ID, outcome (`SUCCESS`, `DENIED`, `FAILED`), timestamp, and `request_id`:

- login success and failure, logout, session revocation;
- authorization failures (`DENIED`);
- user creation, role change, activation/deactivation;
- ingestion submission, pipeline start, pipeline retry, activation of a new context, snapshot retirement;
- model training start and registration;
- case creation, field changes, transitions, assignment;
- case subject add and remove;
- finding creation;
- ring status changes;
- intervention scenario creation;
- evaluation run creation;
- copilot queries (metadata only: intent, referenced resource IDs, context_id, outcome, latency; never question or answer text);
- sensitive configuration changes.

Audit events are append-only (§6.5).

---

# 25. Non-Functional Requirements

## 25.1 Reference Environment and Performance Targets

**Reference environment:** a single host with 8 vCPU, 32 GiB RAM, local SSD, Docker Compose with all services co-located, the PaySim reference slice (§7.1) loaded and active, Ollama on CPU. Targets exclude browser rendering and cold starts and are measured with warm caches, one concurrent user, and the benchmark harness of §27.

| Operation | Target |
|---|---|
| Account lookup | p95 ≤ 500 ms |
| Risk retrieval | p95 ≤ 750 ms |
| Bounded 2-hop neighborhood (default limits) | p95 ≤ 1500 ms |
| Simple transaction query (one page) | p95 ≤ 750 ms |
| Case retrieval | p95 ≤ 500 ms |
| Health/readiness | p95 ≤ 250 ms |
| Interactive path query | p95 ≤ 5 s (hard timeout) |
| Full pipeline on the reference slice | completes; duration recorded, no target |
| Intervention scenario (RANK, typical ring) | completes within `job_timeout_seconds`; duration recorded |

Full-PaySim ingestion is a benchmark-tier activity (§8.1) with duration recorded and no target.

## 25.2 Reference Graph Limits

```text
max_depth     = 3
max_nodes     = 500
max_edges     = 2000
query_timeout = 5 seconds
```

## 25.3 Reference Money-Flow Limits

See §16.7.1 (interactive) and §16.7.2 (analytical). The values are configuration; the existence of hard server-side bounds and the reject policy are normative.

## 25.4 Reliability

Dependency failures MUST produce explicit failure or degraded states; the system MUST NOT fabricate information to mask a dependency failure. A worker crash MUST NOT lose a pipeline: expired leases are reclaimed and the stage resumes (§7.8). A failed graph build MUST NOT affect the active snapshot (§6.8).

## 25.5 Reproducibility

Every risk assessment is traceable through dataset, ingestion run, graph snapshot, analytics run, feature version, model version, risk-logic version, and scoring run. Re-running the pipeline with identical inputs, versions, and configuration on the reference tier produces identical identifiers (§6.2) and scores equal to 7 decimal places (§12).

## 25.6 Maintainability

Business logic is independent of API transport. Graph access is isolated. Risk, propagation, motif, path, and intervention calculations are independently testable against fixtures without running services. ML inference is independently testable.

## 25.7 Resource Safety

The system MUST prevent unbounded traversal, unlimited path enumeration, oversized requests and results, global analytics during interactive requests, unbounded concurrent simulations, and uncontrolled LLM generation.

---

# 26. Deployment

## 26.1 Services

| Service | Role | Published port | Restart |
|---|---|---|---|
| `dashboard` | static frontend | yes | unless-stopped |
| `backend` | FastAPI API process | yes | unless-stopped |
| `worker` | job runner (same image as backend, different entrypoint) | no | unless-stopped |
| `postgres` | canonical store | no | unless-stopped |
| `neo4j` | derived graph store (Community edition) | no | unless-stopped |
| `ollama` | local LLM | no | unless-stopped |
| `migrate` | one-shot: database migrations and Neo4j constraints/indexes | no | no |
| `ollama-pull` | one-shot: pulls the pinned model | no | no |

## 26.2 Startup Ordering and Health

- `postgres` and `neo4j` have healthchecks. `migrate` depends on both being healthy. `backend` and `worker` depend on `migrate` having completed successfully.
- `backend` and `worker` refuse to start if the schema version does not match the code (§6.7).
- Ollama is optional for core readiness.

## 26.3 Health Endpoints

```text
/health  liveness: 200 while the process serves requests; no dependency checks
/ready   200 when PostgreSQL is reachable and the schema version matches;
         503 otherwise
         body reports neo4j, ollama, worker heartbeat, and active context as
         component states (UP, DOWN, DEGRADED) without affecting the status code
```

Neo4j or Ollama being down degrades the features that need them (graph endpoints return `503 GRAPH_UNAVAILABLE`; copilot returns `503 COPILOT_UNAVAILABLE`) but does not make the backend unready.

## 26.4 Persistence

Named volumes for PostgreSQL data, Neo4j data, model artifacts, staging uploads, and the Ollama model cache.

## 26.5 Initialization

Deployment supports: database migrations; Neo4j constraints and indexes; administrator bootstrap (§22.1); optional demo dataset registration. No seed data contains credentials.

## 26.6 Network

All services share an internal Compose network. Only `dashboard` and `backend` publish ports (SR-22). Neo4j's browser and Bolt ports, PostgreSQL, and Ollama are not published.

---

# 27. Testing Strategy

## 27.1 Unit Tests

Required areas: validation and rejection codes; normalization and identity namespacing; duplicate handling; deterministic identifiers (UUIDv5); event-time cutoffs; every feature formula and state; temporal windows; motif detection and confidence; risk components, composition, rounding, and tier boundaries; rule firing under unavailable inputs; propagation; path enumeration and analytical bounds; intervention residual filtering and metrics; ring features; case transitions and field rules; RBAC (every permission × role); error mapping; copilot output validation and deny-list; pipeline transition table (every legal and illegal transition).

## 27.2 Integration Tests

Required integration coverage: PostgreSQL (including append-only triggers and grants); Neo4j (build, validation, switch-over, retirement); job queue (claim, lease expiry, heartbeat, resume); ML artifact loading and compatibility; SHAP; Ollama (structured output, timeout, unavailability). Each dependency failure is independently testable.

## 27.3 API Tests

Every endpoint in §19.2, including aliases, is tested as applicable for: success; validation failure; `400 LIMIT_EXCEEDED`; authentication failure; authorization failure for **each role that is denied** (§22.2); not found; conflict; timeout or dependency failure; staleness flag; pagination (including `total_is_capped`).

## 27.4 Golden Fixtures

Deterministic fixtures, each with hand-computed expected values stored alongside:

- `A → B → C` with expected degree, PageRank, betweenness, components, and paths;
- duplicates and malformed rows (one per rejection code);
- two versions of the same dataset with overlapping source IDs;
- cold-start accounts;
- communities and both candidate classes;
- the risk test vectors of §27.5;
- the propagation counterexample: undirected path C – A – B with pre-propagation scores C = 0.50, A = 0.49, B = 0.48; expected final scores A = 0.5150000 (HIGH) and B = 0.4966667 (MEDIUM);
- the truncation fixture: 120 qualifying baseline paths with `analytic_max_paths = 50`; expected `truncated = true` and metrics reported as lower bounds; with the bound raised to 10,000, removing X (which lies on 60 paths) yields `path_disruption = 0.5`;
- the network-risk counterexample: suspicious accounts A = 0.90, B = 0.60, C = 0.55, D = 0.20 with D the sole intermediary on every qualifying path; expected `normalized_risk_reduction` D = 1.0, A = 0.40;
- case transitions and field rules;
- copilot safety vectors (§27.6).

## 27.5 Risk Test Vectors

1. ML-only baseline.
2. High graph signal.
3. High behavioral signal.
4. High propagated signal.
5. Rule contribution, including a rule whose input is `UNAVAILABLE` (does not fire).
6. Missing graph signal (component 0, `UNAVAILABLE`, `signal_coverage` and `max_attainable_score` correct).
7. Missing model.
8. Lower boundary (0).
9. Upper boundary (maximum attainable 0.95).
10. Every tier boundary, exactly and at ±1e-7 after rounding.
11. Regime `RISK_FEATURES_UNAVAILABLE`: R03–R05 never fire.

## 27.6 Security Tests

SQL injection; Cypher injection; oversized traversal; oversized result requests; above-limit parameters (rejected, not clamped); unauthorized case mutations and field changes per role; unauthorized audit access; revoked session reuse after logout, deactivation, and role change; login throttling; prompt injection through account source references, finding descriptions, and case titles; AI escalation attempts; deny-list vectors (each baseline entry must cause rejection; quoted context text must not); invented source references; secret leakage through errors; unpublished ports unreachable from the host.

## 27.7 End-to-End

The golden path starts from a clean environment with an **empty model registry**:

```text
Dataset → Ingestion → Validation → PostgreSQL → Profiling → Graph construction
 → Graph analytics and motifs → Feature generation → Training (no compatible model)
 → Scoring (ML → pre-propagation → propagation → final) → Ring analysis → READY
 → Dashboard → SHAP (on demand) → Investigation (case, subjects, findings)
 → Intervention simulation → Evaluation run → Copilot
```

## 27.8 Ring Intelligence Tests

Deterministic fixtures verify community-to-ring extraction, both candidate classes, membership (all community members), every ring feature (§9A.2) including truncation propagation, ring risk composition, evidence retention, lineage, deterministic ring IDs across reruns, status transitions, and non-criminal interpretation wording.

## 27.9 Temporal Motif Tests

Fixtures cover: rapid pass-through `A→B→C→D`; fan-in `A→D, B→D, C→D`; fan-out `A→B, A→C, A→D`; circular flow `A→B→C→A`; layered movement `A→B→C→D→E`; burst against a known 168-bucket baseline; equal timestamps (`order_ambiguous = true`); non-maximal sub-sequences (not reported); greedy fan segmentation; negative cases outside the window; duplicate and parallel transactions; per-anchor expansion limit; cutoff and version consistency; exact motif counts and confidence values.

## 27.10 Intervention Analysis Tests

Fixtures verify that:

1. removing a peripheral account has lower disruption than removing a sole intermediary;
2. removing a bridge disconnects the expected suspicious paths;
3. redundant paths remain after removal of one intermediary;
4. the account budget `k_max` is enforced and invalid EVALUATE targets return `400 INTERVENTION_TARGET_INVALID`;
5. canonical PostgreSQL and Neo4j state is unchanged (row counts and digests before and after);
6. residual sets equal a fresh bounded enumeration on the hypothetical graph when the baseline is not truncated;
7. results are identical under artificial CPU load (no wall-clock dependence);
8. ranking inputs and rank order are reproducible, including candidate-ID tie-breaks;
9. each account yields exactly one RANK candidate;
10. the network-risk counterexample of §27.4 holds.

## 27.11 Multi-Level Evaluation Tests

Fixtures verify the transaction score rule, test-split population, reference ring construction, one-to-one matching, network metrics, the degree-ranked comparison baseline for intervention effectiveness, and that metrics unavailable on the dataset are reported as such (§28.7).

## 27.12 Reliability Tests

Partial Neo4j build failure followed by retry; worker killed mid-stage followed by lease expiry and resume; activation transaction failure leaving the previous context active; reruns producing identical identifiers.

---

# 28. Acceptance Criteria

## 28.1 Acceptance-Test Format

Every acceptance case specifies: AT-ID, preconditions, input, action, expected result, negative or abuse condition where applicable, and linked requirements. AT-IDs are unique; v1.3.2 duplicates are renumbered (Appendix F).

## 28.2 Acceptance-Test Matrix

| AT-ID | Preconditions / Input | Action | Expected Result | Linked |
|---|---|---|---|---|
| AT-DATA-01 | valid fixture | ingest | canonical rows and counts persist; profile recorded | FR-DATA |
| AT-DATA-02 | malformed rows + valid rows | ingest | malformed rows rejected with reason codes; valid rows continue | FR-DATA |
| AT-DATA-03 | same checksum and version | ingest twice | `409 DATASET_ALREADY_REGISTERED`; no duplicate canonical records | FR-DATA |
| AT-DATA-04 | PaySim v1 and v2 with overlapping source IDs | ingest both | both succeed with disjoint canonical IDs | FR-DATA |
| AT-DATA-05 | large upload | submit | `202` within 30 s; ingestion proceeds in the worker | FR-DATA |
| AT-GRAPH-01 | canonical A→B→C | build graph | IDs, topology, counts, and digest match canonical data | FR-GRAPH |
| AT-GRAPH-02 | Neo4j unavailable | neighborhood | `503 GRAPH_UNAVAILABLE`; no fabricated graph | FR-GRAPH |
| AT-GRAPH-03 | depth > max | neighborhood | `400 LIMIT_EXCEEDED` | FR-GRAPH |
| AT-GRAPH-04 | build fails midway | retry | previous snapshot remains active; retry succeeds; no orphan nodes in the active context | FR-GRAPH |
| AT-GRAPH-05 | retired snapshot | neighborhood with its ID | `410 SNAPSHOT_RETIRED` | FR-GRAPH |
| AT-ANALYTICS-01 | fixed graph | PageRank | configured output reproducible to 1e-9 | FR-GRAPH |
| AT-ANALYTICS-02 | fixed export order | Louvain twice | identical partition with identical canonical community IDs | FR-GRAPH |
| AT-RING-01 | fixed community signals | score candidate | exact deterministic candidate score and class | FR-RING |
| AT-RING-02 | qualifying community | extract ring | stable ring ID, membership, evidence across reruns | FR-RING |
| AT-RING-03 | fixed ring fixture | features | exact registry outputs, availability, truncation state | FR-RING |
| AT-RING-04 | fixed ring assessment | risk/evidence | score, components, evidence, lineage; no criminality claim | FR-RING |
| AT-RING-05 | candidate ring | PATCH status as ANALYST / INVESTIGATOR | 403 / 200 with audit event | FR-RING, SR-02 |
| AT-FEAT-01 | fixed history | generate vector | F01–F42 values and states match registry | FR-FEAT |
| AT-FEAT-02 | transaction or graph edge after T | generate at T | excluded; F11–F18 unchanged | FR-FEAT |
| AT-FEAT-03 | cold-start account | generate vector | documented zero/UNAVAILABLE states only | FR-FEAT |
| AT-FEAT-04 | snapshot with `data_cutoff > T` | generate at T | rejected | FR-FEAT |
| AT-ML-01 | labelled fixture | build target | positive/negative/unlabelled/excluded match §11; MERCHANT excluded | FR-ML |
| AT-ML-02 | temporal fixture | split/train | window table recorded; all §11.6 leakage checks pass, including entity separation and label-window containment | FR-ML |
| AT-ML-03 | incompatible feature version or regime | load artifact | inference rejected (`MODEL_INCOMPATIBLE`) | FR-ML |
| AT-ML-04 | ML unavailable | risk request | ML component UNAVAILABLE; historical score not substituted | FR-ML |
| AT-RISK-01 | fixed component values | score | exact formula result to 7 dp | FR-RISK |
| AT-RISK-02 | final score 0.25 | tier | MEDIUM | FR-RISK |
| AT-RISK-03 | final score 0.50 | tier | HIGH | FR-RISK |
| AT-RISK-04 | final score 0.75 | tier | CRITICAL | FR-RISK |
| AT-RISK-05 | graph unavailable | score | component 0 + UNAVAILABLE; coverage reported | FR-RISK |
| AT-RISK-06 | prior assessment | rescore | new row; old row unchanged | FR-RISK |
| AT-PROP-01 | source 0.8, d = 1 | propagate | contribution 0.40 | FR-PROP |
| AT-PROP-02 | cyclic graph | propagate | terminates within bounds | FR-PROP |
| AT-PROP-03 | counterexample fixture (§27.4) | score | B = 0.4966667, MEDIUM, under any evaluation order | FR-PROP |
| AT-XAI-01 | compatible assessment | SHAP | exact model, feature, and assessment references; ML-only label | FR-XAI |
| AT-TEMP-01 | known timestamps | calculate | exact formula values | FR-TEMP |
| AT-TEMP-02 | insufficient history | dormancy | UNAVAILABLE | FR-TEMP |
| AT-FLOW-01 | parallel A→B transactions | path | one topology hop; all evidence IDs retained | FR-FLOW |
| AT-FLOW-02 | A→B→A cycle | path | repeated account not traversed | FR-FLOW |
| AT-FLOW-03 | > 50 paths | path | ≤ 50 results; hard timeout | FR-FLOW |
| AT-FLOW-04 | truncation fixture | analytical enumeration | deterministic `truncated = true`; identical under load | FR-FLOW |
| AT-MOTIF-01 | pass-through fixture | detect | expected sequence and evidence | FR-MOTIF |
| AT-MOTIF-02 | fan-in/out fixture | detect | expected topology, segmentation, and evidence | FR-MOTIF |
| AT-MOTIF-03 | cycle fixture | detect | cycle identified; no criminality claim | FR-MOTIF |
| AT-MOTIF-04 | layered/burst fixture | detect | expected motif and deterministic confidence | FR-MOTIF |
| AT-MOTIF-05 | outside-window fixture | detect | no invalid motif merge | FR-MOTIF |
| AT-INT-01 | suspicious ring | simulate | no canonical mutation | FR-INT |
| AT-INT-02 | candidate | analyze | disruption, residual, path, cost, rank outputs | FR-INT |
| AT-INT-03 | budget k | EVALUATE with k+1 accounts | `400 INTERVENTION_TARGET_INVALID` | FR-INT |
| AT-INT-04 | deterministic graph | rank twice | identical order and candidate IDs | FR-INT |
| AT-INT-05 | candidate pool | RANK | exact scope, eligibility, one candidate per account, order | FR-INT |
| AT-INT-06 | tied candidates | rank | candidate-ID tie-break | FR-INT |
| AT-INT-07 | any scenario | simulate | no prohibited global recomputation | FR-INT |
| AT-INT-08 | zero-denominator fixture | simulate | explicit zero/UNAVAILABLE normalized metrics | FR-INT |
| AT-INT-09 | network-risk counterexample | rank | D reduction 1.0; A reduction 0.40 | FR-INT |
| AT-INT-10 | user with 2 running scenarios | submit third | `429` | FR-INT |
| AT-EVAL-01 | evaluation fixtures | evaluate | four levels with reference and lineage metadata | FR-EVAL |
| AT-EVAL-02 | network benchmark | evaluate | network identification, flow coverage, risk ranking, intervention effectiveness vs degree baseline | FR-EVAL |
| AT-EVAL-03 | end-to-end benchmark | evaluate | progression transaction → network with PaySim limitation statement | FR-EVAL |
| AT-INV-01 | investigator | create case | OPEN case + audit event | FR-INV |
| AT-INV-02 | analyst | resolve case | 403 | SR-02 |
| AT-INV-03 | invalid transition | PATCH | `409 INVALID_CASE_TRANSITION` | FR-INV |
| AT-INV-04 | stale `version` | PATCH | `409 CASE_VERSION_CONFLICT` | FR-INV |
| AT-INV-05 | case | add/remove subjects | subject linked; removal soft and audited | FR-INV |
| AT-INV-06 | analyst, non-participant | PATCH title | 403 | SR-02 |
| AT-API-01 | valid request | call every endpoint and alias | documented schema and status | API |
| AT-API-02 | oversized request | call endpoint | `400 LIMIT_EXCEEDED` / `413` | API, NFR |
| AT-SEC-01 | unauthenticated | protected endpoint | 401, no protected data | SR-01 |
| AT-SEC-02 | analyst | audit endpoint | 403, no audit data | SR-02 |
| AT-SEC-03 | injection payload | query/filter | no injection or data escape | SR-06, SR-07 |
| AT-SEC-04 | each role | every DENY permission of §22.2 | 403 and audit event | SR-02, SR-03 |
| AT-SEC-05 | user deactivated or role changed | reuse token | 401 | SR-21 |
| AT-AI-01 | authorized account | copilot | schema-valid, reference-grounded response | AI |
| AT-AI-02 | injection text in source ref, finding, case title | copilot | treated as data; no privilege change; output validated | AI, SR |
| AT-AI-03 | Ollama unavailable | copilot | `503 COPILOT_UNAVAILABLE`; investigation usable | AI |
| AT-AI-04 | invented source reference / deny-list phrase | simulated output | `503 AI_RESPONSE_INVALID` | AI |
| AT-AI-05 | concurrent generation in progress | second request > 2 s wait, or rate exceeded | `429` | AI |
| AT-OPS-01 | clean Docker environment | startup | migrate completes; health and readiness succeed; only dashboard/backend ports published | NFR |
| AT-OPS-02 | Neo4j down | account query and `/ready` | relational features work; `/ready` 200 with neo4j DOWN | NFR |
| AT-OPS-03 | worker killed mid-stage | wait for lease expiry | stage resumes; pipeline reaches READY | NFR |
| AT-OPS-04 | identical inputs | rerun pipeline | identical identifiers and scores | NFR |
| AT-OPS-05 | reference environment, reference slice active | run the §25.1 benchmark harness | every latency target met | NFR |
| AT-OPS-06 | clean database | apply migrations; insert rows violating each PK, FK, UNIQUE and CHECK of §6.3 | each insert rejected; composite community FKs enforced | NFR |
| AT-E2E-01 | clean environment, empty model registry, fixture | golden path (§27.7) | succeeds through copilot | E2E |

## 28.3 Ring Intelligence Acceptance

- **AT-RING-02.** Given a community satisfying the candidate conditions, MuleNetX SHALL produce a ring with a deterministic identity, constituent accounts and transactions, temporal span, and source community.
- **AT-RING-03.** Given a deterministic ring fixture, MuleNetX SHALL compute the ring features of §9A.2 with their versions, availability, and truncation state.
- **AT-RING-04.** Given a ring risk assessment, MuleNetX SHALL expose the component signals, final ring score, risk logic version, and evidence without claiming criminality.

## 28.4 Temporal Motif Acceptance

- **AT-MOTIF-01.** Given a rapid pass-through fixture, MuleNetX SHALL identify the expected maximal sequence and retain participating transactions and accounts.
- **AT-MOTIF-02.** Given fan-in and fan-out fixtures, MuleNetX SHALL identify the common destination or source and participants within the window, using greedy non-overlapping segmentation.
- **AT-MOTIF-03.** Given a circular-flow fixture, MuleNetX SHALL identify the cycle while stating that a cycle is not proof of fraud.
- **AT-MOTIF-04.** Given a layered-movement or burst fixture, MuleNetX SHALL identify the motif and return deterministic confidence and evidence.
- **AT-MOTIF-05.** Given transactions outside the window, MuleNetX SHALL NOT merge them into one motif instance.

## 28.5 Intervention Acceptance

- **AT-INT-01.** MuleNetX SHALL generate hypothetical candidates without modifying canonical account, transaction, graph, risk, case, or audit data.
- **AT-INT-02.** For a candidate, MuleNetX SHALL report suspicious-flow disruption, path disruption, residual flow, residual network risk, connectivity change, cost, ranking inputs, and baseline truncation state.
- **AT-INT-03.** MuleNetX SHALL reject any account-set intervention with more than `k_max` accounts.
- **AT-INT-04.** Given a deterministic baseline and configuration, rankings SHALL be reproducible using the frozen formulas and tie-break order.
- **AT-INT-05.** In RANK mode, the candidate pool SHALL contain exactly one candidate per eligible account and one per eligible edge, in the order of §16A.4.3.
- **AT-INT-06.** Given equal ranking metrics, the lexicographically smaller `candidate_id` SHALL rank first.
- **AT-INT-07.** Scenarios SHALL NOT trigger global PageRank, betweenness, community detection, ML training, SHAP, or inference for unaffected accounts.
- **AT-INT-08.** With zero baseline suspicious flow, paths, reachable pairs, or risk mass, the corresponding normalized metric SHALL be 0 with an explicit UNAVAILABLE state.
- **AT-INT-09.** The network-risk counterexample SHALL yield the values of §27.4.
- **AT-INT-10.** Concurrent scenario limits SHALL be enforced per user.

## 28.6 Multi-Level Evaluation Acceptance

- **AT-EVAL-01.** MuleNetX SHALL report metrics at transaction, account, ring, and network levels with reference-set and lineage metadata.
- **AT-EVAL-02.** Network evaluation SHALL include suspicious-network identification, suspicious-flow coverage, network-risk ranking, and intervention effectiveness, as defined in §28.7.
- **AT-EVAL-03.** The report SHALL show the transaction → account → ring → network progression and SHALL state that PaySim does not provide authoritative mule-ring ground truth.

## 28.7 Multi-Level Evaluation Reference Construction

**Population.** Every level is evaluated on the **test split** (§11.5): test-split accounts and transactions with timestamps in the test window, using the snapshot whose `data_cutoff` is the test cutoff and the scoring run bound to it.

**Transaction reference and score.** The dataset transaction label (PaySim `isFraud`) is the transaction reference; for PaySim it is a synthetic fraud reference, not mule-account or ring ground truth. The transaction score is `max(final_score(source), final_score(destination))`; `ml_score` of both endpoints is reported alongside. Metrics: PR-AUC, ROC-AUC, precision@100, precision at top 1%.

**Account reference.** `reference_account_label = 1` when the account participates in at least one reference-positive test transaction; otherwise 0. Accounts with no test-window transactions are excluded. MERCHANT accounts are excluded (consistent with §11.2). The aggregation rule is fixed.

**Ring reference.** Reference rings are the weakly connected components of the subgraph induced by reference-positive test transactions, keeping components with at least 3 reference-positive accounts. Reference ring IDs are UUIDv5 of the sorted member account IDs (§6.2). Analytical communities are never ground truth because their IDs match.

**Ring matching.** An analytical ring matches a reference ring when member-account Jaccard similarity ≥ 0.5. Matching is one-to-one by maximum Jaccard, ties broken by descending similarity, then ascending reference ring ID, then ascending analytical ring ID. Unmatched analytical rings are false positives; unmatched reference rings are false negatives.

**Network level.**

```text
identified_network_accounts = members of all analytical rings in the scoring run
reference_network_accounts  = members of all reference rings
network_precision = |identified ∩ reference| / |identified|
network_recall    = |identified ∩ reference| / |reference|
suspicious_flow_coverage =
    Σ amount of reference-positive test transactions whose both endpoints are identified
  / Σ amount of reference-positive test transactions
network_risk_ranking = average precision of rings ranked by ring risk score,
                       where a ring is positive if it is matched
```

Zero denominators produce 0 with an UNAVAILABLE state.

**Intervention effectiveness.** For each matched analytical ring with a completed RANK scenario, report the distribution (mean, median, min, max) of `flow_disruption_percentage` for the rank-1 candidate and for a **degree-ranked baseline candidate** (the account in the ring with the highest total degree, ties by account ID) evaluated in EVALUATE mode. Results are labelled simulated; they are never a measure of real-world enforcement effectiveness.

**Not measurable on PaySim.** Metrics that depend on labels the dataset does not provide (for example mule-account or ring identity) are reported as `NOT_MEASURABLE` with the reason, not as zero. Every evaluation records the dataset and reference construction version, snapshot, analytics, feature, model, and risk-logic versions, and configuration.

---

# 29. Demonstration Scenarios

1. **Ingestion and profiling.** A PaySim file is submitted and reaches `PROFILED` with validation counts, rejection codes, and a profile.
2. **Pipeline from scratch.** With an empty model registry, the pipeline runs through training to `READY`; the active context banner updates.
3. **Graph construction.** Canonical records become a validated Neo4j snapshot; counts and digest are shown.
4. **Account investigation.** An investigator searches an account, views transactions, risk components with coverage, propagation provenance, SHAP (ML component), and a bounded neighborhood.
5. **Community and ring.** A community is inspected and a potential ring candidate is presented without criminality claims; an investigator updates its review status.
6. **Money flow.** A source and destination produce bounded paths with intermediaries and evidence.
7. **Case.** An investigator creates a case, links subjects, adds evidence-backed findings, and performs valid transitions; an analyst's forbidden transition is refused.
8. **Copilot.** The backend retrieves authorized evidence and returns a schema-valid, reference-grounded answer from local Ollama/Qwen.
9. **Ollama failure.** The copilot becomes unavailable while investigation remains usable.
10. **Neo4j failure.** Relational features remain available; graph features are explicitly degraded; `/ready` stays 200.
11. **ML failure.** The ML component is unavailable; no historical score is substituted.
12. **Ring intelligence.** Ring features, risk, and evidence are inspected and drilled into accounts, transactions, motifs, and paths.
13. **Temporal motifs.** Known motif fixtures are shown with explicit patterns, confidence components, and evidence.
14. **Network intervention simulation.** RANK mode ranks hypothetical candidates; EVALUATE mode tests an investigator-chosen set; results are labelled hypothetical; canonical state is unchanged.
15. **Multi-level evaluation.** An evaluation run reports all four levels, the degree-baseline comparison, lineage, and the PaySim limitation statement.
16. **Worker recovery.** The worker is stopped mid-stage and restarted; the pipeline resumes.

# 30. Requirements Traceability

## 30.1 Traceability Contract

Every requirement identifier has exactly one row. The label is a summary; the cited section is the normative text. Every service, table, and endpoint named here exists in §18, §6.3, or §19. Verification refers to §27; acceptance refers to §28.2. All API paths are relative to `/api/v1`. `—` means not applicable. Every requirement links to at least one specific acceptance test. Requirements added in v1.3.3 are marked †.

| ID | Requirement | Section | Owning service | DB objects | API | Verification | Acceptance |
|---|---|---|---|---|---|---|---|
| FR-DATA-001 | detect the input schema and select the dataset adapter. | §7.1 | IngestionService | datasets | POST /ingestion | §27.1 | AT-DATA-01 |
| FR-DATA-002 | validate required columns, types, nullability, IDs, amounts, timestamps and transaction types. | §7.3 | IngestionService | ingestion_runs | POST /ingestion | §27.1 | AT-DATA-02 |
| FR-DATA-003 | normalize source records into canonical, dataset-namespaced fields. | §6.2, §7.1.1 | IngestionService | accounts, transactions | — | §27.1 | AT-DATA-01, AT-DATA-04 |
| FR-DATA-004 | handle duplicate transaction records per the dataset adapter policy. | §7.5 | IngestionService | transactions (source_record_hash) | — | §27.1 | AT-DATA-03 |
| FR-DATA-005 | reject invalid records with reason codes. | §7.3 | IngestionService | ingestion_runs.rejection_summary | GET /ingestion/{id} | §27.1 | AT-DATA-02 |
| FR-DATA-006 | persist validated accounts and transactions in PostgreSQL. | §7.2 | IngestionService | accounts, transactions | — | §27.2 | AT-DATA-01 |
| FR-DATA-007 | persist dataset, ingestion-run and pipeline lineage. | §6.3.3 | IngestionService, JobService | datasets, ingestion_runs, pipeline_runs | GET /pipeline-runs/{id} | §27.2 | AT-DATA-01 |
| FR-DATA-008 | construct the derived Neo4j graph from canonical records. | §6.8 | GraphService | graph_snapshots; Neo4j | — | §27.2 | AT-GRAPH-01 |
| FR-DATA-009 | persist deterministic pipeline state transitions with resume points. | §7.6, §7.7 | JobService | pipeline_runs, jobs | POST /pipeline-runs/{id}/retry | §27.1, §27.12 | AT-OPS-03, AT-E2E-01 |
| FR-DATA-010 | expose ingestion and pipeline status and validation results through the API. | §19.5 | IngestionService, JobService | ingestion_runs, pipeline_runs | GET /ingestion/{id}, GET /pipeline-runs/{id} | §27.3 | AT-DATA-01, AT-DATA-05 |
| FR-DATA-011 † | produce a profiling report for every dataset before analytics. | §7.9 | ProfilingService | dataset_profiles | GET /datasets/{id}/profile | §27.2 | AT-DATA-01 |
| FR-DATA-012 † | execute long-running work as leased jobs in the worker process. | §7.8 | JobService | jobs | GET /pipeline-runs/{id} | §27.2, §27.12 | AT-OPS-03 |
| FR-DATA-013 † | reject re-registration of an identical dataset version. | §7.5 | IngestionService | datasets UNIQUE(checksum, dataset_version) | POST /ingestion | §27.3 | AT-DATA-03 |
| FR-GRAPH-001 | construct the canonical directed account/transaction projection. | §6.8, §16.1 | GraphService | Neo4j Account, Transaction, TRANSFERRED_TO | — | §27.2 | AT-GRAPH-01 |
| FR-GRAPH-002 | create immutable, event-time-bounded graph snapshots. | §3.4, §6.8 | GraphService | graph_snapshots | — | §27.2 | AT-GRAPH-01, AT-FEAT-04 |
| FR-GRAPH-003 | compute graph metrics with the engine of the analytics tier. | §8.2, §8.3 | AnalyticsService | account_graph_metrics | GET /graph/metrics | §27.1 | AT-ANALYTICS-01 |
| FR-GRAPH-004 | compute deterministic connected components. | §8.3 | AnalyticsService | account_graph_metrics | GET /graph/metrics | §27.1 | AT-ANALYTICS-01 |
| FR-GRAPH-005 | compute deterministic community assignments with canonical IDs. | §8.3, §6.2.3 | AnalyticsService | communities, community_memberships | GET /communities | §27.1 | AT-ANALYTICS-02 |
| FR-GRAPH-006 | persist analytics and algorithm versions. | §6.3.3 | AnalyticsService | analytics_runs | — | §27.2 | AT-ANALYTICS-01 |
| FR-GRAPH-007 | enforce traversal depth, node, edge, result and time limits with the reject policy. | §19.9, §25.2 | GraphService | — | GET /graph/neighborhood | §27.3, §27.6 | AT-GRAPH-03 |
| FR-GRAPH-008 | return deterministic graph ordering and truncation. | §19.2 | GraphService | — | GET /graph/neighborhood | §27.1 | AT-GRAPH-01 |
| FR-GRAPH-009 | support graph exploration without arbitrary Cypher. | §19.9, SR-07 | GraphService | — | GET /graph/neighborhood | §27.6 | AT-SEC-03 |
| FR-GRAPH-010 | retain graph evidence and snapshot lineage. | §19.12 | GraphService | graph_snapshots | all analytical endpoints | §27.3 | AT-API-01 |
| FR-GRAPH-011 | degrade graph features without affecting PostgreSQL or readiness. | §26.3 | GraphService | — | GET /graph/neighborhood, /ready | §27.2 | AT-GRAPH-02, AT-OPS-02 |
| FR-GRAPH-012 | expose graph analytics through the API. | §19.2 | AnalyticsService | account_graph_metrics | GET /graph/metrics | §27.3 | AT-API-01 |
| FR-GRAPH-013 † | validate, atomically activate and retire graph snapshots. | §6.8, §6.9 | GraphService | graph_snapshots, active_context | GET /context | §27.12 | AT-GRAPH-04, AT-GRAPH-05 |
| FR-RING-001 | extract potential ring candidates from communities. | §9.1–§9.3 | RingIntelligenceService | potential_fraud_ring_candidates | GET /rings | §27.8 | AT-RING-01 |
| FR-RING-002 | construct ring membership and constituent evidence. | §9A.2 | RingIntelligenceService | ring_memberships, communities (composite key) | GET /rings/{id}/accounts, /transactions | §27.8 | AT-RING-02 |
| FR-RING-003 | compute ring-level features. | §9A.2 | RingIntelligenceService | ring_feature_sets | GET /rings/{id}/features | §27.8 | AT-RING-03 |
| FR-RING-004 | compute deterministic ring risk. | §9A.3 | RingIntelligenceService | ring_risk_assessments | GET /rings/{id}/risk | §27.8 | AT-RING-04 |
| FR-RING-005 | retain ring evidence lineage and deterministic ring IDs. | §9A.4, §9A.5 | RingIntelligenceService | ring tables | GET /rings/{id}/evidence | §27.8 | AT-RING-02, AT-OPS-04 |
| FR-RING-006 | expose ring intelligence for investigation. | §19.13 | RingIntelligenceService | ring tables | GET /rings/{id} | §27.3 | AT-API-01 |
| FR-RING-007 † | support reviewer status transitions of candidates. | §9.4 | RingIntelligenceService | potential_fraud_ring_candidates | PATCH /rings/{id}/status | §27.3 | AT-RING-05 |
| FR-TEMP-001 | compute canonical temporal features. | §15.2–§15.7, §10.1 | FeatureService | account_feature_values | GET /accounts/{id}/temporal | §27.1 | AT-TEMP-01 |
| FR-TEMP-002 | apply event-time cutoff and window semantics. | §3.4, §10.4 | FeatureService | account_feature_values | GET /accounts/{id}/temporal | §27.1 | AT-FEAT-02, AT-TEMP-02 |
| FR-TEMP-003 | detect temporal behavioral motifs (detailed by FR-MOTIF-001 to FR-MOTIF-007). | §15.9 | TemporalMotifService | temporal_motifs | GET /accounts/{id}/motifs | §27.9 | AT-MOTIF-01 |
| FR-TEMP-004 | persist deterministic motif evidence and versions. | §15.9.1, §6.2.3 | TemporalMotifService | temporal_motifs | GET /rings/{id}/motifs | §27.9 | AT-MOTIF-01, AT-OPS-04 |
| FR-MOTIF-001 | apply the common motif detection contract (ordering, maximality, limits). | §15.9.1 | TemporalMotifService | temporal_motifs | GET /accounts/{id}/motifs | §27.9 | AT-MOTIF-01, AT-MOTIF-05 |
| FR-MOTIF-002 | detect rapid pass-through. | §15.9.2 | TemporalMotifService | temporal_motifs | GET /accounts/{id}/motifs | §27.9 | AT-MOTIF-01 |
| FR-MOTIF-003 | detect fan-in and fan-out with greedy segmentation. | §15.9.3 | TemporalMotifService | temporal_motifs | GET /accounts/{id}/motifs | §27.9 | AT-MOTIF-02 |
| FR-MOTIF-004 | detect circular flow. | §15.9.4 | TemporalMotifService | temporal_motifs | GET /accounts/{id}/motifs | §27.9 | AT-MOTIF-03 |
| FR-MOTIF-005 | detect layered movement. | §15.9.5 | TemporalMotifService | temporal_motifs | GET /accounts/{id}/motifs | §27.9 | AT-MOTIF-04 |
| FR-MOTIF-006 | detect burst activity against the trailing baseline. | §15.9.6 | TemporalMotifService | temporal_motifs | GET /accounts/{id}/motifs | §27.9 | AT-MOTIF-04 |
| FR-MOTIF-007 | compute deterministic motif confidence. | §15.9.7 | TemporalMotifService | temporal_motifs | GET /accounts/{id}/motifs | §27.9 | AT-MOTIF-04 |
| FR-FLOW-001 | perform bounded shortest-path analysis. | §16.2 | MoneyFlowService | — | GET /graph/path | §27.1 | AT-FLOW-01 |
| FR-FLOW-002 | perform bounded multi-path analysis. | §16.2, §16.7 | MoneyFlowService | — | GET /graph/path | §27.1 | AT-FLOW-03 |
| FR-FLOW-003 | apply simple-path and duplicate rules. | §16.3, §16.4 | MoneyFlowService | — | GET /graph/path | §27.1 | AT-FLOW-01, AT-FLOW-02 |
| FR-FLOW-004 | return deterministic path ordering, IDs and evidence. | §16.5, §16.8 | MoneyFlowService | — | GET /graph/path, GET /graph/paths/{path_id} | §27.1 | AT-FLOW-01 |
| FR-FLOW-005 | enforce interactive and analytical path bounds and lineage. | §16.7 | MoneyFlowService | — | GET /graph/path | §27.1, §27.6 | AT-FLOW-03, AT-FLOW-04 |
| FR-INT-001 | support the four hypothetical intervention operations in RANK and EVALUATE modes. | §16A.3 | InterventionService | intervention_scenarios | POST /rings/{id}/interventions/simulate | §27.10 | AT-INT-02 |
| FR-INT-002 | generate deterministic candidate pools and enforce k_max ≤ 3. | §16A.4 | InterventionService | intervention_candidates | POST /rings/{id}/interventions/simulate | §27.10 | AT-INT-03, AT-INT-05 |
| FR-INT-003 | compute residuals by filtering the complete baseline path set. | §16A.5, §16A.7 | InterventionService | intervention_scenarios | GET /interventions/{id} | §27.10 | AT-INT-07, AT-FLOW-04 |
| FR-INT-004 | compute residual risk mass and disruption metrics deterministically. | §16A.9–§16A.12 | InterventionService | intervention_candidates | GET /interventions/{id}/candidates | §27.10 | AT-INT-08, AT-INT-09 |
| FR-INT-005 | return candidate evidence and reproducibility metadata. | §16A.15, §16A.16 | InterventionService | intervention_candidates | GET /interventions/{id}/candidates | §27.10 | AT-INT-02 |
| FR-INT-006 | rank intervention candidates deterministically. | §16A.14 | InterventionService | intervention_candidates | GET /interventions/{id}/candidates | §27.10 | AT-INT-04, AT-INT-06 |
| FR-INT-007 | preserve canonical state, hypothetical labelling and simulation capacity limits. | §16A.17, §19.15 | InterventionService | — | POST /rings/{id}/interventions/simulate | §27.10 | AT-INT-01, AT-INT-10 |
| FR-EVAL-001 | evaluate transaction-level metrics on the test split. | §28.7 | EvaluationService | evaluation_runs, evaluation_metrics | GET /evaluation/runs/{id}/TRANSACTION | §27.11 | AT-EVAL-01 |
| FR-EVAL-002 | evaluate account-level identification and ranking. | §28.7 | EvaluationService | evaluation_metrics | GET /evaluation/runs/{id}/ACCOUNT | §27.11 | AT-EVAL-01 |
| FR-EVAL-003 | evaluate ring-level detection and ranking against reference rings. | §28.7 | EvaluationService | evaluation_metrics | GET /evaluation/runs/{id}/RING | §27.11 | AT-EVAL-01, AT-EVAL-03 |
| FR-EVAL-004 | evaluate network-level coverage, risk ranking and simulated intervention effectiveness. | §28.7 | EvaluationService | evaluation_metrics | GET /evaluation/runs/{id}/NETWORK | §27.11 | AT-EVAL-02 |
| FR-FEAT-001 | define the feature registry. | §10.1 | FeatureService | feature_versions | — | §27.1 | AT-FEAT-01 |
| FR-FEAT-002 | compute account-level feature vectors at an event-time cutoff. | §10.1, §10.4 | FeatureService | account_feature_values | GET /accounts/{id}/features | §27.1 | AT-FEAT-01, AT-FEAT-02, AT-FEAT-04 |
| FR-FEAT-003 | version feature definitions, regime and outputs. | §10.2, §10.5 | FeatureService | feature_versions | — | §27.1 | AT-FEAT-01 |
| FR-FEAT-004 | handle missing and unavailable feature values deterministically. | §10.3, §10.6 | FeatureService | account_feature_values | GET /accounts/{id}/features | §27.1 | AT-FEAT-03 |
| FR-FEAT-005 | expose feature lineage for reproducibility. | §10.7 | FeatureService | account_feature_values | GET /accounts/{id}/features | §27.3 | AT-XAI-01 |
| FR-ML-001 | define the fraud-prediction target. | §11.2 | MLService | model_versions | — | §27.1 | AT-ML-01 |
| FR-ML-002 | construct leakage-controlled training data. | §11.4, §11.6 | MLService | model_versions | — | §27.1 | AT-ML-02 |
| FR-ML-003 | apply deterministic train/validation/test separation with entity separation. | §11.5 | MLService | model_versions.split_boundaries | — | §27.1 | AT-ML-02 |
| FR-ML-004 | train the initial replaceable XGBoost model, including from an empty registry. | §11.8, §7.6 | MLService | model_versions; artifacts | GET /models | §27.7 | AT-E2E-01 |
| FR-ML-005 | handle class imbalance according to the training contract. | §11.7 | MLService | model_versions | — | §27.1 | AT-ML-02 |
| FR-ML-006 | compute required classification metrics. | §11.10 | MLService | model_versions | GET /models/{version} | §27.1 | AT-ML-02 |
| FR-ML-007 | persist model and dataset lineage. | §11.9 | MLService | model_versions | GET /models/{version} | §27.2 | AT-ML-02 |
| FR-ML-008 | produce fraud probability in [0,1]. | §11.3 | MLService | risk_assessments.ml_score | GET /accounts/{id}/risk | §27.1 | AT-RISK-01 |
| FR-ML-009 | serve versioned predictions and reject incompatible artifacts. | §11.11, §11.12 | MLService | risk_assessments | GET /accounts/{id}/risk | §27.2 | AT-ML-03, AT-ML-04 |
| FR-RISK-001 | preserve ML fraud probability as a distinct signal. | §12.1 | RiskService | risk_assessments | GET /accounts/{id}/risk | §27.5 | AT-RISK-01 |
| FR-RISK-002 | compute graph signal score from G_SET. | §12.3 | RiskService | risk_assessments | GET /accounts/{id}/risk | §27.5 | AT-RISK-01 |
| FR-RISK-003 | compute behavioral signal score from B_SET. | §12.3 | RiskService | risk_assessments | GET /accounts/{id}/risk | §27.5 | AT-RISK-01 |
| FR-RISK-004 | compute rule signal score; unavailable inputs never fire. | §12.5 | RiskService | risk_assessments.fired_rules | GET /accounts/{id}/risk | §27.5 | AT-RISK-01 |
| FR-RISK-005 | compute bounded propagated risk from pre-propagation sources. | §12.1, §13 | PropagationService | risk_assessments, propagation_contributions | GET /accounts/{id}/risk/propagation | §27.5 | AT-PROP-01, AT-PROP-03 |
| FR-RISK-006 | combine signals with the frozen formula in the acyclic order. | §12.1, §12.4 | RiskService | risk_assessments | GET /accounts/{id}/risk | §27.5 | AT-RISK-01, AT-PROP-03 |
| FR-RISK-007 | clamp and round the final score. | §12.4 | RiskService | risk_assessments | GET /accounts/{id}/risk | §27.5 | AT-RISK-01 |
| FR-RISK-008 | assign deterministic risk tiers after rounding. | §12.6 | RiskService | risk_assessments.risk_tier | GET /accounts/{id}/risk | §27.5 | AT-RISK-02, AT-RISK-03, AT-RISK-04 |
| FR-RISK-009 | apply missing-signal and cold-start semantics with coverage reporting. | §12.8 | RiskService | risk_assessments | GET /accounts/{id}/risk | §27.5 | AT-RISK-05 |
| FR-RISK-010 | persist immutable risk assessments bound to a scoring run. | §12.9, §6.5 | RiskService | risk_assessments, scoring_runs | GET /accounts/{id}/risk/history | §27.2 | AT-RISK-06 |
| FR-RISK-011 | preserve component provenance. | §12.1 | RiskService | risk_assessments | GET /accounts/{id}/risk | §27.3 | AT-RISK-01 |
| FR-RISK-012 | version risk logic, normalization reference and thresholds. | §12.7 | RiskService | risk_logic_versions | — | §27.1 | AT-RISK-01 |
| FR-RISK-013 | expose current and historical risk assessments. | §19.7 | RiskService | risk_assessments | GET /accounts/{id}/risk, /risk/history | §27.3 | AT-RISK-06 |
| FR-PROP-001 | identify eligible propagation sources by pre-propagation score. | §13.2 | PropagationService | propagation_contributions | GET /accounts/{id}/risk/propagation | §27.1 | AT-PROP-03 |
| FR-PROP-002 | apply bounded BFS propagation distance. | §13.2 | PropagationService | propagation_contributions | — | §27.1 | AT-PROP-02 |
| FR-PROP-003 | apply deterministic distance decay and max aggregation. | §13.2 | PropagationService | propagation_contributions | — | §27.1 | AT-PROP-01 |
| FR-PROP-004 | prevent propagation from erasing ML provenance. | §13.4 | PropagationService | risk_assessments | GET /accounts/{id}/risk | §27.1 | AT-RISK-01 |
| FR-PROP-005 | persist propagation provenance and availability. | §13.3 | PropagationService | propagation_contributions | GET /accounts/{id}/risk/propagation | §27.2 | AT-PROP-01 |
| FR-XAI-001 | generate SHAP explanations on demand for the ML component. | §14.1, §14.2 | ExplainabilityService | shap_explanations | GET /accounts/{id}/shap | §27.2 | AT-XAI-01 |
| FR-XAI-002 | persist explanation lineage. | §14.2, §14.3 | ExplainabilityService | shap_explanations | GET /accounts/{id}/shap | §27.2 | AT-XAI-01 |
| FR-XAI-003 | return feature contributions deterministically. | §14.2 | ExplainabilityService | shap_explanations | GET /accounts/{id}/shap | §27.1 | AT-XAI-01 |
| FR-XAI-004 | distinguish model explanation from criminality interpretation and from the final score. | §14.4 | ExplainabilityService | — | GET /accounts/{id}/shap | §27.3 | AT-XAI-01 |
| FR-XAI-005 | expose explanation evidence to investigators. | §19.8 | ExplainabilityService | shap_explanations | GET /accounts/{id}/shap | §27.3 | AT-XAI-01 |
| FR-INV-001 | retrieve account investigation context. | §17.1 | AccountService | accounts | GET /accounts/{id} | §27.3 | AT-API-01 |
| FR-INV-002 | explore related graph entities. | §17.1 | GraphService | — | GET /graph/neighborhood | §27.3 | AT-API-01 |
| FR-INV-003 | view risk and explainability evidence. | §17.1 | RiskService, ExplainabilityService | risk_assessments, shap_explanations | GET /accounts/{id}/risk, /shap | §27.3 | AT-XAI-01 |
| FR-INV-004 | view temporal and motif evidence. | §17.1 | FeatureService, TemporalMotifService | account_feature_values, temporal_motifs | GET /accounts/{id}/temporal, /motifs | §27.3 | AT-MOTIF-01 |
| FR-INV-005 | trace bounded money flows. | §17.1 | MoneyFlowService | — | GET /graph/path | §27.3 | AT-FLOW-01 |
| FR-INV-006 | review ring and network evidence. | §17.1 | RingIntelligenceService | ring tables | GET /rings/{id}/evidence | §27.3 | AT-RING-04 |
| FR-INV-007 | create findings with validated evidence references. | §17.5 | InvestigationService | findings | POST /cases/{id}/findings | §27.3 | AT-INV-01 |
| FR-INV-008 | create and manage cases with optimistic concurrency. | §17.2, §19.10 | InvestigationService | cases | POST /cases, PATCH /cases/{id} | §27.3 | AT-INV-01, AT-INV-04 |
| FR-INV-009 | validate case-state transitions. | §17.2 | InvestigationService | cases | PATCH /cases/{id} | §27.1 | AT-INV-03 |
| FR-INV-010 | enforce role and participant rules on case changes. | §17.3, §22.2 | InvestigationService, AuthService | cases | PATCH /cases/{id} | §27.6 | AT-INV-02, AT-INV-06 |
| FR-INV-011 | persist investigation audit events. | §24.3 | AuditService | audit_events | GET /audit | §27.2 | AT-INV-01 |
| FR-INV-012 | retain evidence references. | §17.5 | InvestigationService | findings.evidence | GET /cases/{id}/findings | §27.2 | AT-INV-01 |
| FR-INV-013 | support the golden investigation workflow. | §17.1 | all | — | §20.3 | §27.7 | AT-E2E-01 |
| FR-INV-014 † | link and unlink case subjects. | §17.4 | InvestigationService | case_subjects | POST/DELETE/GET /cases/{id}/subjects | §27.3 | AT-INV-05 |
| SR-01 | require authentication for protected operations. | §22 | AuthService, all routes | users, auth_sessions, audit_events | all protected endpoints | §27.6 | AT-SEC-01 |
| SR-02 | enforce authorization server-side, including field rules. | §22 | AuthService, all routes | — | all protected endpoints | §27.6 | AT-SEC-04, AT-INV-06 |
| SR-03 | enforce ADMIN/INVESTIGATOR/ANALYST RBAC. | §22 | AuthService, all routes | — | all protected endpoints | §27.6 | AT-SEC-04 |
| SR-04 | treat frontend visibility as non-authoritative. | §22 | AuthService, all routes | — | all protected endpoints | §27.6 | AT-SEC-04 |
| SR-05 | prevent database credentials from reaching the frontend. | §22 | AuthService, all routes | — | all protected endpoints | §27.6 | AT-SEC-03 |
| SR-06 | parameterize SQL inputs. | §22 | AuthService, all routes | — | all protected endpoints | §27.6 | AT-SEC-03 |
| SR-07 | prohibit arbitrary Cypher. | §22 | AuthService, all routes | — | all protected endpoints | §27.6 | AT-SEC-03 |
| SR-08 | enforce graph bounds server-side. | §22 | AuthService, all routes | — | all protected endpoints | §27.6 | AT-GRAPH-03 |
| SR-09 | enforce money-flow and analytical bounds server-side. | §22 | AuthService, all routes | — | all protected endpoints | §27.6 | AT-FLOW-03 |
| SR-10 | prevent AI output from becoming an authorization decision. | §22 | AuthService, all routes | — | all protected endpoints | §27.6 | AT-AI-02 |
| SR-11 | deny database credentials to the copilot. | §22 | AuthService, all routes | — | all protected endpoints | §27.6 | AT-AI-02 |
| SR-12 | prevent AI execution of SQL/Cypher/shell/filesystem operations. | §22 | AuthService, all routes | — | all protected endpoints | §27.6 | AT-AI-02 |
| SR-13 | keep investigation data local. | §22 | AuthService, all routes | — | all protected endpoints | §27.6 | AT-OPS-01 |
| SR-14 | audit security-sensitive operations. | §22 | AuthService, all routes | users, auth_sessions, audit_events | all protected endpoints | §27.6 | AT-SEC-04 |
| SR-15 | protect secrets and fail on default secrets. | §22 | AuthService, all routes | — | all protected endpoints | §27.6 | AT-OPS-01 |
| SR-16 | avoid secret or stack-trace disclosure in errors. | §22 | AuthService, all routes | — | all protected endpoints | §27.6 | AT-SEC-03 |
| SR-17 | enforce request, upload and result limits server-side. | §22 | AuthService, all routes | — | all protected endpoints | §27.6 | AT-API-02 |
| SR-18 | avoid protected-data disclosure on authorization failure. | §22 | AuthService, all routes | — | all protected endpoints | §27.6 | AT-SEC-02 |
| SR-19 | log authentication and authorization events. | §22 | AuthService, all routes | users, auth_sessions, audit_events | all protected endpoints | §27.6 | AT-SEC-04 |
| SR-20 | attribute administrative actions. | §22 | AuthService, all routes | users, auth_sessions, audit_events | all protected endpoints | §27.6 | AT-SEC-04 |
| SR-21 † | revoke sessions on logout, deactivation and role change. | §22 | AuthService, all routes | users, auth_sessions, audit_events | all protected endpoints | §27.6 | AT-SEC-05 |
| SR-22 † | publish only dashboard and backend ports. | §22 | AuthService, all routes | — | all protected endpoints | §27.6 | AT-OPS-01 |
| SR-23 † | stream, cap and header-check uploads. | §22 | AuthService, all routes | — | all protected endpoints | §27.6 | AT-API-02 |
| SR-24 † | protect append-only tables with privileges and triggers. | §22 | AuthService, all routes | — | all protected endpoints | §27.6 | AT-RISK-06 |
| AI-01 | classify intent with deterministic rules before context retrieval. | §21.3 | AIService | audit_events (metadata only) | POST /copilot/query | §27.6 | AT-AI-01 |
| AI-02 | retrieve only authorized investigation context. | §21.2, §21.4 | AIService | audit_events (metadata only) | POST /copilot/query | §27.6 | AT-AI-01 |
| AI-03 | assemble structured, JSON-encoded, length-capped context. | §21.4 | AIService | audit_events (metadata only) | POST /copilot/query | §27.6 | AT-AI-02 |
| AI-04 | use the local LLM only through the AI service boundary. | §21.8 | AIService | audit_events (metadata only) | POST /copilot/query | §27.6 | AT-AI-03 |
| AI-05 | return facts, observed signals, possible interpretation and limitations. | §21.5 | AIService | audit_events (metadata only) | POST /copilot/query | §27.6 | AT-AI-01 |
| AI-06 | treat retrieved data as untrusted prompt content. | §21.6 | AIService | audit_events (metadata only) | POST /copilot/query | §27.6 | AT-AI-02 |
| AI-07 | prevent arbitrary tool, database or system execution. | §21.6 | AIService | audit_events (metadata only) | POST /copilot/query | §27.6 | AT-AI-02 |
| AI-08 | reject outputs with invalid references, uncited facts or deny-list phrases. | §21.6 | AIService | audit_events (metadata only) | POST /copilot/query | §27.6 | AT-AI-04 |
| AI-09 | degrade cleanly when Ollama is unavailable. | §21.7 | AIService | audit_events (metadata only) | POST /copilot/query | §27.6 | AT-AI-03 |
| AI-10 | keep AI advisory and non-authoritative. | §21.6 | AIService | audit_events (metadata only) | POST /copilot/query | §27.6 | AT-AI-02 |
| AI-11 † | enforce generation concurrency and per-user rate limits. | §21.7 | AIService | audit_events (metadata only) | POST /copilot/query | §27.6 | AT-AI-05 |
| NFR-01 | provide reproducible dataset and pipeline lineage. | §25.5 | — | — | — | §27 | AT-OPS-04 |
| NFR-02 | meet reference latency targets in the reference environment. | §25.1 | — | — | — | §27 | AT-OPS-05 |
| NFR-03 | meet reference graph traversal limits. | §25.2 | — | — | — | §27 | AT-GRAPH-03 |
| NFR-04 | bound expensive analytical operations deterministically. | §16.7.2, §25.7 | — | — | — | §27 | AT-FLOW-04 |
| NFR-05 | run batch work in the worker without blocking the API. | §4.4, §7.8 | — | — | — | §27 | AT-DATA-05 |
| NFR-06 | maintain deterministic analytical outputs and identifiers. | §6.2.3, §25.5 | — | — | — | §27 | AT-OPS-04 |
| NFR-07 | provide liveness and readiness behavior. | §26.3 | — | — | — | §27 | AT-OPS-02 |
| NFR-08 | support Docker Compose deployment. | §26 | — | — | — | §27 | AT-OPS-01 |
| NFR-09 | retain structured request and operation logging. | §24.1 | — | — | — | §27 | AT-OPS-01 |
| NFR-10 | include request IDs in logs and errors. | §19.1, §24.1 | — | — | — | §27 | AT-API-01 |
| NFR-11 | expose pipeline state, metrics and failures. | §24.2 | — | — | — | §27 | AT-E2E-01 |
| NFR-12 | support degraded Neo4j operation without relational impact. | §26.3 | — | — | — | §27 | AT-OPS-02 |
| NFR-13 | keep core investigation usable without Ollama. | §21.7 | — | — | — | §27 | AT-AI-03 |
| NFR-14 | protect configuration and secrets. | §23 | — | — | — | §27 | AT-OPS-01 |
| NFR-15 | maintain database integrity constraints. | §6.3, §6.4 | — | — | — | §27 | AT-OPS-06 |
| NFR-16 | support indexed canonical queries and keyset pagination. | §6.3, §19.11 | — | — | — | §27 | AT-OPS-05 |
| NFR-17 | support bounded graph queries. | §25.2 | — | — | — | §27 | AT-GRAPH-03 |
| NFR-18 | support bounded feature computation. | §10 | — | — | — | §27 | AT-FEAT-01 |
| NFR-19 | support reproducible ML evaluation. | §11.9 | — | — | — | §27 | AT-ML-02 |
| NFR-20 | support immutable analytical history. | §6.5 | — | — | — | §27 | AT-RISK-06 |
| NFR-21 | retain version metadata on analytical outputs. | §19.12 | — | — | — | §27 | AT-API-01 |
| NFR-22 | support end-to-end golden-path testing from an empty registry. | §27.7 | — | — | — | §27 | AT-E2E-01 |
| NFR-23 | document operational failure behavior. | §25.4, §26.3 | — | — | — | §27 | AT-OPS-02 |
| NFR-24 † | recover from worker failure by lease expiry and resume. | §7.8, §25.4 | — | — | — | §27 | AT-OPS-03 |

## 30.2 Changes to Requirement Identifiers

- v1.3.2 §30.2 listed a second, conflicting set of meanings for FR-RING-001..004 and FR-INT/FR-EVAL rows. The §30.1 meanings are retained; the conflicting rows are removed.
- FR-MOTIF-001..007, previously only in v1.3.2 §30.2, are now first-class requirements in §30.1.
- Requirements added in v1.3.3 are marked † above. No v1.3.2 identifier is deleted or reused with a different meaning.
- README §38 identifiers are superseded by this section (§1.1).

# Appendix A — Requirement Index

**FR-DATA** (13): FR-DATA-001, FR-DATA-002, FR-DATA-003, FR-DATA-004, FR-DATA-005, FR-DATA-006, FR-DATA-007, FR-DATA-008, FR-DATA-009, FR-DATA-010, FR-DATA-011, FR-DATA-012, FR-DATA-013

**FR-GRAPH** (13): FR-GRAPH-001, FR-GRAPH-002, FR-GRAPH-003, FR-GRAPH-004, FR-GRAPH-005, FR-GRAPH-006, FR-GRAPH-007, FR-GRAPH-008, FR-GRAPH-009, FR-GRAPH-010, FR-GRAPH-011, FR-GRAPH-012, FR-GRAPH-013

**FR-RING** (7): FR-RING-001, FR-RING-002, FR-RING-003, FR-RING-004, FR-RING-005, FR-RING-006, FR-RING-007

**FR-TEMP** (4): FR-TEMP-001, FR-TEMP-002, FR-TEMP-003, FR-TEMP-004

**FR-MOTIF** (7): FR-MOTIF-001, FR-MOTIF-002, FR-MOTIF-003, FR-MOTIF-004, FR-MOTIF-005, FR-MOTIF-006, FR-MOTIF-007

**FR-FLOW** (5): FR-FLOW-001, FR-FLOW-002, FR-FLOW-003, FR-FLOW-004, FR-FLOW-005

**FR-INT** (7): FR-INT-001, FR-INT-002, FR-INT-003, FR-INT-004, FR-INT-005, FR-INT-006, FR-INT-007

**FR-EVAL** (4): FR-EVAL-001, FR-EVAL-002, FR-EVAL-003, FR-EVAL-004

**FR-FEAT** (5): FR-FEAT-001, FR-FEAT-002, FR-FEAT-003, FR-FEAT-004, FR-FEAT-005

**FR-ML** (9): FR-ML-001, FR-ML-002, FR-ML-003, FR-ML-004, FR-ML-005, FR-ML-006, FR-ML-007, FR-ML-008, FR-ML-009

**FR-RISK** (13): FR-RISK-001, FR-RISK-002, FR-RISK-003, FR-RISK-004, FR-RISK-005, FR-RISK-006, FR-RISK-007, FR-RISK-008, FR-RISK-009, FR-RISK-010, FR-RISK-011, FR-RISK-012, FR-RISK-013

**FR-PROP** (5): FR-PROP-001, FR-PROP-002, FR-PROP-003, FR-PROP-004, FR-PROP-005

**FR-XAI** (5): FR-XAI-001, FR-XAI-002, FR-XAI-003, FR-XAI-004, FR-XAI-005

**FR-INV** (14): FR-INV-001, FR-INV-002, FR-INV-003, FR-INV-004, FR-INV-005, FR-INV-006, FR-INV-007, FR-INV-008, FR-INV-009, FR-INV-010, FR-INV-011, FR-INV-012, FR-INV-013, FR-INV-014

**SR** (24): SR-01, SR-02, SR-03, SR-04, SR-05, SR-06, SR-07, SR-08, SR-09, SR-10, SR-11, SR-12, SR-13, SR-14, SR-15, SR-16, SR-17, SR-18, SR-19, SR-20, SR-21, SR-22, SR-23, SR-24

**AI** (11): AI-01, AI-02, AI-03, AI-04, AI-05, AI-06, AI-07, AI-08, AI-09, AI-10, AI-11

**NFR** (24): NFR-01, NFR-02, NFR-03, NFR-04, NFR-05, NFR-06, NFR-07, NFR-08, NFR-09, NFR-10, NFR-11, NFR-12, NFR-13, NFR-14, NFR-15, NFR-16, NFR-17, NFR-18, NFR-19, NFR-20, NFR-21, NFR-22, NFR-23, NFR-24

Total: 170 requirements.
---

# Appendix B — Canonical Data Lineage

```text
Dataset (dataset_key, version, checksum, adapter)
  ├─ DatasetProfile
  └─ IngestionRun → Accounts, Transactions (dataset-namespaced IDs)
        ↓
PipelineRun (state machine §7.6; stages executed as Jobs §7.8)
        ↓
GraphSnapshot (data_cutoff, OPERATIONAL | TRAINING_SPLIT; validated; Neo4j build)
        ↓
AnalyticsRun (engine tier, algorithm configuration)
  ├─ AccountGraphMetrics
  ├─ Communities + CommunityMemberships
  └─ TemporalMotifs
        ↓
FeatureVersion (registry v1, feature_regime) → AccountFeatureValues (as_of)
        ↓
ModelVersion (trained on TRAINING_SPLIT snapshots; split boundaries; regime)
        ↓
ScoringRun (snapshot, analytics run, feature version, model version, risk logic version)
  ├─ RiskAssessments (ml → pre_propagation → propagated → final → tier; as_of)
  ├─ PropagationContributions
  └─ SHAP explanations (on demand, cached)
        ↓
Ring analysis (bound to ScoringRun)
  ├─ PotentialFraudRingCandidates (+ status history)
  ├─ RingMemberships, RingFeatureSets, RingRiskAssessments
        ↓
ActiveContext (single row; switched atomically at READY)
        ↓
InterventionScenarios → InterventionCandidates (hypothetical; bound to ScoringRun)
EvaluationRuns → EvaluationMetrics (test split; reference construction version)
        ↓
Investigation: Cases → CaseSubjects, Findings (evidence references)
        ↓
Authorized copilot context (read-only) → Local AI Copilot
AuditEvents record every security-relevant step.
```

---

# Appendix C — Architecture Invariants

1. PostgreSQL is canonical for accounts, transactions, and persisted analytical results.
2. Neo4j is derived analytical state and can be rebuilt from PostgreSQL.
3. Dataset-namespaced PostgreSQL IDs are the cross-system identity contract.
4. Neo4j internal IDs are never public identifiers.
5. No investigator-facing graph traversal is unbounded.
6. No money-flow query or analytical path enumeration is unbounded; analytical bounds are deterministic work budgets, not wall-clock limits.
7. Model probability is not mule probability.
8. Community membership is not proof of a fraud ring.
9. Connectivity is not proof of criminal activity or of funds movement.
10. Risk assessments are immutable.
11. Unavailable signals are not fabricated.
12. Stale analytical results are labelled.
13. Risk logic is versioned.
14. Feature definitions and the feature regime are versioned.
15. Model artifacts are versioned and hash-verified.
16. Graph snapshots are versioned and carry an event-time `data_cutoff`.
17. AI cannot authorize protected actions.
18. AI cannot execute database or system commands.
19. Frontend controls are not security controls.
20. Core investigation does not depend on Ollama.
21. Canonical and derived data are never competing sources of truth.
22. Changes to these invariants require an SRS revision.
23. Communities and rings are distinct analytical concepts.
24. Temporal motifs are behavioral-pattern evidence, not criminality determinations.
25. Intervention scenarios are hypothetical and cannot mutate canonical state.
26. Intervention budgets are bounded (`k_max ≤ 3`) and server-enforced.
27. Intervention rankings are decision-support scores, not enforcement recommendations.
28. Multi-level evaluation distinguishes transaction, account, ring, and network evidence and references.
29. Connectivity disruption uses unique ordered suspicious source/destination pairs.
30. Simulations operate only on immutable analytical snapshots and the bound scoring run.
31. Motif confidence is deterministic pattern-strength evidence, not a probability of criminality.
32. Unavailable ring, risk, and intervention components contribute zero without weight renormalization, and their unavailability is reported.
33. Normalized metrics use explicit zero-denominator handling.
34. Evaluation reference construction is deterministic and never treats analytical communities as ground truth.
35. Event time and processing time are never compared (§3.4).
36. No feature, snapshot, or assessment used for an observation at cutoff T contains information with event time after T.
37. The analytical stage order is acyclic: propagation sources use pre-propagation scores of the same scoring run (§12.1).
38. Every identifier that a determinism claim relies on is a UUIDv5 of canonical content (§6.2.3).
39. Intervention residual path sets are subsets of the baseline path set, obtained by filtering.
40. Long-running work runs in the worker, never in the API request path.
41. Exactly one analytical context is active, switched atomically.
42. Above-limit request parameters are rejected, never silently clamped.

---

# Appendix D — Implementation-Readiness Checklist

## Document contract completeness

- [x] Every canonical and analytical entity has a physical schema (§6.3), including feature values, graph metrics, SHAP, propagation provenance, ring membership, case subjects, sessions, jobs, scoring runs, and evaluation.
- [x] Event-time model and cutoff rules (§3.4, §10.4).
- [x] Acyclic scoring order with a worked counterexample fixture (§12.1, §27.4).
- [x] Complete pipeline state machine, job model, retry and resume (§7.6–§7.8).
- [x] Neo4j physical schema, build validation, switch-over, retirement (§6.8–§6.9).
- [x] Engine tiers and the reference dataset (§1.6, §8.2).
- [x] Suspicious-flow vocabulary (§3.5) used by rings, features, interventions, and evaluation.
- [x] Deterministic analytical and interactive path bounds (§16.7).
- [x] Risk component feature sets, normalization reference, and rounding (§12).
- [x] Motif enumeration rules (§15.9).
- [x] Ring membership and features (§9A).
- [x] Intervention modes, exact residuals, revised network risk (§16A).
- [x] API inventory with permissions, limits, and aliases (§19); UI mapping (§20.3).
- [x] Opaque sessions, permission matrix, case field rules (§22).
- [x] Copilot intent, schema, validation, deny-list, capacity (§21).
- [x] Evaluation reference construction and metric definitions (§28.7).
- [x] Unique acceptance-test identifiers; regenerated traceability (§28.2, §30).

## Open before implementation is planned

- [ ] Partha confirms or changes DEC-01 to DEC-05 (§1.6).
- [ ] The dataset profiling report (§7.9) is run on the chosen PaySim file and reviewed. If it shows too few multi-hop chains for ring, motif, and intervention demonstrations on real data, decide whether to enable synthetic injection (§7.10) for the demo.

## Implementation verification (not SRS contracts)

- [ ] Verify indexes against real query plans.
- [ ] Implement and test the Neo4j build, validation, and switch-over.
- [ ] Run the full test suites of §27.
- [ ] Benchmark against §25.1 in the reference environment.
- [ ] Verify the UI mapping and states of §20.

---

# Appendix E — Definition of Done for SRS v1.3.3

The SRS is implementation-ready when:

1. An engineer can create the canonical database schema without inventing fields.
2. An engineer can create the Neo4j schema without inventing identity or snapshot semantics.
3. An engineer can implement synchronization and activation without deciding which store owns what.
4. An engineer can implement a feature without guessing its formula, window, or cutoff.
5. An engineer can train the model without guessing the target, split, or leakage boundary.
6. An engineer can calculate risk without inventing composition, order, normalization, or rounding.
7. An engineer can run every pipeline stage in order from an empty environment.
8. An engineer can implement every analytical path computation deterministically.
9. An engineer can expose dashboard data without inventing API semantics.
10. An engineer can enforce case transitions and field rules without relying on the frontend.
11. An engineer can implement the copilot without granting authority to the LLM and with mechanically testable output validation.
12. An engineer can derive automated tests with exact expected values from the acceptance criteria.
13. A planner can break the system into modules, migrations, services, endpoints, configuration, and tests without redefining scope.

If a condition fails during implementation, the implementer reports the specific contract deviation and obtains an SRS revision before changing frozen behavior.

Weights, thresholds, algorithm parameters, rule contributions, and propagation values are baseline engineering parameters for deterministic MVP behavior. They are not calibrated real-world AML truth. Empirical changes require a new versioned configuration and regression tests.

---

# Appendix F — Change Log (v1.3.2 → v1.3.3)

## F.1 Mandatory corrections

| Change | Audit finding | What changed | Where |
|---|---|---|---|
| REV-01 | AUD-001 | Event-time model; `graph_snapshots.data_cutoff`, `risk_assessments.as_of`; cutoff rules in event time; per-split training snapshots; fixed PaySim epoch anchor (2020-01-01T00:00Z) | §3.4, §6.3, §6.8, §10.4, §11.4 |
| REV-02 | AUD-002, AUD-023 | Acyclic order: ML → pre-propagation → propagation (sources by pre-propagation score; BFS on the undirected projection) → final; feature regime `RISK_FEATURES_UNAVAILABLE` (DEC-03) | §10.2, §11.11, §12.1, §12.4, §13 |
| REV-03 | AUD-003 | Pipeline states for profiling, features, conditional training, scoring, ring analysis; resume points; E2E from empty registry | §7.6, §7.7, §27.7 |
| REV-04 | AUD-004 | Dataset-namespaced IDs (`{dataset_key}:{source_ref}`), PaySim transaction ref synthesis, account type derivation, `UNIQUE(checksum, dataset_version)`, dedup policy; IDs widened to VARCHAR(160) | §6.2, §6.3, §7.1.1, §7.5 |
| REV-05 | AUD-005 | Suspicious-flow vocabulary | §3.5 |
| REV-06 | AUD-006 | Analytical path bounds as deterministic work budgets; complete baseline; residuals by filtering; `truncated` flag | §16.7.2, §16A.5, §16A.7 |
| REV-07 | AUD-007 | Network risk redefined as surviving suspicious risk mass over baseline mass; scenarios bound to a scoring run. **Changes a frozen formula** (justified as a defect: the mean was non-monotone, see §27.4 fixture) | §16A.5, §16A.12 |
| REV-08 | AUD-008 | Additive tables: `account_feature_values`, `account_graph_metrics`, `shap_explanations`, `propagation_contributions`, `ring_memberships`, `evaluation_runs`, `evaluation_metrics`, `case_subjects`, `auth_sessions`, `jobs`, `scoring_runs`, `active_context`, `dataset_profiles`; `scoring_run_id` on assessments; motif GIN index | §6.3 |
| REV-09 | AUD-009 | G_SET and B_SET with equal weights; normalization methods and the 101-point quantile reference; R01 rewritten on a registry quantity; decimal arithmetic rounded half-even to 7 dp before tiers | §12.2–§12.5 |
| REV-10 | AUD-010 | Observation construction, retrospective detection (DEC-05), split percentiles, first-split entity assignment, MERCHANT exclusion, NaN encoding | §10.3, §11.2–§11.6 |
| REV-11 | AUD-011 | Engine tiers (NetworkX reference, GDS benchmark with concurrency 1); reference slice (DEC-01); canonical community IDs | §1.6, §7.1.2, §8.2 |
| REV-12 | AUD-012 | Neo4j labels, properties, constraints, `snapshot_key` scoping, aggregated `TRANSFERRED_TO`, blue/green build, validation digest, retirement (`410`) | §6.8, §6.9 |
| REV-13 | AUD-013 | Worker process; PostgreSQL job table with `SKIP LOCKED`, advisory lock per dataset, lease and heartbeat; simulations and evaluation as jobs | §4.4, §7.8 |
| REV-14 | AUD-014 | RANK and EVALUATE modes; one candidate per account; network-scoped scenarios deferred (`target_ring_id` NOT NULL) | §16A.3, §16A.4, §19.15 |
| REV-15 | AUD-015 | UUIDv5 identifiers for communities, rings, motifs, paths, intervention candidates, reference rings | §6.2.3 |
| REV-16 | AUD-016 | Motif ordering (non-decreasing timestamps, `order_ambiguous`), maximal sequences, greedy fan segmentation, trailing 168-bucket burst baseline, per-anchor expansion limit | §15.9 |
| REV-17 | AUD-017 | Ring membership = all community members; `candidate_class`; candidate signal T renamed `community_temporal_density`; FI/FO defined; CP tied to CIRCULAR_FLOW motifs; MFC dominant set = paths covering ≥ 50% of flow; TC restricted to motifs fully inside the ring; `member_risk` bound to the scoring run | §9, §9A |
| REV-18 | AUD-018 | Permission rows for rings, motifs, simulation, evaluation, pipelines, models, subjects; case field and transition table; opaque server-side sessions; user administration endpoints | §17.3, §19.4, §22 |
| REV-19 | AUD-019 | Rule-based intent; JSON-schema output; reference validation; versioned deny-list; concurrency and rate limits; JSON-encoded, length-capped context; only dashboard/backend ports published | §21, §26.6 |
| REV-20 | AUD-020 | Transaction score = max endpoint final score; test-split population; reference rings = WCC of fraud-transaction subgraph with ≥ 3 positive accounts; network and intervention-effectiveness metrics with a degree-ranked baseline; `NOT_MEASURABLE` reporting | §28.7 |
| REV-21 | AUD-032 | Endpoints for ring status, case subjects, pipeline runs, models, users, propagation, evaluation runs, scenario listing; v1.3.2 paths retained as aliases; complete UI mapping | §19.2, §19.2.1, §20.3 |
| REV-22 | AUD-027 | Capped totals (`total_is_capped`); keyset pagination for transactions | §19.6, §19.11 |
| REV-23 | AUD-031 | Regenerated traceability against real services, tables and endpoints; FR-MOTIF promoted; duplicate AT IDs renumbered; README §38 superseded | §1.1, §28.2, §30, Appendix A |

## F.2 Optional enhancements adopted

| Change | Audit finding | What changed | Where |
|---|---|---|---|
| OPT-01 | AUD-028 | PageRank and betweenness enter risk and ring compositions as percentile ranks; raw values remain features | §8.4, §12.2 |
| OPT-02 | AUD-030 | `signal_coverage` and `max_attainable_score` in risk responses; test vector 9 set to 0.95 | §12.8, §19.7, §27.5 |
| OPT-03 | AUD-029 | Motif confidence floor of 2/3 documented; UI shows confidence components | §15.9.7, §20.6 |

## F.3 Other audit findings

| Finding | Disposition | Where |
|---|---|---|
| AUD-021 | Profiling gate (DEC-02); optional synthetic injection, off by default and labelled | §7.9, §7.10 |
| AUD-022 | Aggregated `TRANSFERRED_TO` projection for path traversal | §6.8, §16.1 |
| AUD-024 | SHAP computed on demand and cached | §14.2 |
| AUD-025 | Upload size cap; 30 s covers acceptance only; CLI registration for large files | §19.2, §19.5 |
| AUD-026 | `/health` liveness; `/ready` 503 only when PostgreSQL is down; one-shot migrate and model pull | §26 |

## F.4 Other changes made during cleanup

- Above-limit parameters are rejected (`400 LIMIT_EXCEEDED`) instead of clamped (§19.1).
- F16 and F17 cold start changed from 1 to `UNAVAILABLE` (§10.1).
- F09 cap, F23 previous window, F33 sentinel, F35 definition, and F20/F41 direction clarified (§10.1).
- `risk_assessments` index `(account_id, final_score DESC)` dropped as unused by any query.
- `feature_versions.source_dataset_version` and `graph_snapshot_id` dropped (lineage lives on scoring runs).
- `communities` primary key changed to `(analytics_run_id, community_id)`.
- `findings.description` limited to 20,000 characters.
- Optimistic concurrency on cases (`version`, `409 CASE_VERSION_CONFLICT`).
- Duplicate acceptance IDs renumbered: v1.3.2 had two AT-RING-01 (candidate score and ring extraction) and two AT-INT-05 (candidate pool and zero denominators). Now AT-RING-01 is the candidate score, AT-RING-02..04 are ring extraction, features, and risk (formerly AT-RING-01..03); AT-INT-05 is the candidate pool and AT-INT-08 the zero-denominator case.
- New acceptance tests: AT-DATA-04/05, AT-GRAPH-04/05, AT-RING-05, AT-FEAT-04, AT-PROP-03, AT-FLOW-04, AT-INT-09/10, AT-INV-04..06, AT-SEC-04/05, AT-AI-05, AT-OPS-03..06.
- Risk terminology moved from §30.3 to §12.10.
- The stray revision row in §1 removed.

## F.6 Design-review fixes (review of 2026-10-17, findings F-01 to F-14)

Each finding was checked against this document. "Already resolved" means the v1.3.3 audit corrections had removed the defect; only the remaining gaps were changed.

| Finding | Status in v1.3.3 | Change made | Where |
|---|---|---|---|
| F-01 Community foreign keys | Partly resolved (composite PK existed; FKs were written against `community_id` alone) | Every community reference is now an explicit composite FK `(analytics_run_id, community_id)`; `ring_feature_sets` gains `analytics_run_id`; the identity scope is explained. The analytics run is used instead of the snapshot because one snapshot can carry several analytics runs. | §6.3.4, §6.3.5 |
| F-02 Feature time vs label time | Partly resolved (retrospective detection was chosen in DEC-05) | Target written as exact intervals per split; the task is stated as retrospective detection with no forward horizon; feature/label separation is by label column, not time; new leakage check 7 (label window containment); AT-ML-02 updated | §11.2–§11.4, §11.6, §28.2 |
| F-03 Suspicious transaction | Partly resolved (§3.5 defined it) | Named predicates `is_suspicious_account` and `is_suspicious_transaction` with inputs, versioned threshold, unavailable-signal behavior, and an explicit ban on source labels as inputs | §3.5 |
| F-04 MFC | Not resolved (the v1.3.3 "≥ 50% coverage" rule was itself degenerate: MFC always fell between 0.5 and 1) | MFC redefined as deterministic top-k concentration with `mfc_top_k = 3`, explicit ranking, tie-break, unique-transaction counting and denominator | §9A.2, §23.2 |
| F-05 Intervention candidate bound | Already resolved: RANK generates single-account and single-edge candidates only, capped at `intervention_max_candidates = 5,000`; account sets exist only in EVALUATE with user-chosen targets | One clarifying sentence: combinations are never enumerated; the per-scenario evaluation bound is stated | §16A.4.4 |
| F-06 Network-scoped API | Already resolved: network-scoped scenarios are out of MVP scope and `target_ring_id` is NOT NULL | None | §1.3, §16A.3, §6.3 |
| F-07 `computed_at` on snapshots | Already resolved: §16A.5 binds by snapshot and scoring-run IDs, not timestamps; no `computed_at` reference to snapshots remains | None | §16A.5 |
| F-08 Path inconsistencies | Already resolved: one canonical path per operation, v1.3.2 paths kept as aliases, traceability regenerated | Stated that UI and traceability paths are relative to `/api/v1` | §19.2.1, §20.3, §30.1 |
| F-09 Duplicate AT IDs | Already resolved (F.4) | None | §28.2 |
| F-10 Ring identity | Partly resolved (deterministic UUIDv5 `candidate_id`) | UNIQUE `(scoring_run_id, analytics_run_id, community_id)`; idempotent insert rule; intervention candidate ID stability stated | §6.3.5, §6.3.7 |
| F-11 Intervention request modes | Already resolved: RANK vs EVALUATE modes with separate validation | None | §16A.3, §19.15 |
| F-12 Durable jobs | Partly resolved (job table, leases, retry) | Explicit durable lifecycle: acceptance committed before `202`, attempts and failure recording, idempotent execution, restart recovery by lease expiry, terminal states; `jobs.failure_category` added | §7.8, §6.3.3 |
| F-13 Traceability precision | Mostly resolved (one row per requirement) | The last three rows without a specific test now link to new AT-OPS-05 (latency benchmark) and AT-OPS-06 (schema constraints) | §28.2, §30.1 |
| F-14 MVP breadth | Not addressed | Delivery sequence with five phases and acceptance-test gates; scope unchanged | §1.7 |

## F.5 Unchanged

All other requirements are carried forward from v1.3.2 without change in meaning, including the 42-feature registry identities, the risk weights (0.50/0.20/0.15/0.10/0.05), tier thresholds, propagation parameters, ring and candidate formulas and thresholds, intervention ranking weights, XGBoost hyperparameters, case state machine, and the role set.

---

# Appendix G — Open Items

| ID | Item | Owner | Blocking |
|---|---|---|---|
| G-01 | Confirm or change DEC-01 (reference slice + NetworkX) | Partha | Implementation planning |
| G-02 | Confirm or change DEC-02 (profiling gate; injection off by default) | Partha | Demo scope |
| G-03 | Confirm or change DEC-03 (`RISK_FEATURES_UNAVAILABLE`) | Partha | ML and risk work |
| G-04 | Confirm or change DEC-04 (one active dataset) | Partha | API work |
| G-05 | Confirm or change DEC-05 (retrospective detection) | Partha | ML work |
| G-06 | Run the profiling report on the chosen PaySim file and review chain depth, account reuse, and fraud-transaction structure | Engineering | Demo scope only |
| G-07 | Future: prior-run regime for risk-derived features; network-scoped interventions; refresh tokens; audit hash chaining; model monitoring | — | No (post-MVP) |
