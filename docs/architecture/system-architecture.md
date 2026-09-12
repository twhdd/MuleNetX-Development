# MuleNetX System Architecture

## Vision

MuleNetX is a graph-based financial crime intelligence platform designed to detect, analyze, investigate, and explain suspicious transaction networks using graph analytics, machine learning, and local AI models.

---

## Core Architecture

```text
Dashboard
    ↓
FastAPI Backend
    ↓
─────────────────────────────
│            │             │
PostgreSQL   Neo4j      ML Engine
│            │             │
│            │         XGBoost
│            │         Isolation Forest
│            │         Graph Neural Networks
│            │         SHAP
│            │
│      Intelligence Core
│      ├─ PageRank
│      ├─ Centrality
│      ├─ Community Detection
│      ├─ Path Tracing
│      └─ Simulation
│
Investigation Engine
│
Ollama
│
Qwen
```

---

## Dashboard Responsibilities

* Intelligence Dashboard
* India Heatmap
* Graph Explorer
* Case Management
* Investigation Copilot
* Analytics Visualizations
* Model Monitoring

Technology:

* React
* D3.js
* TailwindCSS
* TypeScript (future)

---

## Backend Responsibilities

* API Gateway
* Authentication
* Service Orchestration
* Database Connections
* Data Retrieval
* Alert Management

Technology:

* FastAPI
* SQLAlchemy
* Pydantic

---

## PostgreSQL Responsibilities

Stores:

* Transactions
* Accounts
* Cases
* Alerts
* User Data
* Investigation Notes

---

## Neo4j Responsibilities

Stores:

* Transaction Networks
* Account Relationships
* Device Relationships
* IP Relationships
* Fraud Rings

Supports:

* Path Discovery
* Ring Detection
* Community Detection
* Graph Queries

---

## Intelligence Core Responsibilities

Graph Algorithms:

* PageRank
* Degree Centrality
* Betweenness Centrality
* Closeness Centrality
* Community Detection

Advanced Features:

* Transaction Tracing
* Fraud Ring Discovery
* Digital Twin Simulation

---

## ML Engine Responsibilities

Models:

* XGBoost
* Random Forest
* Isolation Forest
* GraphSAGE
* Graph Neural Networks

Features:

* Fraud Scoring
* Anomaly Detection
* Risk Prediction
* Pattern Recognition

---

## Explainability Layer

Technology:

* SHAP

Purpose:

* Explain model decisions
* Generate analyst-friendly reasoning
* Highlight influential features

---

## Investigation Engine Responsibilities

Features:

* Case Management
* AI Investigation Assistant
* PDF Report Generation
* Evidence Collection
* Investigation History

---

## Local AI Layer

Technology:

* Ollama
* Qwen

Purpose:

* Explain suspicious activity
* Generate investigation summaries
* Answer analyst questions
* Produce case reports

The AI layer never performs fraud detection directly.

Fraud detection is performed by the Intelligence Core and ML Engine.

The AI layer only explains and summarizes evidence.

---

## Initial Dataset Strategy

Primary Dataset:

* PaySim

---

