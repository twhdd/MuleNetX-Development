"""Account-level analytical results and communities (SRS §6.3.4, §6.3.5 communities/memberships).

Revision ID: 0003_account_analytics
Revises: 0002_pipeline_lineage
"""

from alembic import op

revision = "0003_account_analytics"
down_revision = "0002_pipeline_lineage"
branch_labels = None
depends_on = None

R = "ON UPDATE RESTRICT ON DELETE RESTRICT"


def _score(col: str, table: str, high: str = "1") -> str:
    return f"CONSTRAINT {table}_{col}_ck CHECK ({col} >= 0 AND {col} <= {high})"


UPGRADE = f"""
CREATE TABLE communities (
    community_id       VARCHAR(64) NOT NULL,
    analytics_run_id   UUID NOT NULL REFERENCES analytics_runs(analytics_run_id) {R},
    graph_snapshot_id  UUID NOT NULL REFERENCES graph_snapshots(graph_snapshot_id) {R},
    algorithm          VARCHAR(100) NOT NULL,
    algorithm_version  VARCHAR(100) NOT NULL,
    member_count       INTEGER NOT NULL CONSTRAINT communities_member_count_ck CHECK (member_count >= 1),
    computed_at        TIMESTAMPTZ NOT NULL,
    analytical_summary JSONB NULL,
    CONSTRAINT communities_pk PRIMARY KEY (analytics_run_id, community_id)
);
CREATE INDEX communities_snapshot_ix ON communities (graph_snapshot_id);

CREATE TABLE community_memberships (
    analytics_run_id UUID NOT NULL REFERENCES analytics_runs(analytics_run_id) {R},
    community_id     VARCHAR(64) NOT NULL,
    account_id       VARCHAR(160) NOT NULL REFERENCES accounts(account_id) {R},
    membership_score NUMERIC(12,8) NULL,
    CONSTRAINT community_memberships_pk PRIMARY KEY (analytics_run_id, community_id, account_id),
    CONSTRAINT community_memberships_community_fk FOREIGN KEY (analytics_run_id, community_id)
        REFERENCES communities(analytics_run_id, community_id) {R}
);
CREATE INDEX community_memberships_account_ix ON community_memberships (account_id, analytics_run_id);

CREATE TABLE account_graph_metrics (
    analytics_run_id UUID NOT NULL REFERENCES analytics_runs(analytics_run_id) {R},
    account_id       VARCHAR(160) NOT NULL REFERENCES accounts(account_id) {R},
    degree           INTEGER NOT NULL CONSTRAINT agm_degree_ck CHECK (degree >= 0),
    in_degree        INTEGER NOT NULL CONSTRAINT agm_in_degree_ck CHECK (in_degree >= 0),
    out_degree       INTEGER NOT NULL CONSTRAINT agm_out_degree_ck CHECK (out_degree >= 0),
    pagerank_raw     DOUBLE PRECISION NOT NULL,
    pagerank_norm    NUMERIC(8,7) NOT NULL {_score("pagerank_norm", "agm")},
    betweenness_raw  DOUBLE PRECISION NOT NULL,
    component_id     VARCHAR(64) NOT NULL,
    component_size   INTEGER NOT NULL CONSTRAINT agm_component_size_ck CHECK (component_size >= 1),
    community_id     VARCHAR(64) NOT NULL,
    community_size   INTEGER NOT NULL CONSTRAINT agm_community_size_ck CHECK (community_size >= 1),
    CONSTRAINT account_graph_metrics_pk PRIMARY KEY (analytics_run_id, account_id),
    CONSTRAINT account_graph_metrics_community_fk FOREIGN KEY (analytics_run_id, community_id)
        REFERENCES communities(analytics_run_id, community_id) {R}
);
CREATE INDEX account_graph_metrics_account_ix ON account_graph_metrics (account_id, analytics_run_id);

CREATE TABLE account_feature_values (
    feature_snapshot_id UUID NOT NULL,
    account_id          VARCHAR(160) NOT NULL REFERENCES accounts(account_id) {R},
    as_of               TIMESTAMPTZ NOT NULL,
    feature_version     VARCHAR(100) NOT NULL REFERENCES feature_versions(feature_version) {R},
    graph_snapshot_id   UUID NOT NULL REFERENCES graph_snapshots(graph_snapshot_id) {R},
    analytics_run_id    UUID NOT NULL REFERENCES analytics_runs(analytics_run_id) {R},
    feature_values      DOUBLE PRECISION[] NOT NULL,
    feature_states      SMALLINT[] NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL,
    CONSTRAINT account_feature_values_pk PRIMARY KEY (feature_snapshot_id, account_id),
    CONSTRAINT afv_lengths_ck CHECK (
        cardinality(feature_values) = cardinality(feature_states) AND cardinality(feature_values) > 0
    ),
    CONSTRAINT afv_states_ck CHECK (feature_states <@ ARRAY[0,1,2,3]::smallint[])
);
CREATE INDEX account_feature_values_account_ix ON account_feature_values (account_id, as_of DESC);

-- graph_snapshot_id must satisfy data_cutoff <= as_of (SRS §6.3.4, §10.4).
CREATE FUNCTION check_feature_snapshot_cutoff() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE cutoff TIMESTAMPTZ;
BEGIN
    SELECT data_cutoff INTO cutoff FROM graph_snapshots WHERE graph_snapshot_id = NEW.graph_snapshot_id;
    IF cutoff IS NOT NULL AND cutoff > NEW.as_of THEN
        RAISE EXCEPTION 'graph snapshot data_cutoff % is after feature cutoff %', cutoff, NEW.as_of
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER account_feature_values_cutoff_tg BEFORE INSERT ON account_feature_values
    FOR EACH ROW EXECUTE FUNCTION check_feature_snapshot_cutoff();

CREATE TABLE risk_assessments (
    assessment_id           UUID PRIMARY KEY,
    scoring_run_id          UUID NOT NULL REFERENCES scoring_runs(scoring_run_id) {R},
    account_id              VARCHAR(160) NOT NULL REFERENCES accounts(account_id) {R},
    as_of                   TIMESTAMPTZ NOT NULL,
    graph_snapshot_id       UUID NOT NULL REFERENCES graph_snapshots(graph_snapshot_id) {R},
    feature_snapshot_id     UUID NOT NULL,
    model_version           VARCHAR(100) NULL REFERENCES model_versions(model_version) {R},
    feature_version         VARCHAR(100) NOT NULL REFERENCES feature_versions(feature_version) {R},
    analytics_version       VARCHAR(100) NOT NULL,
    risk_logic_version      VARCHAR(100) NOT NULL REFERENCES risk_logic_versions(risk_logic_version) {R},
    ml_score                NUMERIC(8,7) NULL {_score("ml_score", "ra")},
    graph_signal_score      NUMERIC(8,7) NOT NULL {_score("graph_signal_score", "ra")},
    behavioral_signal_score NUMERIC(8,7) NOT NULL {_score("behavioral_signal_score", "ra")},
    rule_signal_score       NUMERIC(8,7) NOT NULL {_score("rule_signal_score", "ra")},
    pre_propagation_score   NUMERIC(8,7) NOT NULL {_score("pre_propagation_score", "ra")},
    propagated_risk         NUMERIC(8,7) NOT NULL {_score("propagated_risk", "ra", "0.5")},
    final_score             NUMERIC(8,7) NOT NULL {_score("final_score", "ra")},
    risk_tier               VARCHAR(20) NOT NULL CONSTRAINT ra_risk_tier_ck
                            CHECK (risk_tier IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    signal_availability     JSONB NOT NULL,
    fired_rules             JSONB NOT NULL,
    generated_at            TIMESTAMPTZ NOT NULL,
    CONSTRAINT risk_assessments_run_account_uq UNIQUE (scoring_run_id, account_id),
    CONSTRAINT risk_assessments_features_fk FOREIGN KEY (feature_snapshot_id, account_id)
        REFERENCES account_feature_values(feature_snapshot_id, account_id) {R}
);
CREATE INDEX risk_assessments_account_asof_ix ON risk_assessments (account_id, as_of DESC, generated_at DESC);
CREATE INDEX risk_assessments_run_tier_score_ix ON risk_assessments (scoring_run_id, risk_tier, final_score DESC);
CREATE INDEX risk_assessments_model_ix ON risk_assessments (model_version);

CREATE TABLE propagation_contributions (
    scoring_run_id       UUID NOT NULL REFERENCES scoring_runs(scoring_run_id) {R},
    account_id           VARCHAR(160) NOT NULL REFERENCES accounts(account_id) {R},
    source_account_id    VARCHAR(160) NOT NULL REFERENCES accounts(account_id) {R},
    source_assessment_id UUID NOT NULL REFERENCES risk_assessments(assessment_id) {R},
    distance             SMALLINT NOT NULL CONSTRAINT pc_distance_ck CHECK (distance BETWEEN 1 AND 3),
    source_score         NUMERIC(8,7) NOT NULL,
    decay_value          NUMERIC(8,7) NOT NULL,
    contribution         NUMERIC(8,7) NOT NULL {_score("contribution", "pc", "0.5")},
    rank                 SMALLINT NOT NULL CONSTRAINT pc_rank_ck CHECK (rank >= 1),
    CONSTRAINT propagation_contributions_pk PRIMARY KEY (scoring_run_id, account_id, rank)
);

CREATE TABLE shap_explanations (
    assessment_id   UUID PRIMARY KEY REFERENCES risk_assessments(assessment_id) {R},
    model_version   VARCHAR(100) NOT NULL REFERENCES model_versions(model_version) {R},
    feature_version VARCHAR(100) NOT NULL REFERENCES feature_versions(feature_version) {R},
    explainer       VARCHAR(50) NOT NULL CONSTRAINT shap_explainer_ck
                    CHECK (explainer IN ('tree_shap_interventional','tree_shap_path_dependent')),
    base_value      DOUBLE PRECISION NOT NULL,
    output_space    VARCHAR(20) NOT NULL CONSTRAINT shap_output_space_ck CHECK (output_space IN ('LOG_ODDS','PROBABILITY')),
    contributions   JSONB NOT NULL,
    computed_at     TIMESTAMPTZ NOT NULL
);
"""

DOWNGRADE = """
DROP TABLE shap_explanations;
DROP TABLE propagation_contributions;
DROP TABLE risk_assessments;
DROP TABLE account_feature_values;
DROP FUNCTION check_feature_snapshot_cutoff();
DROP TABLE account_graph_metrics;
DROP TABLE community_memberships;
DROP TABLE communities;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
