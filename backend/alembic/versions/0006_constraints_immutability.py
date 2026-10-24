"""Constraints and immutability enforcement (SRS §6.5, §6.7).

1. `accounts.latest_risk_assessment_id` FK (the cyclic reference, added after `risk_assessments`).
2. The app role loses UPDATE/DELETE on the twelve append-only tables of §6.5(1).
3. One `BEFORE UPDATE` trigger function rejects changes to columns marked "Imm." in §6.3; columns marked
   once ("Once", "Set once", "Yes, once") may change only from NULL. Column lists below were generated
   from SRS §6.3 by `scripts/schema_check.py:parse_srs` and are frozen here.
4. SECURITY DEFINER purge functions let a stage retry delete its own partial outputs from append-only
   tables (§7.7) only while the owning run has not succeeded (OQ-11).

Revision ID: 0006_constraints_immutability
Revises: 0005_investigation_evaluation
"""

from alembic import op

revision = "0006_constraints_immutability"
down_revision = "0005_investigation_evaluation"
branch_labels = None
depends_on = None

APPEND_ONLY = (
    "findings", "audit_events", "transactions", "risk_assessments", "account_feature_values",
    "shap_explanations", "propagation_contributions", "ring_feature_sets", "ring_risk_assessments",
    "temporal_motifs", "intervention_candidates", "evaluation_metrics",
)

