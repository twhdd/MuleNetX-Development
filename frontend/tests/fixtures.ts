/** API fixtures shaped by the generated OpenAPI types, modelled on the abc_chain backend fixture (A → B → C). */
import type { Account, Assessment, Case, Context, Features, Lineage, Neighborhood, PathQuery, PipelineRun, Shap, TransactionPage } from "../src/api/types";

export const lineage: Lineage = {
  graph_snapshot_id: "11111111-1111-5111-8111-111111111111",
  analytics_run_id: "22222222-2222-4222-8222-222222222222",
  scoring_run_id: "33333333-3333-4333-8333-333333333333",
  model_version: "xgb-20261018T031428-a4879723-d99a68",
  risk_logic_version: "rl-1",
};

export const context: Context = {
  dataset_id: "44444444-4444-4444-8444-444444444444",
  graph_snapshot_id: lineage.graph_snapshot_id,
  analytics_run_id: lineage.analytics_run_id,
  scoring_run_id: lineage.scoring_run_id,
  model_version: lineage.model_version,
  risk_logic_version: lineage.risk_logic_version,
  updated_at: "2026-10-18T03:34:08Z",
  updated_by_pipeline_run_id: "55555555-5555-4555-8555-555555555555",
  is_active: true,
  is_synthetic_injection: false,
};

export function account(ref: string, score: number | null, tier: string | null, extra: Partial<Account> = {}): Account {
  return {
    account_id: `abc:${ref}`,
    source_account_ref: ref,
    dataset_id: context.dataset_id!,
    dataset_key: "abc",
    account_type: "CUSTOMER",
    created_at: null,
    risk_score: score,
    risk_tier: tier,
    community_id: "c0ffee00-0000-5000-8000-000000000001",
    latest_risk_assessment_id: "66666666-6666-4666-8666-666666666666",
    lineage,
    computed_at: null,
    is_stale: false,
    ...extra,
  };
}

export const accounts: Account[] = [account("B", 0.81, "CRITICAL"), account("A", 0.52, "MEDIUM"), account("C", 0.31, "LOW")];

export function assessment(id: string, extra: Partial<Assessment> = {}): Assessment {
  return {
    assessment_id: "66666666-6666-4666-8666-666666666666",
    account_id: id,
    scoring_run_id: lineage.scoring_run_id!,
    as_of: "2020-01-01T02:00:00Z",
    ml_score: 0.9123456,
    graph_signal_score: 0.71,
    behavioral_signal_score: 0.44,
    rule_signal_score: 0.8,
    pre_propagation_score: 0.7654321,
    propagated_risk: 0.12,
    final_score: 0.8123456,
    risk_tier: "CRITICAL",
    signal_availability: {
      ml: { state: "AVAILABLE", reason: null },
      graph: { state: "AVAILABLE", inputs: {} },
      behavioral: { state: "AVAILABLE", inputs: {} },
      rules: { state: "AVAILABLE" },
      propagation: { state: "AVAILABLE" },
    },
    signal_coverage: 1,
    max_attainable_score: 0.8123456,
    fired_rules: [{ rule_id: "R01", name: "rapid pass-through" }],
    model_version: lineage.model_version,
    feature_version: "v1",
    analytics_version: "nx-3.7-b2eb8ba41f53",
    risk_logic_version: "rl-1",
    generated_at: "2026-10-18T03:34:07Z",
    interpretation: "Analytical risk score; not a determination of fraud, mule status or criminality.",
    lineage,
    computed_at: "2026-10-18T03:34:07Z",
    is_stale: false,
    ...extra,
  };
}

export const shap: Shap = {
  assessment_id: "66666666-6666-4666-8666-666666666666",
  account_id: "abc:B",
  model_version: lineage.model_version!,
  feature_version: "v1",
  explainer: "tree_shap_path_dependent",
  output_space: "LOG_ODDS",
  base_value: -1.2,
  ml_score: 0.9123456,
  explains: "ML_COMPONENT_ONLY",
  statement: "This explanation covers the ML component (ml_score) only.",
  top_n: 2,
  contributions: [
    { feature_id: "F06", name: "mean_transaction_amount", value: 95, state: "OBSERVED", shap: 2.77, relative_importance: 0.7, direction: "INCREASES" },
    { feature_id: "F08", name: "amount_stddev", value: 5, state: "OBSERVED", shap: -0.4, relative_importance: 0.3, direction: "DECREASES" },
  ],
  feature_count: 42,
  lineage,
  computed_at: "2026-10-18T03:35:00Z",
  is_stale: false,
};

export const features: Features = {
  account_id: "abc:B",
  feature_snapshot_id: "77777777-7777-5777-8777-777777777777",
  feature_version: "v1",
  as_of: "2020-01-01T02:00:00Z",
  features: [
    { feature_id: "F01", name: "transaction_count", value: 2, state: "OBSERVED", window: "all", unit: "count", description: "Transactions touching the account." },
    { feature_id: "F19", name: "neighbor_risk_mean", value: null, state: "UNAVAILABLE", window: null, unit: null, description: "Risk-derived feature." },
    { feature_id: "F27", name: "dormancy_to_activity", value: 0, state: "ZERO", window: "30d", unit: "ratio", description: "Dormancy." },
  ],
  lineage,
  computed_at: "2026-10-18T03:34:00Z",
  is_stale: false,
};

