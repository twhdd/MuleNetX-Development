# Product

<!-- impeccable:product-schema 1 -->

> Written without an interview: the owner asked for an unattended build with no questions. Every fact below comes from `docs/SRS.md`, `docs/PLAN.md`, the backend that exists in this repository, or the owner's written brief. Items marked *(inferred)* are assumptions to confirm.

## Platform

web

## Users

- **Investigators** at a bank's financial-crime or fraud unit. They triage accounts flagged as possible money mules, follow money between accounts, open cases, link subjects and record findings (SRS §17, §22.2 role INVESTIGATOR).
- **Analysts.** They read everything an investigator reads. They can only change cases they created or are assigned to, and they never resolve a case (§22.2 role ANALYST).
- **Administrators.** They upload PaySim datasets, watch pipeline runs reach READY, inspect dataset profiles and model versions, manage users and read the audit log (§22.2 role ADMIN).
- *(inferred)* Long working sessions at a desk, often on large or multiple monitors in a dim operations room.

## Product Purpose

MuleNetX is a graph-based money-mule detection and investigation system. It ingests transaction data and builds a transaction graph. From that graph it computes analytics and features, trains an XGBoost model and composes an explainable risk score per account. It then supports an investigation workflow over the result. Success means an investigator can move from a flagged account to an evidenced, reproducible case quickly. They must also always be able to see where each number came from.

## Positioning

Every displayed score is decomposed and traceable. Each score shows its ML, graph, behavioural, rule and propagation components and its signal coverage. It also shows SHAP for the ML part only and the lineage of the snapshot, analytics run, scoring run, model and risk logic it came from. A score is labelled as an analytical signal, never as a determination of fraud.

## Operating Context

- Data: the PaySim synthetic mobile-money dataset (a reference slice is the default). PaySim has **no geography, no names and no device data**. It has accounts, transaction types (PAYMENT, TRANSFER, CASH_OUT, CASH_IN, DEBIT), hourly time steps and amounts.
- The dashboard reads only the backend REST API (`/api/v1`, `docs/openapi.json`). The browser session lives in memory only, so a reload requires login.
- Evidence labels are mandatory (§20.5): FACT, ANALYTICAL SIGNAL, MODEL OUTPUT, ANALYTICAL CANDIDATE, HYPOTHETICAL SIMULATION, INVESTIGATOR FINDING, AI INTERPRETATION.
- The UI states are fixed (§20.4): LOADING, SUCCESS, EMPTY, ERROR, UNAUTHORIZED, UNAVAILABLE, STALE, QUEUED/RUNNING. STALE comes only from `is_stale`; UNAVAILABLE comes only from availability fields or a 503.

## Capabilities and Constraints

- Phase 3 surfaces: login, active-context banner, account search, account workspace (profile, transactions, risk components, propagation, SHAP, features, temporal), graph explorer (bounded neighbourhood), money-flow path view, communities, cases (subjects, findings, role-aware transitions), and admin (ingestion, pipelines, dataset profile, models, users, audit).
- Later phases add rings, motifs, interventions (always labelled Hypothetical Simulation), evaluation and the copilot.
- The UI does no client-side scoring. Every value comes from an API field, and the server enforces authorization and case transitions.
- Stack (PLAN §2, frozen): React 18, TypeScript 5, Vite 5, D3 7, Zustand 4, React Router 6, plain CSS modules. Tests use Vitest, React Testing Library, MSW and Playwright.
- No UI control performs a real blocking action on an account.

## Brand Commitments

- Name: **MuleNetX**.
- The owner supplied `MULENETX_REDESIGNED.jsx` (outside this repo) as the visual inspiration: a black ground, a serif italic for entity names, monospace for data, a green-amber-red risk ramp, a heatmap on the home screen and a D3 force graph explorer. The brief permits "improvements or a full redesign" of that look.

## Evidence on Hand

- A real backend and API with real data once a dataset is ingested (synthetic labelled fixtures in `backend/tests/`).
- **Absent and never to be fabricated:** geography (the inspiration's India state map has no source in PaySim), customer names, analyst names, case counts, monetary totals and any benchmark figures.

## Product Principles

1. Provenance before persuasion. Every number carries its label, lineage and freshness.
2. Signal, not verdict. Scores rank attention; they never accuse.
3. The server decides. The UI offers actions and the API enforces them.
4. Show the shape of the money. Graph structure and flow are first-class, not decoration.
5. Honest states. Loading, empty, stale and unavailable are designed screens, not afterthoughts.

## Accessibility & Inclusion

*(inferred)* WCAG 2.2 AA contrast and full keyboard operation, because the product is an internal tool used for long sessions.