IMMUTABLE_COLUMNS = {'account_feature_values': ['feature_snapshot_id', 'account_id', 'as_of', 'feature_version',
                            'graph_snapshot_id', 'analytics_run_id', 'feature_values', 'feature_states',
                            'created_at'],
 'account_graph_metrics': ['analytics_run_id', 'account_id', 'degree', 'in_degree', 'out_degree',
                           'pagerank_raw', 'pagerank_norm', 'betweenness_raw', 'component_id',
                           'component_size', 'community_id', 'community_size'],
 'accounts': ['account_id', 'dataset_id', 'source_account_ref', 'account_type', 'created_at'],
 'active_context': ['singleton'],
 'analytics_runs': ['analytics_run_id', 'graph_snapshot_id', 'analytics_version', 'engine',
                    'algorithm_configuration', 'started_at'],
 'audit_events': ['event_id', 'user_id', 'action', 'resource_type', 'resource_id', 'outcome', 'timestamp',
                  'request_id', 'metadata'],
 'auth_sessions': ['session_id', 'token_hash', 'user_id', 'role_at_issue', 'created_at',
                   'absolute_expires_at'],
 'case_subjects': ['case_id', 'subject_type', 'subject_id', 'added_by', 'added_at'],
 'cases': ['case_id', 'created_by', 'created_at'],
 'communities': ['community_id', 'analytics_run_id', 'graph_snapshot_id', 'algorithm', 'algorithm_version',
                 'member_count', 'computed_at', 'analytical_summary'],
 'community_memberships': ['analytics_run_id', 'community_id', 'account_id', 'membership_score'],
 'dataset_profiles': ['dataset_id', 'profile_version', 'metrics', 'created_at'],
 'datasets': ['dataset_id', 'dataset_key', 'name', 'source', 'dataset_version', 'schema_version', 'adapter',
              'adapter_config', 'checksum', 'timestamp_resolution_seconds', 'is_synthetic_injection',
              'created_at'],
 'evaluation_metrics': ['evaluation_run_id', 'level', 'metric', 'value', 'sample_count', 'availability',
                        'details'],
 'evaluation_runs': ['evaluation_run_id', 'dataset_id', 'model_version', 'test_snapshot_id', 'scoring_run_id',
                     'analytics_version', 'risk_logic_version', 'reference_construction_version',
                     'configuration', 'created_at'],
 'feature_versions': ['feature_version', 'definition_hash', 'feature_count', 'feature_registry_reference',
                      'created_at'],
 'findings': ['finding_id', 'case_id', 'type', 'description', 'evidence', 'source', 'created_by',
              'created_at'],
 'graph_snapshots': ['graph_snapshot_id', 'dataset_id', 'ingestion_run_id', 'purpose', 'data_cutoff',
                     'pipeline_version', 'graph_schema_version', 'source_record_count', 'created_at'],
 'ingestion_runs': ['ingestion_run_id', 'dataset_id', 'pipeline_version', 'started_at'],
 'intervention_candidates': ['candidate_id', 'scenario_id', 'operation_type', 'target_ids',
                             'residual_suspicious_flow', 'flow_disruption', 'flow_disruption_percentage',
                             'residual_suspicious_paths', 'normalized_path_disruption',
                             'residual_reachable_suspicious_pairs', 'normalized_connectivity_disruption',
                             'residual_risk_mass', 'residual_network_risk', 'normalized_risk_reduction',
                             'intervention_cost', 'normalized_intervention_cost', 'intervention_score',
                             'rank_position', 'affected_account_ids', 'affected_path_ids',
                             'alternative_path_ids', 'unavailable_metrics', 'evidence', 'created_at'],
 'intervention_scenarios': ['scenario_id', 'mode', 'target_ring_id', 'baseline_graph_snapshot_id',
                            'scoring_run_id', 'intervention_type', 'target_ids', 'ranking_configuration',
                            'ranking_configuration_hash', 'analytics_version', 'risk_logic_version',
                            'requested_by', 'job_id', 'created_at'],
 'jobs': ['job_id', 'kind', 'payload', 'lock_key', 'max_attempts', 'requested_by', 'request_id',
          'created_at'],
 'model_versions': ['model_version', 'model_type', 'target_definition', 'feature_version', 'feature_regime',
                    'training_dataset_id', 'training_snapshot_ids', 'split_boundaries', 'training_config',
                    'class_distribution', 'evaluation_metrics', 'operating_threshold', 'artifact_reference',
                    'artifact_sha256', 'implementation_version', 'random_seed', 'created_at'],
 'pipeline_runs': ['pipeline_run_id', 'dataset_id', 'started_at'],
 'potential_fraud_ring_candidates': ['candidate_id', 'community_id', 'analytics_run_id', 'graph_snapshot_id',
                                     'scoring_run_id', 'candidate_score', 'candidate_class', 'signal_summary',
                                     'analytics_version', 'risk_logic_version', 'created_at'],
 'propagation_contributions': ['scoring_run_id', 'account_id', 'source_account_id', 'source_assessment_id',
                               'distance', 'source_score', 'decay_value', 'contribution', 'rank'],
 'ring_feature_sets': ['ring_feature_set_id', 'ring_id', 'analytics_run_id', 'community_id',
                       'graph_snapshot_id', 'scoring_run_id', 'analytics_version', 'feature_version',
                       'ring_size', 'transaction_count', 'start_time', 'end_time', 'temporal_span_seconds',
                       'suspicious_transaction_density', 'risk_concentration', 'temporal_coordination',
                       'money_flow_concentration', 'centrality_signal', 'fan_in_signal', 'fan_out_signal',
                       'cycle_presence', 'suspicious_path_density', 'eligible_path_count',
                       'qualifying_path_count', 'paths_truncated', 'availability', 'computed_at'],
 'ring_memberships': ['ring_id', 'account_id'],
 'ring_risk_assessments': ['ring_risk_assessment_id', 'ring_id', 'feature_set_id', 'scoring_run_id',
                           'member_risk', 'transaction_risk', 'topology_signal', 'temporal_signal',
                           'money_flow_signal', 'ring_risk_score', 'risk_tier', 'availability',
                           'risk_logic_version', 'analytics_version', 'feature_version', 'generated_at'],
 'risk_assessments': ['assessment_id', 'scoring_run_id', 'account_id', 'as_of', 'graph_snapshot_id',
                      'feature_snapshot_id', 'model_version', 'feature_version', 'analytics_version',
                      'risk_logic_version', 'ml_score', 'graph_signal_score', 'behavioral_signal_score',
                      'rule_signal_score', 'pre_propagation_score', 'propagated_risk', 'final_score',
                      'risk_tier', 'signal_availability', 'fired_rules', 'generated_at'],
 'risk_logic_versions': ['risk_logic_version', 'formula_identifier', 'configuration',
                         'normalization_reference', 'rules', 'tier_thresholds', 'propagation_parameters',
                         'ring_parameters', 'created_at'],
 'scoring_runs': ['scoring_run_id', 'graph_snapshot_id', 'analytics_run_id', 'as_of', 'feature_version',
                  'feature_snapshot_id', 'model_version', 'risk_logic_version', 'started_at'],
 'shap_explanations': ['assessment_id', 'model_version', 'feature_version', 'explainer', 'base_value',
                       'output_space', 'contributions', 'computed_at'],
 'temporal_motifs': ['motif_id', 'analytics_run_id', 'graph_snapshot_id', 'motif_type', 'anchor_account_id',
                     'start_time', 'end_time', 'temporal_window_seconds', 'participating_account_ids',
                     'participating_transaction_ids', 'transaction_count', 'motif_confidence',
                     'order_ambiguous', 'evidence', 'analytics_version', 'computed_at'],
 'transactions': ['transaction_id', 'dataset_id', 'ingestion_run_id', 'source_transaction_ref',
                  'source_account_id', 'destination_account_id', 'amount', 'timestamp', 'transaction_type',
                  'fraud_label', 'source_record_hash'],
 'users': ['user_id', 'username', 'created_at']}

