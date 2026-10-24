"""Investigation and evaluation tables (SRS §6.3.8, §6.3.9).

Revision ID: 0005_investigation_evaluation
Revises: 0004_rings_motifs_interventions
"""

from alembic import op

revision = "0005_investigation_evaluation"
down_revision = "0004_rings_motifs_interventions"
branch_labels = None
depends_on = None

R = "ON UPDATE RESTRICT ON DELETE RESTRICT"

UPGRADE = f"""
CREATE TABLE cases (
    case_id     UUID PRIMARY KEY,
    title       VARCHAR(250) NOT NULL CONSTRAINT cases_title_nonempty CHECK (length(title) > 0),
    status      VARCHAR(30) NOT NULL CONSTRAINT cases_status_ck
                CHECK (status IN ('OPEN','IN_REVIEW','ESCALATED','RESOLVED','FALSE_POSITIVE','CLOSED')),
    priority    VARCHAR(20) NOT NULL CONSTRAINT cases_priority_ck CHECK (priority IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    assigned_to UUID NULL REFERENCES users(user_id) {R},
    created_by  UUID NOT NULL REFERENCES users(user_id) {R},
    created_at  TIMESTAMPTZ NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL,
    closed_at   TIMESTAMPTZ NULL,
    version     INTEGER NOT NULL CONSTRAINT cases_version_ck CHECK (version >= 1),
    CONSTRAINT cases_closed_at_ck CHECK ((status = 'CLOSED') = (closed_at IS NOT NULL))
);
CREATE INDEX cases_status_updated_ix ON cases (status, updated_at DESC);
CREATE INDEX cases_assigned_status_ix ON cases (assigned_to, status);
CREATE INDEX cases_created_by_ix ON cases (created_by);
CREATE INDEX cases_created_at_ix ON cases (created_at DESC);

CREATE TABLE case_subjects (
    case_id      UUID NOT NULL REFERENCES cases(case_id) {R},
    subject_type VARCHAR(20) NOT NULL CONSTRAINT case_subjects_type_ck
                 CHECK (subject_type IN ('ACCOUNT','TRANSACTION','RING','SCENARIO')),
    subject_id   VARCHAR(160) NOT NULL,
    added_by     UUID NOT NULL REFERENCES users(user_id) {R},
    added_at     TIMESTAMPTZ NOT NULL,
    removed_by   UUID NULL REFERENCES users(user_id) {R},
    removed_at   TIMESTAMPTZ NULL,
    CONSTRAINT case_subjects_pk PRIMARY KEY (case_id, subject_type, subject_id, added_at)
);
CREATE INDEX case_subjects_subject_ix ON case_subjects (subject_type, subject_id);

CREATE TABLE findings (
    finding_id  UUID PRIMARY KEY,
    case_id     UUID NOT NULL REFERENCES cases(case_id) {R},
    type        VARCHAR(50) NOT NULL CONSTRAINT findings_type_nonempty CHECK (length(type) > 0),
    description TEXT NOT NULL CONSTRAINT findings_description_ck
                CHECK (length(description) > 0 AND length(description) <= 20000),
    evidence    JSONB NOT NULL,
    source      VARCHAR(100) NOT NULL CONSTRAINT findings_source_nonempty CHECK (length(source) > 0),
    created_by  UUID NOT NULL REFERENCES users(user_id) {R},
    created_at  TIMESTAMPTZ NOT NULL
);
CREATE INDEX findings_case_created_ix ON findings (case_id, created_at);
CREATE INDEX findings_creator_created_ix ON findings (created_by, created_at);

CREATE TABLE evaluation_runs (
    evaluation_run_id              UUID PRIMARY KEY,
    dataset_id                     UUID NOT NULL REFERENCES datasets(dataset_id) {R},
    model_version                  VARCHAR(100) NOT NULL REFERENCES model_versions(model_version) {R},
    test_snapshot_id               UUID NOT NULL REFERENCES graph_snapshots(graph_snapshot_id) {R},
    scoring_run_id                 UUID NOT NULL REFERENCES scoring_runs(scoring_run_id) {R},
    analytics_version              VARCHAR(100) NOT NULL,
    risk_logic_version             VARCHAR(100) NOT NULL REFERENCES risk_logic_versions(risk_logic_version) {R},
    reference_construction_version VARCHAR(50) NOT NULL,
    configuration                  JSONB NOT NULL,
    status                         VARCHAR(20) NOT NULL CONSTRAINT er_status_ck
                                   CHECK (status IN ('QUEUED','RUNNING','COMPLETED','FAILED')),
    created_at                     TIMESTAMPTZ NOT NULL,
    completed_at                   TIMESTAMPTZ NULL
);

CREATE TABLE evaluation_metrics (
    evaluation_run_id UUID NOT NULL REFERENCES evaluation_runs(evaluation_run_id) {R},
    level             VARCHAR(20) NOT NULL CONSTRAINT em_level_ck CHECK (level IN ('TRANSACTION','ACCOUNT','RING','NETWORK')),
    metric            VARCHAR(60) NOT NULL,
    value             DOUBLE PRECISION NULL,
    sample_count      BIGINT NOT NULL CONSTRAINT em_sample_count_ck CHECK (sample_count >= 0),
    availability      VARCHAR(20) NOT NULL CONSTRAINT em_availability_ck CHECK (availability IN ('AVAILABLE','UNAVAILABLE')),
    details           JSONB NULL,
    CONSTRAINT evaluation_metrics_pk PRIMARY KEY (evaluation_run_id, level, metric)
);
"""

DOWNGRADE = """
DROP TABLE evaluation_metrics;
DROP TABLE evaluation_runs;
DROP TABLE findings;
DROP TABLE case_subjects;
DROP TABLE cases;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
