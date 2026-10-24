"""Application configuration (SRS §23).

One settings class holds every key of SRS §23.2 with its baseline value. Keys marked **V** in §23.2
change analytical results; they are read only when a new version record is created and are copied
into that record. Computations read them from the version record, never from live settings.
"""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

KNOWN_DEFAULT_SECRETS = frozenset({"", "neo4j", "password", "postgres", "changeme", "change_me", "CHANGE_ME"})

JobKind = Literal["INGEST", "PIPELINE_STAGE", "TRAIN", "INTERVENTION", "EVALUATION", "SNAPSHOT_RETIRE"]
JOB_KINDS: tuple[JobKind, ...] = (
    "INGEST",
    "PIPELINE_STAGE",
    "TRAIN",
    "INTERVENTION",
    "EVALUATION",
    "SNAPSHOT_RETIRE",
)


def _dsn_password(dsn: str) -> str | None:
    parts = urlsplit(dsn)
    return parts.password


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", case_sensitive=False)

    # ── Infrastructure and secrets ─────────────────────────────────────────
    postgres_dsn: str
    postgres_owner_dsn: str | None = None
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    mulenetx_bootstrap_admin_username: str | None = None
    mulenetx_bootstrap_admin_password: str | None = None
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["http://localhost:8080"])
    artifact_dir: str = "/data/artifacts"
    staging_dir: str = "/data/staging"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ── Authentication (§22.1) ─────────────────────────────────────────────
    session_idle_minutes: int = Field(default=30, gt=0)
    session_absolute_hours: int = Field(default=12, gt=0)
    login_max_failures: int = Field(default=5, gt=0)
    login_window_minutes: int = Field(default=15, gt=0)
    argon2_time_cost: int = Field(default=3, gt=0)
    argon2_memory_kib: int = Field(default=65536, gt=0)
    argon2_parallelism: int = Field(default=4, gt=0)

    # ── Ingestion, jobs, snapshots (§7, §19.5) ─────────────────────────────
    max_upload_bytes: int = Field(default=1024 * 1024 * 1024, gt=0)
    job_lease_seconds: int = Field(default=60, gt=0)
    job_heartbeat_seconds: float = Field(default=15, gt=0)
    job_max_attempts: int = Field(default=3, ge=1)
    job_timeout_ingest_seconds: int = Field(default=3600, gt=0)
    job_timeout_pipeline_stage_seconds: int = Field(default=7200, gt=0)
    job_timeout_train_seconds: int = Field(default=7200, gt=0)
    job_timeout_intervention_seconds: int = Field(default=1800, gt=0)
    job_timeout_evaluation_seconds: int = Field(default=3600, gt=0)
    job_timeout_snapshot_retire_seconds: int = Field(default=1800, gt=0)
    graph_build_batch_size: int = Field(default=10_000, gt=0)
    synthetic_injection_enabled: bool = False
    worker_pipeline_slots: int = Field(default=1, ge=1)
    worker_analysis_slots: int = Field(default=2, ge=1)
    worker_poll_seconds: float = Field(default=1.0, gt=0)

    # ── Versioned analytical parameters (V) ───────────────────────────────
    reference_slice_max_rows: int = Field(default=1_000_000, gt=0)
    paysim_epoch_anchor: datetime = datetime.fromisoformat("2020-01-01T00:00:00+00:00")
    analytics_engine: Literal["REFERENCE"] = "REFERENCE"
    pagerank_damping: float = 0.85
    pagerank_max_iterations: int = 100
    pagerank_tolerance: float = 1e-6
    louvain_resolution: float = 1.0
    louvain_seed: int = 42
    min_candidate_community_size: int = 3
    mfc_top_k: int = 3
    suspicious_threshold: str = "0.50"
    propagation_maximum_distance: int = 3
    propagation_maximum_contribution: str = "0.50"
    propagation_provenance_top_n: int = 5
    motif_max_expansions_per_anchor: int = 100_000
    analytic_max_depth: int = 5
    analytic_max_paths: int = 10_000
    analytic_max_expansions: int = 1_000_000
    split_percentile_train: float = Field(default=0.70, gt=0, lt=1)
    split_percentile_val: float = Field(default=0.85, gt=0, lt=1)
    xgb_n_estimators: int = 300
    xgb_max_depth: int = 6
    xgb_learning_rate: float = 0.05
    xgb_subsample: float = 0.8
    xgb_colsample_bytree: float = 0.8
    xgb_random_seed: int = 42
    xgb_nthread: int = 1
    risk_weight_ml: str = "0.50"
    risk_weight_graph: str = "0.20"
    risk_weight_behavioral: str = "0.15"
    risk_weight_propagation: str = "0.10"
    risk_weight_rules: str = "0.05"
    risk_tier_medium: str = "0.25"
    risk_tier_high: str = "0.50"
    risk_tier_critical: str = "0.75"
    candidate_threshold: str = "0.50"
    ring_candidate_threshold: str = "0.70"
    k_max: int = Field(default=3, ge=1, le=3)
    intervention_max_candidates: int = 5_000

    # ── Money flow, interventions, API (§16.7.1, §19, §25.2) ───────────────
    path_max_depth: int = 5
    path_max_results: int = 50
    path_query_timeout_seconds: float = 5.0
    max_hop_evidence: int = 20
    max_concurrent_scenarios_per_user: int = 2
    graph_max_depth: int = 3
    graph_max_nodes: int = 500
    graph_max_edges: int = 2000
    graph_query_timeout_seconds: float = 5.0
    default_page_size: int = 25
    max_page_size: int = 100
    pagination_count_cap: int = 10_000
    max_transaction_range_days: int = 31
    shap_max_top_n: int = 50
    shap_default_top_n: int = 10

    # ── Copilot (§21) ──────────────────────────────────────────────────────
    copilot_timeout_seconds: float = 20.0
    copilot_max_concurrency: int = 1
    copilot_rate_per_minute: int = 6
    copilot_max_context_tokens: int = 6000
    copilot_max_text_field: int = 1000
    copilot_max_output_tokens: int = 1024
    copilot_deny_list_version: int = 1
    copilot_queue_wait_seconds: float = 2.0

    @field_validator("postgres_dsn")
    @classmethod
    def _postgres_dsn_secret(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("POSTGRES_DSN is required")
        password = _dsn_password(value)
        if password is None or password in KNOWN_DEFAULT_SECRETS:
            raise ValueError("POSTGRES_DSN must carry a non-default password")
        return value

    @field_validator("postgres_owner_dsn")
    @classmethod
    def _owner_dsn_secret(cls, value: str | None) -> str | None:
        if value is None:
            return None
        password = _dsn_password(value)
        if password is None or password in KNOWN_DEFAULT_SECRETS:
            raise ValueError("POSTGRES_OWNER_DSN must carry a non-default password")
        return value

    @field_validator("neo4j_password")
    @classmethod
    def _neo4j_secret(cls, value: str) -> str:
        if value in KNOWN_DEFAULT_SECRETS:
            raise ValueError("NEO4J_PASSWORD must be set to a non-default secret")
        return value

    @field_validator("mulenetx_bootstrap_admin_password")
    @classmethod
    def _bootstrap_secret(cls, value: str | None) -> str | None:
        if value is not None and value in KNOWN_DEFAULT_SECRETS:
            raise ValueError("MULENETX_BOOTSTRAP_ADMIN_PASSWORD must not be empty or a default")
        return value

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value

    @model_validator(mode="after")
    def _no_wildcard_cors(self) -> Settings:
        if any(origin == "*" for origin in self.cors_allowed_origins):
            raise ValueError("CORS_ALLOWED_ORIGINS must not contain a wildcard")
        return self

    def job_timeout_seconds(self, kind: str) -> int:
        timeouts: dict[str, int] = {
            "INGEST": self.job_timeout_ingest_seconds,
            "PIPELINE_STAGE": self.job_timeout_pipeline_stage_seconds,
            "TRAIN": self.job_timeout_train_seconds,
            "INTERVENTION": self.job_timeout_intervention_seconds,
            "EVALUATION": self.job_timeout_evaluation_seconds,
            "SNAPSHOT_RETIRE": self.job_timeout_snapshot_retire_seconds,
        }
        return timeouts[kind]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # values come from the environment