ONCE_COLUMNS = {'analytics_runs': ['completed_at'],
 'auth_sessions': ['revoked_at', 'revocation_reason'],
 'case_subjects': ['removed_by', 'removed_at'],
 'cases': ['closed_at'],
 'datasets': ['record_count'],
 'evaluation_runs': ['completed_at'],
 'graph_snapshots': ['node_count', 'edge_count', 'validation_digest', 'ready_at'],
 'ingestion_runs': ['completed_at'],
 'intervention_scenarios': ['baseline_suspicious_flow', 'baseline_suspicious_paths',
                            'baseline_reachable_suspicious_pairs', 'baseline_risk_mass',
                            'baseline_paths_truncated', 'eligible_candidate_ids', 'completed_at'],
 'jobs': ['completed_at'],
 'pipeline_runs': ['ingestion_run_id', 'graph_snapshot_id', 'analytics_run_id', 'scoring_run_id',
                   'model_version', 'completed_at'],
 'scoring_runs': ['completed_at', 'accounts_scored']}

TRIGGER_FUNCTION = """
CREATE FUNCTION reject_immutable_update() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    col TEXT;
    once_mode BOOLEAN := FALSE;
    old_row JSONB := to_jsonb(OLD);
    new_row JSONB := to_jsonb(NEW);
BEGIN
    FOREACH col IN ARRAY TG_ARGV LOOP
        IF col = '--once' THEN
            once_mode := TRUE;
            CONTINUE;
        END IF;
        IF (old_row -> col) IS DISTINCT FROM (new_row -> col) THEN
            IF once_mode AND (old_row -> col) = 'null'::jsonb THEN
                CONTINUE;
            END IF;
            RAISE EXCEPTION 'column %.% is immutable', TG_TABLE_NAME, col USING ERRCODE = 'integrity_constraint_violation';
        END IF;
    END LOOP;
    RETURN NEW;
END $$;
"""

