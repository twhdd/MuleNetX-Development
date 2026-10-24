"""Rings, temporal motifs and network intervention (SRS §6.3.5, §6.3.6, §6.3.7).

Revision ID: 0004_rings_motifs_interventions
Revises: 0003_account_analytics
"""

from alembic import op

revision = "0004_rings_motifs_interventions"
down_revision = "0003_account_analytics"
branch_labels = None
depends_on = None

R = "ON UPDATE RESTRICT ON DELETE RESTRICT"
TIERS = "('LOW','MEDIUM','HIGH','CRITICAL')"
MOTIF_TYPES = "('RAPID_PASS_THROUGH','FAN_IN','FAN_OUT','CIRCULAR_FLOW','LAYERED_MOVEMENT','BURST_ACTIVITY')"
OPERATIONS = "('ACCOUNT_REMOVAL','INTERMEDIARY_REMOVAL','ACCOUNT_SET_REMOVAL','EDGE_REMOVAL')"


def _unit(col: str, table: str) -> str:
    return f"CONSTRAINT {table}_{col}_ck CHECK ({col} >= 0 AND {col} <= 1)"


def _nonneg(col: str, table: str) -> str:
    return f"CONSTRAINT {table}_{col}_ck CHECK ({col} >= 0)"


UPGRADE = f"""
CREATE TABLE potential_fraud_ring_candidates (
    candidate_id       UUID PRIMARY KEY,
    community_id       VARCHAR(64) NOT NULL,
    analytics_run_id   UUID NOT NULL REFERENCES analytics_runs(analytics_run_id) {R},
    graph_snapshot_id  UUID NOT NULL REFERENCES graph_snapshots(graph_snapshot_id) {R},
    scoring_run_id     UUID NOT NULL REFERENCES scoring_runs(scoring_run_id) {R},
    candidate_score    NUMERIC(8,7) NOT NULL CONSTRAINT pfrc_score_ck CHECK (candidate_score >= 0.5 AND candidate_score <= 1),
    candidate_class    VARCHAR(40) NOT NULL CONSTRAINT pfrc_class_ck
                       CHECK (candidate_class IN ('SUSPICIOUS_COMMUNITY','POTENTIAL_FRAUD_RING_CANDIDATE')),
    signal_summary     JSONB NOT NULL,
    candidate_status   VARCHAR(20) NOT NULL CONSTRAINT pfrc_status_ck
                       CHECK (candidate_status IN ('CANDIDATE','REVIEWED','DISMISSED')),
    status_changed_by  UUID NULL REFERENCES users(user_id) {R},
    status_changed_at  TIMESTAMPTZ NULL,
    analytics_version  VARCHAR(100) NOT NULL,
    risk_logic_version VARCHAR(100) NOT NULL REFERENCES risk_logic_versions(risk_logic_version) {R},
    created_at         TIMESTAMPTZ NOT NULL,
    CONSTRAINT pfrc_community_fk FOREIGN KEY (analytics_run_id, community_id)
        REFERENCES communities(analytics_run_id, community_id) {R},
    CONSTRAINT pfrc_run_community_uq UNIQUE (scoring_run_id, analytics_run_id, community_id)
);
CREATE INDEX pfrc_run_class_score_ix ON potential_fraud_ring_candidates (scoring_run_id, candidate_class, candidate_score DESC);
CREATE INDEX pfrc_analytics_community_ix ON potential_fraud_ring_candidates (analytics_run_id, community_id);
CREATE INDEX pfrc_status_ix ON potential_fraud_ring_candidates (candidate_status);

CREATE TABLE ring_memberships (
    ring_id    UUID NOT NULL REFERENCES potential_fraud_ring_candidates(candidate_id) {R},
    account_id VARCHAR(160) NOT NULL REFERENCES accounts(account_id) {R},
    CONSTRAINT ring_memberships_pk PRIMARY KEY (ring_id, account_id)
);
CREATE INDEX ring_memberships_account_ix ON ring_memberships (account_id);

CREATE TABLE ring_feature_sets (
    ring_feature_set_id            UUID PRIMARY KEY,
    ring_id                        UUID NOT NULL REFERENCES potential_fraud_ring_candidates(candidate_id) {R},
    analytics_run_id               UUID NOT NULL REFERENCES analytics_runs(analytics_run_id) {R},
    community_id                   VARCHAR(64) NOT NULL,
    graph_snapshot_id              UUID NOT NULL REFERENCES graph_snapshots(graph_snapshot_id) {R},
    scoring_run_id                 UUID NOT NULL REFERENCES scoring_runs(scoring_run_id) {R},
    analytics_version              VARCHAR(100) NOT NULL,
    feature_version                VARCHAR(100) NOT NULL,
    ring_size                      INTEGER NOT NULL CONSTRAINT rfs_ring_size_ck CHECK (ring_size >= 1),
    transaction_count              INTEGER NOT NULL {_nonneg("transaction_count", "rfs")},
    start_time                     TIMESTAMPTZ NULL,
    end_time                       TIMESTAMPTZ NULL,
    temporal_span_seconds          BIGINT NOT NULL {_nonneg("temporal_span_seconds", "rfs")},
    suspicious_transaction_density NUMERIC(8,7) NOT NULL {_unit("suspicious_transaction_density", "rfs")},
    risk_concentration             NUMERIC(8,7) NOT NULL {_unit("risk_concentration", "rfs")},
    temporal_coordination          NUMERIC(8,7) NOT NULL {_unit("temporal_coordination", "rfs")},
    money_flow_concentration       NUMERIC(8,7) NOT NULL {_unit("money_flow_concentration", "rfs")},
    centrality_signal              NUMERIC(8,7) NOT NULL {_unit("centrality_signal", "rfs")},
    fan_in_signal                  NUMERIC(8,7) NOT NULL {_unit("fan_in_signal", "rfs")},
    fan_out_signal                 NUMERIC(8,7) NOT NULL {_unit("fan_out_signal", "rfs")},
    cycle_presence                 NUMERIC(8,7) NOT NULL CONSTRAINT rfs_cycle_presence_ck CHECK (cycle_presence IN (0, 1)),
    suspicious_path_density        NUMERIC(8,7) NOT NULL {_unit("suspicious_path_density", "rfs")},
    eligible_path_count            INTEGER NOT NULL {_nonneg("eligible_path_count", "rfs")},
    qualifying_path_count          INTEGER NOT NULL {_nonneg("qualifying_path_count", "rfs")},
    paths_truncated                BOOLEAN NOT NULL,
    availability                   JSONB NOT NULL,
    computed_at                    TIMESTAMPTZ NOT NULL,
    CONSTRAINT rfs_community_fk FOREIGN KEY (analytics_run_id, community_id)
        REFERENCES communities(analytics_run_id, community_id) {R},
    CONSTRAINT rfs_times_ck CHECK ((transaction_count = 0) = (start_time IS NULL AND end_time IS NULL))
);
CREATE INDEX rfs_ring_computed_ix ON ring_feature_sets (ring_id, computed_at DESC);
CREATE INDEX rfs_scoring_run_ix ON ring_feature_sets (scoring_run_id);

CREATE TABLE ring_risk_assessments (
    ring_risk_assessment_id UUID PRIMARY KEY,
    ring_id                 UUID NOT NULL REFERENCES potential_fraud_ring_candidates(candidate_id) {R},
    feature_set_id          UUID NOT NULL REFERENCES ring_feature_sets(ring_feature_set_id) {R},
    scoring_run_id          UUID NOT NULL REFERENCES scoring_runs(scoring_run_id) {R},
    member_risk             NUMERIC(8,7) NOT NULL {_unit("member_risk", "rra")},
    transaction_risk        NUMERIC(8,7) NOT NULL {_unit("transaction_risk", "rra")},
    topology_signal         NUMERIC(8,7) NOT NULL {_unit("topology_signal", "rra")},
    temporal_signal         NUMERIC(8,7) NOT NULL {_unit("temporal_signal", "rra")},
    money_flow_signal       NUMERIC(8,7) NOT NULL {_unit("money_flow_signal", "rra")},
    ring_risk_score         NUMERIC(8,7) NOT NULL {_unit("ring_risk_score", "rra")},
    risk_tier               VARCHAR(20) NOT NULL CONSTRAINT rra_risk_tier_ck CHECK (risk_tier IN {TIERS}),
    availability            JSONB NOT NULL,
    risk_logic_version      VARCHAR(100) NOT NULL REFERENCES risk_logic_versions(risk_logic_version) {R},
    analytics_version       VARCHAR(100) NOT NULL,
    feature_version         VARCHAR(100) NOT NULL,
    generated_at            TIMESTAMPTZ NOT NULL
);
CREATE INDEX rra_ring_generated_ix ON ring_risk_assessments (ring_id, generated_at DESC);
CREATE INDEX rra_run_tier_ix ON ring_risk_assessments (scoring_run_id, risk_tier);

CREATE TABLE temporal_motifs (
    motif_id                      UUID PRIMARY KEY,
    analytics_run_id              UUID NOT NULL REFERENCES analytics_runs(analytics_run_id) {R},
    graph_snapshot_id             UUID NOT NULL REFERENCES graph_snapshots(graph_snapshot_id) {R},
    motif_type                    VARCHAR(40) NOT NULL CONSTRAINT tm_type_ck CHECK (motif_type IN {MOTIF_TYPES}),
    anchor_account_id             VARCHAR(160) NOT NULL REFERENCES accounts(account_id) {R},
    start_time                    TIMESTAMPTZ NOT NULL,
    end_time                      TIMESTAMPTZ NOT NULL,
    temporal_window_seconds       INTEGER NOT NULL CONSTRAINT tm_window_ck CHECK (temporal_window_seconds > 0),
    participating_account_ids     JSONB NOT NULL,
    participating_transaction_ids JSONB NOT NULL,
    transaction_count             INTEGER NOT NULL CONSTRAINT tm_tx_count_ck CHECK (transaction_count > 0),
    motif_confidence              NUMERIC(8,7) NOT NULL {_unit("motif_confidence", "tm")},
    order_ambiguous               BOOLEAN NOT NULL,
    evidence                      JSONB NOT NULL,
    analytics_version             VARCHAR(100) NOT NULL,
    computed_at                   TIMESTAMPTZ NOT NULL
);
CREATE INDEX tm_run_type_start_ix ON temporal_motifs (analytics_run_id, motif_type, start_time);
CREATE INDEX tm_anchor_start_ix ON temporal_motifs (anchor_account_id, start_time);
CREATE INDEX tm_participants_gin_ix ON temporal_motifs USING GIN (participating_account_ids jsonb_path_ops);

CREATE TABLE intervention_scenarios (
    scenario_id                         UUID PRIMARY KEY,
    mode                                VARCHAR(10) NOT NULL CONSTRAINT is_mode_ck CHECK (mode IN ('RANK','EVALUATE')),
    target_ring_id                      UUID NOT NULL REFERENCES potential_fraud_ring_candidates(candidate_id) {R},
    baseline_graph_snapshot_id          UUID NOT NULL REFERENCES graph_snapshots(graph_snapshot_id) {R},
    scoring_run_id                      UUID NOT NULL REFERENCES scoring_runs(scoring_run_id) {R},
    intervention_type                   VARCHAR(40) NULL CONSTRAINT is_type_ck CHECK (intervention_type IN {OPERATIONS}),
    target_ids                          JSONB NULL,
    baseline_suspicious_flow            NUMERIC(20,4) NULL {_nonneg("baseline_suspicious_flow", "is")},
    baseline_suspicious_paths           INTEGER NULL {_nonneg("baseline_suspicious_paths", "is")},
    baseline_reachable_suspicious_pairs INTEGER NULL {_nonneg("baseline_reachable_suspicious_pairs", "is")},
    baseline_risk_mass                  NUMERIC(20,7) NULL {_nonneg("baseline_risk_mass", "is")},
    baseline_paths_truncated            BOOLEAN NULL,
    eligible_candidate_ids              JSONB NULL,
    ranking_configuration               JSONB NOT NULL,
    ranking_configuration_hash          CHAR(64) NOT NULL,
    analytics_version                   VARCHAR(100) NOT NULL,
    risk_logic_version                  VARCHAR(100) NOT NULL REFERENCES risk_logic_versions(risk_logic_version) {R},
    requested_by                        UUID NOT NULL REFERENCES users(user_id) {R},
    job_id                              UUID NULL REFERENCES jobs(job_id) {R},
    status                              VARCHAR(20) NOT NULL CONSTRAINT is_status_ck
                                        CHECK (status IN ('QUEUED','RUNNING','COMPLETED','FAILED')),
    error_summary                       TEXT NULL,
    created_at                          TIMESTAMPTZ NOT NULL,
    completed_at                        TIMESTAMPTZ NULL
);
CREATE INDEX is_ring_created_ix ON intervention_scenarios (target_ring_id, created_at DESC);
CREATE INDEX is_status_ix ON intervention_scenarios (status);

CREATE TABLE intervention_candidates (
    candidate_id                        UUID NOT NULL,
    scenario_id                         UUID NOT NULL REFERENCES intervention_scenarios(scenario_id) {R},
    operation_type                      VARCHAR(40) NOT NULL CONSTRAINT ic_type_ck CHECK (operation_type IN {OPERATIONS}),
    target_ids                          JSONB NOT NULL,
    residual_suspicious_flow            NUMERIC(20,4) NOT NULL {_nonneg("residual_suspicious_flow", "ic")},
    flow_disruption                     NUMERIC(20,4) NOT NULL {_nonneg("flow_disruption", "ic")},
    flow_disruption_percentage          NUMERIC(8,7) NOT NULL {_unit("flow_disruption_percentage", "ic")},
    residual_suspicious_paths           INTEGER NOT NULL {_nonneg("residual_suspicious_paths", "ic")},
    normalized_path_disruption          NUMERIC(8,7) NOT NULL {_unit("normalized_path_disruption", "ic")},
    residual_reachable_suspicious_pairs INTEGER NOT NULL {_nonneg("residual_reachable_suspicious_pairs", "ic")},
    normalized_connectivity_disruption  NUMERIC(8,7) NOT NULL {_unit("normalized_connectivity_disruption", "ic")},
    residual_risk_mass                  NUMERIC(20,7) NOT NULL {_nonneg("residual_risk_mass", "ic")},
    residual_network_risk               NUMERIC(8,7) NOT NULL {_unit("residual_network_risk", "ic")},
    normalized_risk_reduction           NUMERIC(8,7) NOT NULL {_unit("normalized_risk_reduction", "ic")},
    intervention_cost                   NUMERIC(12,4) NOT NULL {_nonneg("intervention_cost", "ic")},
    normalized_intervention_cost        NUMERIC(8,7) NOT NULL {_unit("normalized_intervention_cost", "ic")},
    intervention_score                  NUMERIC(8,7) NOT NULL {_unit("intervention_score", "ic")},
    rank_position                       INTEGER NOT NULL CONSTRAINT ic_rank_ck CHECK (rank_position > 0),
    affected_account_ids                JSONB NOT NULL,
    affected_path_ids                   JSONB NOT NULL,
    alternative_path_ids                JSONB NOT NULL,
    unavailable_metrics                 JSONB NOT NULL,
    evidence                            JSONB NOT NULL,
    created_at                          TIMESTAMPTZ NOT NULL,
    CONSTRAINT intervention_candidates_pk PRIMARY KEY (scenario_id, candidate_id),
    CONSTRAINT ic_scenario_rank_uq UNIQUE (scenario_id, rank_position)
);
"""

DOWNGRADE = """
DROP TABLE intervention_candidates;
DROP TABLE intervention_scenarios;
DROP TABLE temporal_motifs;
DROP TABLE ring_risk_assessments;
DROP TABLE ring_feature_sets;
DROP TABLE ring_memberships;
DROP TABLE potential_fraud_ring_candidates;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
