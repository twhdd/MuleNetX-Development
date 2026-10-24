"""Pipeline and lineage tables (SRS §6.3.3).

Revision ID: 0002_pipeline_lineage
Revises: 0001_identity_canonical
"""

from alembic import op

revision = "0002_pipeline_lineage"
down_revision = "0001_identity_canonical"
branch_labels = None
depends_on = None

R = "ON UPDATE RESTRICT ON DELETE RESTRICT"

PIPELINE_STATES = (
    "CREATED", "INGESTING", "INGESTED", "PROFILING", "PROFILED", "GRAPH_BUILDING", "GRAPH_READY",
    "ANALYTICS_RUNNING", "ANALYTICS_READY", "FEATURES_RUNNING", "FEATURES_READY", "TRAINING",
    "MODEL_READY", "SCORING", "SCORED", "RING_ANALYSIS", "READY", "FAILED",
)
STATES_SQL = ",".join(f"'{s}'" for s in PIPELINE_STATES)

UPGRADE = f"""
CREATE TABLE dataset_profiles (
    dataset_id      UUID PRIMARY KEY REFERENCES datasets(dataset_id) {R},
    profile_version VARCHAR(50) NOT NULL,
    metrics         JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL
);

CREATE TABLE ingestion_runs (
    ingestion_run_id  UUID PRIMARY KEY,
    dataset_id        UUID NOT NULL REFERENCES datasets(dataset_id) {R},
    pipeline_version  VARCHAR(100) NOT NULL,
    started_at        TIMESTAMPTZ NOT NULL,
    completed_at      TIMESTAMPTZ NULL,
    status            VARCHAR(20) NOT NULL CONSTRAINT ingestion_runs_status_ck
                      CHECK (status IN ('CREATED','RUNNING','SUCCEEDED','FAILED')),
    records_seen      BIGINT NOT NULL CONSTRAINT ingestion_runs_seen_ck CHECK (records_seen >= 0),
    records_accepted  BIGINT NOT NULL CONSTRAINT ingestion_runs_accepted_ck CHECK (records_accepted >= 0),
    records_rejected  BIGINT NOT NULL CONSTRAINT ingestion_runs_rejected_ck CHECK (records_rejected >= 0),
    records_duplicate BIGINT NOT NULL CONSTRAINT ingestion_runs_duplicate_ck CHECK (records_duplicate >= 0),
    rejection_summary JSONB NOT NULL,
    error_summary     TEXT NULL
);
CREATE INDEX ingestion_runs_dataset_started_ix ON ingestion_runs (dataset_id, started_at DESC);
CREATE INDEX ingestion_runs_status_started_ix ON ingestion_runs (status, started_at DESC);

ALTER TABLE transactions ADD CONSTRAINT transactions_ingestion_run_fk
    FOREIGN KEY (ingestion_run_id) REFERENCES ingestion_runs(ingestion_run_id) {R};

CREATE TABLE graph_snapshots (
    graph_snapshot_id    UUID PRIMARY KEY,
    dataset_id           UUID NOT NULL REFERENCES datasets(dataset_id) {R},
    ingestion_run_id     UUID NOT NULL REFERENCES ingestion_runs(ingestion_run_id) {R},
    purpose              VARCHAR(20) NOT NULL CONSTRAINT graph_snapshots_purpose_ck
                         CHECK (purpose IN ('OPERATIONAL','TRAINING_SPLIT')),
    data_cutoff          TIMESTAMPTZ NOT NULL,
    pipeline_version     VARCHAR(100) NOT NULL,
    graph_schema_version VARCHAR(50) NOT NULL,
    source_record_count  BIGINT NOT NULL CONSTRAINT graph_snapshots_src_count_ck CHECK (source_record_count >= 0),
    node_count           BIGINT NULL CONSTRAINT graph_snapshots_node_count_ck CHECK (node_count >= 0),
    edge_count           BIGINT NULL CONSTRAINT graph_snapshots_edge_count_ck CHECK (edge_count >= 0),
    validation_digest    CHAR(64) NULL,
    status               VARCHAR(20) NOT NULL CONSTRAINT graph_snapshots_status_ck
                         CHECK (status IN ('BUILDING','VALIDATING','READY','FAILED','RETIRED')),
    created_at           TIMESTAMPTZ NOT NULL,
    ready_at             TIMESTAMPTZ NULL
);
CREATE INDEX graph_snapshots_dataset_purpose_cutoff_ix ON graph_snapshots (dataset_id, purpose, data_cutoff DESC);
CREATE INDEX graph_snapshots_status_ix ON graph_snapshots (status);

CREATE TABLE analytics_runs (
    analytics_run_id        UUID PRIMARY KEY,
    graph_snapshot_id       UUID NOT NULL REFERENCES graph_snapshots(graph_snapshot_id) {R},
    analytics_version       VARCHAR(100) NOT NULL,
    engine                  VARCHAR(30) NOT NULL CONSTRAINT analytics_runs_engine_ck
                            CHECK (engine IN ('NETWORKX','NEO4J_GDS')),
    algorithm_configuration JSONB NOT NULL,
    started_at              TIMESTAMPTZ NOT NULL,
    completed_at            TIMESTAMPTZ NULL,
    status                  VARCHAR(20) NOT NULL CONSTRAINT analytics_runs_status_ck
                            CHECK (status IN ('RUNNING','SUCCEEDED','FAILED')),
    error_summary           TEXT NULL
);
CREATE INDEX analytics_runs_snapshot_started_ix ON analytics_runs (graph_snapshot_id, started_at DESC);
CREATE INDEX analytics_runs_status_ix ON analytics_runs (status);

CREATE TABLE feature_versions (
    feature_version            VARCHAR(100) PRIMARY KEY,
    definition_hash            CHAR(64) NOT NULL CONSTRAINT feature_versions_hash_uq UNIQUE,
    feature_count              INTEGER NOT NULL CONSTRAINT feature_versions_count_ck CHECK (feature_count > 0),
    feature_registry_reference TEXT NOT NULL,
    created_at                 TIMESTAMPTZ NOT NULL
);

CREATE TABLE model_versions (
    model_version          VARCHAR(100) PRIMARY KEY,
    model_type             VARCHAR(100) NOT NULL,
    target_definition      JSONB NOT NULL,
    feature_version        VARCHAR(100) NOT NULL REFERENCES feature_versions(feature_version) {R},
    feature_regime         VARCHAR(40) NOT NULL CONSTRAINT model_versions_regime_ck
                           CHECK (feature_regime IN ('RISK_FEATURES_UNAVAILABLE')),
    training_dataset_id    UUID NOT NULL REFERENCES datasets(dataset_id) {R},
    training_snapshot_ids  JSONB NOT NULL,
    split_boundaries       JSONB NOT NULL,
    training_config        JSONB NOT NULL,
    class_distribution     JSONB NOT NULL,
    evaluation_metrics     JSONB NOT NULL,
    operating_threshold    NUMERIC(8,7) NOT NULL CONSTRAINT model_versions_threshold_ck
                           CHECK (operating_threshold >= 0 AND operating_threshold <= 1),
    artifact_reference     TEXT NOT NULL,
    artifact_sha256        CHAR(64) NOT NULL,
    implementation_version VARCHAR(100) NOT NULL,
    random_seed            INTEGER NOT NULL,
    created_at             TIMESTAMPTZ NOT NULL
);
CREATE INDEX model_versions_feature_version_ix ON model_versions (feature_version);
CREATE INDEX model_versions_created_ix ON model_versions (created_at DESC);

CREATE TABLE risk_logic_versions (
    risk_logic_version      VARCHAR(100) PRIMARY KEY,
    formula_identifier      VARCHAR(100) NOT NULL,
    configuration           JSONB NOT NULL,
    normalization_reference JSONB NOT NULL,
    rules                   JSONB NOT NULL,
    tier_thresholds         JSONB NOT NULL,
    propagation_parameters  JSONB NOT NULL,
    ring_parameters         JSONB NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL
);

CREATE TABLE scoring_runs (
    scoring_run_id      UUID PRIMARY KEY,
    graph_snapshot_id   UUID NOT NULL REFERENCES graph_snapshots(graph_snapshot_id) {R},
    analytics_run_id    UUID NOT NULL REFERENCES analytics_runs(analytics_run_id) {R},
    as_of               TIMESTAMPTZ NOT NULL,
    feature_version     VARCHAR(100) NOT NULL REFERENCES feature_versions(feature_version) {R},
    feature_snapshot_id UUID NOT NULL,
    model_version       VARCHAR(100) NULL REFERENCES model_versions(model_version) {R},
    risk_logic_version  VARCHAR(100) NOT NULL REFERENCES risk_logic_versions(risk_logic_version) {R},
    started_at          TIMESTAMPTZ NOT NULL,
    completed_at        TIMESTAMPTZ NULL,
    status              VARCHAR(20) NOT NULL CONSTRAINT scoring_runs_status_ck
                        CHECK (status IN ('RUNNING','SUCCEEDED','FAILED')),
    accounts_scored     BIGINT NULL CONSTRAINT scoring_runs_scored_ck CHECK (accounts_scored >= 0)
);
CREATE INDEX scoring_runs_snapshot_started_ix ON scoring_runs (graph_snapshot_id, started_at DESC);
CREATE INDEX scoring_runs_status_ix ON scoring_runs (status);

CREATE TABLE pipeline_runs (
    pipeline_run_id      UUID PRIMARY KEY,
    dataset_id           UUID NOT NULL REFERENCES datasets(dataset_id) {R},
    ingestion_run_id     UUID NULL REFERENCES ingestion_runs(ingestion_run_id) {R},
    current_state        VARCHAR(30) NOT NULL CONSTRAINT pipeline_runs_state_ck CHECK (current_state IN ({STATES_SQL})),
    graph_snapshot_id    UUID NULL REFERENCES graph_snapshots(graph_snapshot_id) {R},
    analytics_run_id     UUID NULL REFERENCES analytics_runs(analytics_run_id) {R},
    scoring_run_id       UUID NULL REFERENCES scoring_runs(scoring_run_id) {R},
    model_version        VARCHAR(100) NULL REFERENCES model_versions(model_version) {R},
    started_at           TIMESTAMPTZ NOT NULL,
    updated_at           TIMESTAMPTZ NOT NULL,
    completed_at         TIMESTAMPTZ NULL,
    failure_stage        VARCHAR(30) NULL,
    failure_category     VARCHAR(50) NULL,
    safe_failure_message TEXT NULL,
    resumable_from       VARCHAR(30) NULL
);
CREATE INDEX pipeline_runs_dataset_started_ix ON pipeline_runs (dataset_id, started_at DESC);
CREATE INDEX pipeline_runs_state_updated_ix ON pipeline_runs (current_state, updated_at DESC);

CREATE TABLE jobs (
    job_id           UUID PRIMARY KEY,
    kind             VARCHAR(40) NOT NULL CONSTRAINT jobs_kind_ck
                     CHECK (kind IN ('INGEST','PIPELINE_STAGE','TRAIN','INTERVENTION','EVALUATION','SNAPSHOT_RETIRE')),
    payload          JSONB NOT NULL,
    status           VARCHAR(20) NOT NULL CONSTRAINT jobs_status_ck
                     CHECK (status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED')),
    lock_key         BIGINT NULL,
    attempts         INTEGER NOT NULL CONSTRAINT jobs_attempts_ck CHECK (attempts >= 0),
    max_attempts     INTEGER NOT NULL CONSTRAINT jobs_max_attempts_ck CHECK (max_attempts >= 1),
    lease_owner      VARCHAR(100) NULL,
    lease_expires_at TIMESTAMPTZ NULL,
    requested_by     UUID NULL REFERENCES users(user_id) {R},
    request_id       VARCHAR(100) NULL,
    created_at       TIMESTAMPTZ NOT NULL,
    started_at       TIMESTAMPTZ NULL,
    completed_at     TIMESTAMPTZ NULL,
    failure_category VARCHAR(40) NULL,
    error_summary    TEXT NULL
);
CREATE INDEX jobs_status_created_ix ON jobs (status, created_at);
CREATE INDEX jobs_kind_status_ix ON jobs (kind, status);
CREATE INDEX jobs_running_lease_ix ON jobs (lease_expires_at) WHERE status = 'RUNNING';

CREATE TABLE active_context (
    singleton                  BOOLEAN PRIMARY KEY CONSTRAINT active_context_singleton_ck CHECK (singleton),
    dataset_id                 UUID NULL REFERENCES datasets(dataset_id) {R},
    graph_snapshot_id          UUID NULL REFERENCES graph_snapshots(graph_snapshot_id) {R},
    analytics_run_id           UUID NULL REFERENCES analytics_runs(analytics_run_id) {R},
    scoring_run_id             UUID NULL REFERENCES scoring_runs(scoring_run_id) {R},
    model_version              VARCHAR(100) NULL REFERENCES model_versions(model_version) {R},
    risk_logic_version         VARCHAR(100) NULL REFERENCES risk_logic_versions(risk_logic_version) {R},
    updated_at                 TIMESTAMPTZ NOT NULL,
    updated_by_pipeline_run_id UUID NULL REFERENCES pipeline_runs(pipeline_run_id) {R}
);
INSERT INTO active_context (singleton, updated_at) VALUES (TRUE, now());
"""

DOWNGRADE = """
DROP TABLE active_context;
DROP TABLE jobs;
DROP TABLE pipeline_runs;
DROP TABLE scoring_runs;
DROP TABLE risk_logic_versions;
DROP TABLE model_versions;
DROP TABLE feature_versions;
DROP TABLE analytics_runs;
DROP TABLE graph_snapshots;
ALTER TABLE transactions DROP CONSTRAINT transactions_ingestion_run_fk;
DROP TABLE ingestion_runs;
DROP TABLE dataset_profiles;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