export const transactions: TransactionPage = {
  items: [
    { transaction_id: "abc:0000000002", source_transaction_ref: "2", dataset_id: context.dataset_id!, source_account_id: "abc:B", destination_account_id: "abc:C", amount: "90.000000", timestamp: "2020-01-01T02:00:00Z", transaction_type: "CASH_OUT", fraud_label: true, direction: "out" },
    { transaction_id: "abc:0000000001", source_transaction_ref: "1", dataset_id: context.dataset_id!, source_account_id: "abc:A", destination_account_id: "abc:B", amount: "100.000000", timestamp: "2020-01-01T01:00:00Z", transaction_type: "TRANSFER", fraud_label: false, direction: "in" },
  ],
  next_cursor: null,
  range: { start: "2019-12-01T02:00:00Z", end: "2020-01-01T02:00:00Z" },
};

export const neighborhood: Neighborhood = {
  account_id: "abc:B",
  graph_snapshot_id: lineage.graph_snapshot_id!,
  depth: 2,
  nodes: [
    { account_id: "abc:B", source_account_ref: "B", account_type: "CUSTOMER", risk_score: 0.81, risk_tier: "CRITICAL", community_id: "c1", hop: 0 },
    { account_id: "abc:A", source_account_ref: "A", account_type: "CUSTOMER", risk_score: 0.52, risk_tier: "MEDIUM", community_id: "c1", hop: 1 },
    { account_id: "abc:C", source_account_ref: "C", account_type: "CUSTOMER", risk_score: 0.31, risk_tier: "LOW", community_id: "c1", hop: 1 },
  ],
  edges: [
    { source_account_id: "abc:A", destination_account_id: "abc:B", tx_count: 1, total_amount: "100.000000", first_ts: "2020-01-01T01:00:00Z", last_ts: "2020-01-01T01:00:00Z" },
    { source_account_id: "abc:B", destination_account_id: "abc:C", tx_count: 1, total_amount: "90.000000", first_ts: "2020-01-01T02:00:00Z", last_ts: "2020-01-01T02:00:00Z" },
  ],
  truncated: false,
  applied_limits: { depth: 2, max_nodes: 100, max_edges: 500, query_timeout_seconds: 5 },
  lineage: { ...lineage, analytics_run_id: null, scoring_run_id: null, model_version: null, risk_logic_version: null },
  computed_at: "2026-10-18T03:36:00Z",
  is_stale: false,
};

export const pathQuery: PathQuery = {
  source_account_id: "abc:A",
  destination_account_id: "abc:C",
  mode: "SHORTEST",
  graph_snapshot_id: lineage.graph_snapshot_id!,
  algorithm_version: "paths-v1",
  paths: [
    {
      path_id: "88888888-8888-5888-8888-888888888888",
      source_account_id: "abc:A",
      destination_account_id: "abc:C",
      path_length: 2,
      accounts: ["abc:A", "abc:B", "abc:C"],
      total_amount: "190.000000",
      hops: [
        { source_account_id: "abc:A", destination_account_id: "abc:B", tx_count: 1, total_amount: "100.000000", transactions: ["abc:0000000001"], timestamps: ["2020-01-01T01:00:00Z"], amounts: ["100.000000"], transaction_types: ["TRANSFER"], transactions_total: 1, evidence_truncated: false },
        { source_account_id: "abc:B", destination_account_id: "abc:C", tx_count: 1, total_amount: "90.000000", transactions: ["abc:0000000002"], timestamps: ["2020-01-01T02:00:00Z"], amounts: ["90.000000"], transaction_types: ["CASH_OUT"], transactions_total: 1, evidence_truncated: false },
      ],
    },
  ],
  paths_found: 1,
  truncated: false,
  applied_limits: { max_depth: 5, max_results: 10, query_timeout_seconds: 5, max_hop_evidence: 20 },
  statement: "A path establishes topological connectivity only.",
  lineage: neighborhood.lineage,
  computed_at: "2026-10-18T03:36:00Z",
  is_stale: false,
};

export function caseOf(extra: Partial<Case> = {}): Case {
  return {
    case_id: "99999999-9999-4999-8999-999999999999",
    title: "Review account B",
    status: "IN_REVIEW",
    priority: "HIGH",
    assigned_to: null,
    created_by: "u-investigator",
    created_at: "2026-10-18T03:36:00Z",
    updated_at: "2026-10-18T03:36:00Z",
    closed_at: null,
    version: 2,
    ...extra,
  };
}

export function run(state: string, extra: Partial<PipelineRun> = {}): PipelineRun {
  return {
    pipeline_run_id: "55555555-5555-4555-8555-555555555555",
    dataset_id: context.dataset_id!,
    ingestion_run_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    current_state: state,
    graph_snapshot_id: null,
    analytics_run_id: null,
    scoring_run_id: null,
    model_version: null,
    started_at: "2026-10-18T03:30:00Z",
    updated_at: "2026-10-18T03:31:00Z",
    completed_at: null,
    failure_stage: null,
    failure_category: null,
    safe_failure_message: null,
    resumable_from: null,
    metrics: { records_seen: 2, records_accepted: 2, job_attempts: 3, lease_expirations: 0 },
    ...extra,
  };
}

export function page<T>(items: T[], pageSize = 25) {
  return { items, page: 1, page_size: pageSize, total: items.length, total_is_capped: false };
}

export function envelope(code: string, message: string, details: Record<string, unknown> = {}) {
  return { error: { code, message, request_id: "req-fixture", details } };
}