PURGE_FUNCTIONS = """
CREATE FUNCTION purge_analytics_outputs(p_run UUID) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM analytics_runs WHERE analytics_run_id = p_run AND status = 'SUCCEEDED') THEN
        RAISE EXCEPTION 'analytics run % succeeded; its outputs are immutable', p_run;
    END IF;
    DELETE FROM temporal_motifs WHERE analytics_run_id = p_run;
    DELETE FROM account_graph_metrics WHERE analytics_run_id = p_run;
    DELETE FROM community_memberships WHERE analytics_run_id = p_run;
    DELETE FROM communities WHERE analytics_run_id = p_run;
END $$;

CREATE FUNCTION purge_feature_snapshot(p_snapshot UUID) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM scoring_runs WHERE feature_snapshot_id = p_snapshot AND status = 'SUCCEEDED') THEN
        RAISE EXCEPTION 'feature snapshot % belongs to a succeeded scoring run', p_snapshot;
    END IF;
    DELETE FROM account_feature_values WHERE feature_snapshot_id = p_snapshot;
END $$;

CREATE FUNCTION purge_scoring_outputs(p_run UUID) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM scoring_runs WHERE scoring_run_id = p_run AND status = 'SUCCEEDED') THEN
        RAISE EXCEPTION 'scoring run % succeeded; its outputs are immutable', p_run;
    END IF;
    DELETE FROM shap_explanations WHERE assessment_id IN
        (SELECT assessment_id FROM risk_assessments WHERE scoring_run_id = p_run);
    DELETE FROM propagation_contributions WHERE scoring_run_id = p_run;
    DELETE FROM risk_assessments WHERE scoring_run_id = p_run;
END $$;

CREATE FUNCTION purge_ring_outputs(p_scoring_run UUID) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM active_context WHERE scoring_run_id = p_scoring_run)
       OR EXISTS (SELECT 1 FROM pipeline_runs WHERE scoring_run_id = p_scoring_run AND current_state = 'READY') THEN
        RAISE EXCEPTION 'ring outputs of scoring run % are published and immutable', p_scoring_run;
    END IF;
    DELETE FROM ring_risk_assessments WHERE scoring_run_id = p_scoring_run;
    DELETE FROM ring_feature_sets WHERE scoring_run_id = p_scoring_run;
    DELETE FROM ring_memberships WHERE ring_id IN
        (SELECT candidate_id FROM potential_fraud_ring_candidates WHERE scoring_run_id = p_scoring_run);
    DELETE FROM potential_fraud_ring_candidates WHERE scoring_run_id = p_scoring_run;
END $$;

CREATE FUNCTION purge_intervention_scenario(p_scenario UUID) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM intervention_scenarios WHERE scenario_id = p_scenario AND status = 'COMPLETED') THEN
        RAISE EXCEPTION 'scenario % completed; its results are immutable', p_scenario;
    END IF;
    DELETE FROM intervention_candidates WHERE scenario_id = p_scenario;
END $$;

CREATE FUNCTION purge_evaluation_run(p_run UUID) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM evaluation_runs WHERE evaluation_run_id = p_run AND status = 'COMPLETED') THEN
        RAISE EXCEPTION 'evaluation run % completed; its results are immutable', p_run;
    END IF;
    DELETE FROM evaluation_metrics WHERE evaluation_run_id = p_run;
END $$;
"""

PURGE_NAMES = (
    "purge_analytics_outputs", "purge_feature_snapshot", "purge_scoring_outputs", "purge_ring_outputs",
    "purge_intervention_scenario", "purge_evaluation_run",
)


def _trigger_sql(table: str) -> str:
    args = list(IMMUTABLE_COLUMNS[table])
    once = ONCE_COLUMNS.get(table, [])
    if once:
        args += ["--once", *once]
    quoted = ", ".join(f"'{a}'" for a in args)
    return (
        f"CREATE TRIGGER {table}_immutable_tg BEFORE UPDATE ON {table} "
        f"FOR EACH ROW EXECUTE FUNCTION reject_immutable_update({quoted});"
    )


def upgrade() -> None:
    op.execute(
        "ALTER TABLE accounts ADD CONSTRAINT accounts_latest_assessment_fk FOREIGN KEY (latest_risk_assessment_id) "
        "REFERENCES risk_assessments(assessment_id) ON UPDATE RESTRICT ON DELETE RESTRICT"
    )
    for table in APPEND_ONLY:
        op.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON {table} FROM mulenetx_app")
    op.execute(TRIGGER_FUNCTION)
    for table in sorted(IMMUTABLE_COLUMNS):
        op.execute(_trigger_sql(table))
    op.execute(PURGE_FUNCTIONS)
    for name in PURGE_NAMES:
        op.execute(f"REVOKE ALL ON FUNCTION {name}(UUID) FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {name}(UUID) TO mulenetx_app")


def downgrade() -> None:
    for name in PURGE_NAMES:
        op.execute(f"DROP FUNCTION {name}(UUID)")
    for table in sorted(IMMUTABLE_COLUMNS):
        op.execute(f"DROP TRIGGER {table}_immutable_tg ON {table}")
    op.execute("DROP FUNCTION reject_immutable_update()")
    for table in APPEND_ONLY:
        op.execute(f"GRANT UPDATE, DELETE ON {table} TO mulenetx_app")
    op.execute("ALTER TABLE accounts DROP CONSTRAINT accounts_latest_assessment_fk")
