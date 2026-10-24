"""Identity and canonical financial data (SRS §6.3.1, §6.3.2, §6.3.8 audit_events).

Revision ID: 0001_identity_canonical
Revises:
"""

from alembic import op

revision = "0001_identity_canonical"
down_revision = None
branch_labels = None
depends_on = None

R = "ON UPDATE RESTRICT ON DELETE RESTRICT"

UPGRADE = f"""
CREATE SCHEMA IF NOT EXISTS staging;
GRANT USAGE, CREATE ON SCHEMA staging TO mulenetx_app;

CREATE TABLE users (
    user_id        UUID PRIMARY KEY,
    username       VARCHAR(100) NOT NULL CONSTRAINT users_username_uq UNIQUE
                   CONSTRAINT users_username_nonempty CHECK (length(username) > 0),
    password_hash  TEXT NOT NULL,
    role           VARCHAR(20) NOT NULL CONSTRAINT users_role_ck CHECK (role IN ('ADMIN','INVESTIGATOR','ANALYST')),
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at  TIMESTAMPTZ NULL
);
CREATE INDEX users_role_active_ix ON users (role, is_active);

CREATE TABLE auth_sessions (
    session_id          UUID PRIMARY KEY,
    token_hash          CHAR(64) NOT NULL CONSTRAINT auth_sessions_token_hash_uq UNIQUE,
    user_id             UUID NOT NULL REFERENCES users(user_id) {R},
    role_at_issue       VARCHAR(20) NOT NULL
                        CONSTRAINT auth_sessions_role_ck CHECK (role_at_issue IN ('ADMIN','INVESTIGATOR','ANALYST')),
    created_at          TIMESTAMPTZ NOT NULL,
    last_seen_at        TIMESTAMPTZ NOT NULL,
    idle_expires_at     TIMESTAMPTZ NOT NULL,
    absolute_expires_at TIMESTAMPTZ NOT NULL,
    revoked_at          TIMESTAMPTZ NULL,
    revocation_reason   VARCHAR(30) NULL CONSTRAINT auth_sessions_reason_ck
                        CHECK (revocation_reason IN ('LOGOUT','DEACTIVATED','ROLE_CHANGED','ADMIN','EXPIRED'))
);
CREATE INDEX auth_sessions_user_revoked_ix ON auth_sessions (user_id, revoked_at);

CREATE TABLE datasets (
    dataset_id                   UUID PRIMARY KEY,
    dataset_key                  VARCHAR(24) NOT NULL CONSTRAINT datasets_key_uq UNIQUE
                                 CONSTRAINT datasets_key_ck CHECK (dataset_key ~ '^[a-z0-9_-]{{1,24}}$'),
    name                         VARCHAR(200) NOT NULL CONSTRAINT datasets_name_nonempty CHECK (length(name) > 0),
    source                       VARCHAR(100) NOT NULL CONSTRAINT datasets_source_nonempty CHECK (length(source) > 0),
    dataset_version              VARCHAR(100) NOT NULL,
    schema_version               VARCHAR(50) NOT NULL,
    adapter                      VARCHAR(50) NOT NULL,
    adapter_config               JSONB NOT NULL,
    checksum                     CHAR(64) NOT NULL,
    timestamp_resolution_seconds INTEGER NOT NULL CONSTRAINT datasets_resolution_ck
                                 CHECK (timestamp_resolution_seconds > 0),
    is_synthetic_injection       BOOLEAN NOT NULL DEFAULT FALSE,
    record_count                 BIGINT NULL CONSTRAINT datasets_record_count_ck CHECK (record_count >= 0),
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT datasets_name_version_uq UNIQUE (name, dataset_version),
    CONSTRAINT datasets_checksum_version_uq UNIQUE (checksum, dataset_version)
);

CREATE TABLE accounts (
    account_id                VARCHAR(160) PRIMARY KEY,
    dataset_id                UUID NOT NULL REFERENCES datasets(dataset_id) {R},
    source_account_ref        VARCHAR(128) NOT NULL
                              CONSTRAINT accounts_ref_nonempty CHECK (length(source_account_ref) > 0),
    account_type              VARCHAR(50) NOT NULL CONSTRAINT accounts_type_nonempty CHECK (length(account_type) > 0),
    created_at                TIMESTAMPTZ NULL,
    risk_score                NUMERIC(8,7) NULL CONSTRAINT accounts_risk_score_ck CHECK (risk_score >= 0 AND risk_score <= 1),
    risk_tier                 VARCHAR(20) NULL CONSTRAINT accounts_risk_tier_ck
                              CHECK (risk_tier IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    community_id              VARCHAR(64) NULL,
    latest_risk_assessment_id UUID NULL,
    CONSTRAINT accounts_dataset_ref_uq UNIQUE (dataset_id, source_account_ref),
    CONSTRAINT accounts_dataset_account_uq UNIQUE (dataset_id, account_id)
);
CREATE INDEX accounts_dataset_tier_score_ix ON accounts (dataset_id, risk_tier, risk_score DESC);
CREATE INDEX accounts_dataset_community_ix ON accounts (dataset_id, community_id);
CREATE INDEX accounts_ref_prefix_ix ON accounts (source_account_ref text_pattern_ops);

CREATE TABLE transactions (
    transaction_id         VARCHAR(160) PRIMARY KEY,
    dataset_id             UUID NOT NULL REFERENCES datasets(dataset_id) {R},
    ingestion_run_id       UUID NOT NULL,
    source_transaction_ref VARCHAR(128) NOT NULL,
    source_account_id      VARCHAR(160) NOT NULL,
    destination_account_id VARCHAR(160) NOT NULL,
    amount                 NUMERIC(20,6) NOT NULL CONSTRAINT transactions_amount_ck CHECK (amount >= 0),
    "timestamp"            TIMESTAMPTZ NOT NULL,
    transaction_type       VARCHAR(50) NOT NULL CONSTRAINT transactions_type_nonempty CHECK (length(transaction_type) > 0),
    fraud_label            BOOLEAN NULL,
    source_record_hash     CHAR(64) NOT NULL,
    CONSTRAINT transactions_dataset_ref_uq UNIQUE (dataset_id, source_transaction_ref),
    CONSTRAINT transactions_source_fk FOREIGN KEY (dataset_id, source_account_id)
        REFERENCES accounts(dataset_id, account_id) {R},
    CONSTRAINT transactions_destination_fk FOREIGN KEY (dataset_id, destination_account_id)
        REFERENCES accounts(dataset_id, account_id) {R}
);
CREATE INDEX transactions_source_ts_ix ON transactions (source_account_id, "timestamp" DESC, transaction_id);
CREATE INDEX transactions_destination_ts_ix ON transactions (destination_account_id, "timestamp" DESC, transaction_id);
CREATE INDEX transactions_dataset_ts_ix ON transactions (dataset_id, "timestamp", transaction_id);
CREATE INDEX transactions_ingestion_run_ix ON transactions (ingestion_run_id);
CREATE INDEX transactions_dataset_hash_ix ON transactions (dataset_id, source_record_hash);

CREATE TABLE audit_events (
    event_id      UUID PRIMARY KEY,
    user_id       UUID NULL REFERENCES users(user_id) {R},
    action        VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id   VARCHAR(200) NULL,
    outcome       VARCHAR(20) NOT NULL CONSTRAINT audit_events_outcome_ck CHECK (outcome IN ('SUCCESS','DENIED','FAILED')),
    "timestamp"   TIMESTAMPTZ NOT NULL,
    request_id    VARCHAR(100) NULL,
    metadata      JSONB NULL
);
CREATE INDEX audit_events_ts_ix ON audit_events ("timestamp" DESC);
CREATE INDEX audit_events_user_ts_ix ON audit_events (user_id, "timestamp" DESC);
CREATE INDEX audit_events_resource_ix ON audit_events (resource_type, resource_id);
CREATE INDEX audit_events_request_ix ON audit_events (request_id);
"""

DOWNGRADE = """
DROP TABLE audit_events;
DROP TABLE transactions;
DROP TABLE accounts;
DROP TABLE datasets;
DROP TABLE auth_sessions;
DROP TABLE users;
DROP SCHEMA staging CASCADE;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
