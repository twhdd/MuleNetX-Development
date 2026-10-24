"""Response read models (SRS §19.4–§19.13), declared so the OpenAPI document carries every response schema.

Models forbid extra fields: a view that drifts from its documented shape fails response validation (500) in
tests instead of silently dropping a field. Deeply variable JSON (profile metrics, model configuration, signal
inputs) stays `dict[str, Any]`, as its contents are defined in the referenced SRS sections.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PageOf[T](Out):
    items: list[T]
    page: int
    page_size: int
    total: int
    total_is_capped: bool


class LineageOut(Out):
    graph_snapshot_id: str | None
    analytics_run_id: str | None
    scoring_run_id: str | None
    model_version: str | None
    risk_logic_version: str | None


class Lineaged(Out):
    """§19.12 lineage envelope."""

    lineage: LineageOut
    computed_at: str | None
    is_stale: bool


# ── errors ──────────────────────────────────────────────────────────────────


class ErrorBody(Out):
    code: str
    message: str
    request_id: str | None
    details: dict[str, Any]


class ErrorEnvelope(Out):
    """§19.3 standard error envelope."""

    error: ErrorBody


# ── health ──────────────────────────────────────────────────────────────────


class HealthOut(Out):
    status: Literal["UP"]


class ReadyComponents(Out):
    postgres: str
    neo4j: str
    ollama: str
    worker: str
    active_context: str


class ReadyOut(Out):
    status: Literal["READY", "NOT_READY"]
    components: ReadyComponents
    details: dict[str, Any]


# ── ingestion, pipeline, models, context ───────────────────────────────────


class IngestionAccepted(Out):
    dataset_id: str
    dataset_key: str
    ingestion_run_id: str
    pipeline_run_id: str
    status: str


class IngestionRunOut(Out):
    ingestion_run_id: str
    dataset_id: str
    dataset_key: str | None
    dataset_name: str | None
    dataset_version: str | None
    pipeline_run_id: str | None
    pipeline_version: str
    status: str
    started_at: str
    completed_at: str | None
    records_seen: int
    records_accepted: int
    records_rejected: int
    records_duplicate: int
    rejection_summary: dict[str, Any]
    error_summary: dict[str, Any] | None


class ProfileOut(Out):
    dataset_id: str
    profile_version: str
    metrics: dict[str, Any]
    created_at: str


class PipelineAccepted(Out):
    pipeline_run_id: str
    status: str


class PipelineRunOut(Out):
    pipeline_run_id: str
    dataset_id: str
    ingestion_run_id: str | None
    current_state: str
    graph_snapshot_id: str | None
    analytics_run_id: str | None
    scoring_run_id: str | None
    model_version: str | None
    started_at: str | None
    updated_at: str | None
    completed_at: str | None
    failure_stage: str | None
    failure_category: str | None
    safe_failure_message: str | None
    resumable_from: str | None
    metrics: dict[str, Any] | None = None


class ModelOut(Out):
    model_version: str
    model_type: str
    target_definition: dict[str, Any]
    feature_version: str
    feature_regime: str
    training_dataset_id: str
    training_snapshot_ids: dict[str, Any]
    split_boundaries: dict[str, Any]
    training_config: dict[str, Any]
    class_distribution: dict[str, Any]
    evaluation_metrics: dict[str, Any]
    operating_threshold: str
    artifact_reference: str
    artifact_sha256: str
    implementation_version: str
    random_seed: int
    created_at: str | None


class ContextOut(Out):
    dataset_id: str | None
    graph_snapshot_id: str | None
    analytics_run_id: str | None
    scoring_run_id: str | None
    model_version: str | None
    risk_logic_version: str | None
    updated_at: str | None
    updated_by_pipeline_run_id: str | None
    is_active: bool
    is_synthetic_injection: bool


# ── accounts, transactions, risk ───────────────────────────────────────────


class AccountOut(Lineaged):
    account_id: str
    source_account_ref: str
    dataset_id: str
    dataset_key: str | None
    account_type: str
    created_at: str | None
    risk_score: float | None
    risk_tier: str | None
    community_id: str | None
    latest_risk_assessment_id: str | None


class TransactionOut(Out):
    transaction_id: str
    source_transaction_ref: str | None
    dataset_id: str
    source_account_id: str
    destination_account_id: str
    amount: str
    timestamp: str
    transaction_type: str
    fraud_label: bool | None
    direction: Literal["in", "out"] | None = None


class TimeRange(Out):
    start: str | None
    end: str | None


class TransactionPage(Out):
    items: list[TransactionOut]
    next_cursor: str | None
    range: TimeRange | None


class AssessmentOut(Lineaged):
    assessment_id: str
    account_id: str
    scoring_run_id: str
    as_of: str
    ml_score: float | None
    graph_signal_score: float
    behavioral_signal_score: float
    rule_signal_score: float
    pre_propagation_score: float
    propagated_risk: float
    final_score: float
    risk_tier: str
    signal_availability: dict[str, Any]
    signal_coverage: float
    max_attainable_score: float
    fired_rules: list[dict[str, Any]]
    model_version: str | None
    feature_version: str
    analytics_version: str | None
    risk_logic_version: str
    generated_at: str
    interpretation: str


class PropagationContribution(Out):
    rank: int
    source_account_id: str
    source_assessment_id: str | None
    distance: int
    source_score: float
    decay_value: float
    contribution: float


class PropagationOut(Lineaged):
    account_id: str
    assessment_id: str
    propagated_risk: float
    contributions: list[PropagationContribution]


class FeatureValueOut(Out):
    feature_id: str
    name: str
    value: float | None
    state: str
    window: str | None
    unit: str | None
    description: str


class FeaturesOut(Lineaged):
    account_id: str
    feature_snapshot_id: str
    feature_version: str
    as_of: str
    features: list[FeatureValueOut]


class TemporalOut(Lineaged):
    account_id: str
    cutoff: str
    feature_version: str
    features: list[FeatureValueOut]


class ShapContribution(Out):
    feature_id: str
    name: str
    value: float | None
    state: str
    shap: float
    relative_importance: float
    direction: str


class ShapOut(Lineaged):
    assessment_id: str
    account_id: str
    model_version: str
    feature_version: str
    explainer: str
    output_space: str
    base_value: float
    ml_score: float
    explains: Literal["ML_COMPONENT_ONLY"]
    statement: str
    top_n: int
    contributions: list[ShapContribution]
    feature_count: int


# ── graph, flow, communities ────────────────────────────────────────────────


class NeighborhoodNode(Out):
    account_id: str
    source_account_ref: str | None
    account_type: str | None
    risk_score: float | None
    risk_tier: str | None
    community_id: str | None
    hop: int


class NeighborhoodEdge(Out):
    source_account_id: str
    destination_account_id: str
    tx_count: int
    total_amount: str
    first_ts: str
    last_ts: str


class NeighborhoodLimits(Out):
    depth: int
    max_nodes: int
    max_edges: int
    query_timeout_seconds: float


class NeighborhoodOut(Lineaged):
    account_id: str
    graph_snapshot_id: str
    depth: int
    nodes: list[NeighborhoodNode]
    edges: list[NeighborhoodEdge]
    truncated: bool
    applied_limits: NeighborhoodLimits


class PathHop(Out):
    source_account_id: str
    destination_account_id: str
    tx_count: int
    total_amount: str
    transactions: list[str]
    timestamps: list[str]
    amounts: list[str]
    transaction_types: list[str]
    transactions_total: int
    evidence_truncated: bool


class PathOut(Out):
    path_id: str
    source_account_id: str
    destination_account_id: str
    path_length: int
    accounts: list[str]
    total_amount: str
    hops: list[PathHop]


class PathLimits(Out):
    max_depth: int
    max_results: int
    query_timeout_seconds: float
    max_hop_evidence: int


class PathQueryOut(Lineaged):
    source_account_id: str
    destination_account_id: str
    mode: Literal["SHORTEST", "ALL"]
    graph_snapshot_id: str
    algorithm_version: str
    paths: list[PathOut]
    paths_found: int
    truncated: bool
    applied_limits: PathLimits
    statement: str


class EvidencePage(Out):
    page: int
    page_size: int


class PathDetailOut(PathOut, Lineaged):
    graph_snapshot_id: str
    algorithm_version: str
    evidence_page: EvidencePage
    statement: str


class GraphMetricsOut(Lineaged):
    account_id: str
    analytics_run_id: str
    analytics_version: str
    engine: str
    degree: int | None
    in_degree: int | None
    out_degree: int | None
    pagerank_raw: float | None
    pagerank_norm: float | None
    betweenness_raw: float | None
    component_id: str | None
    component_size: int | None
    community_id: str | None
    community_size: int | None
    algorithm_configuration: dict[str, Any]


class CommunityOut(Out):
    community_id: str
    analytics_run_id: str
    graph_snapshot_id: str
    algorithm: str
    algorithm_version: str
    member_count: int
    computed_at: str
    analytical_summary: dict[str, Any] | None


class CommunityPage(PageOf[CommunityOut], Lineaged):
    pass


class CommunityMember(Out):
    account_id: str
    source_account_ref: str | None
    account_type: str | None
    risk_tier: str | None
    risk_score: float | None


class CommunityDetailOut(CommunityOut):
    members: PageOf[CommunityMember]
    interpretation: str
    lineage: LineageOut
    is_stale: bool


class AccountCommunityOut(CommunityDetailOut):
    account_id: str


class MotifOut(Out):
    motif_id: str
    motif_type: Literal[
        "RAPID_PASS_THROUGH", "FAN_IN", "FAN_OUT", "CIRCULAR_FLOW", "LAYERED_MOVEMENT", "BURST_ACTIVITY"
    ]
    anchor_account_id: str
    start_time: str
    end_time: str
    temporal_window_seconds: int
    participating_account_ids: list[str]
    participating_transaction_ids: list[str]
    transaction_count: int
    motif_confidence: float
    confidence_components: dict[str, Any]
    order_ambiguous: bool
    truncated: bool
    evidence: dict[str, Any]
    detector_version: str | None
    analytics_version: str


class MotifPage(PageOf[MotifOut], Lineaged):
    interpretation: str


class RingOut(Lineaged):
    ring_id: str
    candidate_class: Literal["SUSPICIOUS_COMMUNITY", "POTENTIAL_FRAUD_RING_CANDIDATE"]
    candidate_status: Literal["CANDIDATE", "REVIEWED", "DISMISSED"]
    candidate_score: float
    signal_summary: dict[str, Any]
    community_id: str
    member_count: int | None
    transaction_count: int | None
    start_time: str | None
    end_time: str | None
    temporal_span_seconds: int | None
    ring_risk_score: float | None
    ring_risk_tier: str | None
    status_changed_by: str | None
    status_changed_at: str | None
    analytics_version: str
    created_at: str | None
    interpretation: str


class RingPage(PageOf[RingOut]):
    interpretation: str


class RingMember(Out):
    account_id: str
    source_account_ref: str | None
    account_type: str | None
    final_score: float | None
    risk_tier: str | None


class RingMemberPage(PageOf[RingMember], Lineaged):
    pass


class RingTransaction(Out):
    transaction_id: str
    source_account_id: str
    destination_account_id: str
    amount: str
    timestamp: str
    transaction_type: str


class RingTransactionPage(Lineaged):
    items: list[RingTransaction]
    next_cursor: str | None


class RingFeature(Out):
    feature: str
    name: str
    value: float
    availability: str | None


class RingFeaturesOut(Lineaged):
    ring_id: str
    ring_feature_set_id: str
    feature_version: str
    ring_size: int
    transaction_count: int
    start_time: str | None
    end_time: str | None
    temporal_span_seconds: int
    features: list[RingFeature]
    eligible_path_count: int
    qualifying_path_count: int
    paths_truncated: bool
    enumeration_counters: dict[str, Any]


class RingComponent(Out):
    component: str
    value: float
    weight: float
    availability: str | None


class RingRiskOut(Lineaged):
    ring_id: str
    ring_risk_assessment_id: str
    ring_risk_score: float
    risk_tier: str
    components: list[RingComponent]
    temporal_indicators: dict[str, int]
    risk_logic_version: str
    feature_version: str
    analytics_version: str
    interpretation: str


class RingEvidenceOut(Lineaged):
    ring_id: str
    source_community: dict[str, str]
    statement: str
    sections: dict[str, PageOf[dict[str, Any]]]
    scope: dict[str, Any]
    features: dict[str, str]
    feature_availability: dict[str, str]
    components: dict[str, str]
    component_availability: dict[str, str]
    ring_risk_score: str
    risk_tier: str
    versions: dict[str, Any]


class ScenarioAccepted(Out):
    scenario_id: str
    status: Literal["QUEUED"]
    hypothetical: Literal[True]


class ScenarioOut(Out):
    scenario_id: str
    hypothetical: Literal[True]
    statement: str
    mode: Literal["RANK", "EVALUATE"]
    status: Literal["QUEUED", "RUNNING", "COMPLETED", "FAILED"]
    target_ring_id: str
    baseline_graph_snapshot_id: str
    scoring_run_id: str
    intervention_type: str | None
    target_ids: list[str] | None
    baseline: dict[str, Any]
    baseline_paths_truncated: bool | None
    metrics_are_lower_bounds: bool
    eligible_candidate_count: int | None
    ranking_configuration: dict[str, Any]
    ranking_configuration_hash: str
    analytics_version: str
    risk_logic_version: str
    requested_by: str
    job_id: str | None
    error_summary: str | None
    created_at: str | None
    completed_at: str | None


class ScenarioPage(PageOf[ScenarioOut]):
    hypothetical: Literal[True]


class InterventionCandidateOut(Out):
    candidate_id: str
    hypothetical: Literal[True]
    baseline_paths_truncated: bool
    rank_position: int
    operation_type: Literal["ACCOUNT_REMOVAL", "INTERMEDIARY_REMOVAL", "ACCOUNT_SET_REMOVAL", "EDGE_REMOVAL"]
    target_ids: list[str]
    intervention_score: float
    residual_suspicious_flow: str
    flow_disruption: str
    flow_disruption_percentage: float
    residual_suspicious_paths: int
    normalized_path_disruption: float
    residual_reachable_suspicious_pairs: int
    normalized_connectivity_disruption: float
    residual_risk_mass: str
    residual_network_risk: float
    normalized_risk_reduction: float
    intervention_cost: float
    normalized_intervention_cost: float
    affected_account_ids: list[str]
    affected_path_ids: list[str]
    alternative_path_ids: list[str]
    unavailable_metrics: list[str]
    evidence: dict[str, Any]


class InterventionCandidatePage(PageOf[InterventionCandidateOut]):
    hypothetical: Literal[True]
    scenario: ScenarioOut


class EvaluationAccepted(Out):
    evaluation_run_id: str
    status: Literal["QUEUED"]


class EvaluationRunOut(Out):
    evaluation_run_id: str
    status: Literal["QUEUED", "RUNNING", "COMPLETED", "FAILED"]
    dataset_id: str
    model_version: str
    test_snapshot_id: str
    scoring_run_id: str
    analytics_version: str
    risk_logic_version: str
    reference_construction_version: str
    configuration: dict[str, Any]
    failure: str | None
    created_at: str | None
    completed_at: str | None
    limitation: str


class EvaluationMetricOut(Out):
    level: Literal["TRANSACTION", "ACCOUNT", "RING", "NETWORK"]
    metric: str
    value: float | None
    sample_count: int
    availability: Literal["AVAILABLE", "UNAVAILABLE"]
    state: str
    details: dict[str, Any]


class EvaluationProgressionStep(Out):
    level: str
    headline_metric: str
    value: float | None
    state: str | None
    sample_count: int | None


class EvaluationSummaryOut(EvaluationRunOut):
    progression: list[EvaluationProgressionStep]
    levels: dict[str, list[EvaluationMetricOut]]
    dataset_profile: dict[str, Any] | None
    state_counts: dict[str, int]


class EvaluationLevelOut(Out):
    evaluation_run_id: str
    level: Literal["TRANSACTION", "ACCOUNT", "RING", "NETWORK"]
    metrics: list[EvaluationMetricOut]
    limitation: str


class EvaluationPage(PageOf[EvaluationRunOut]):
    pass


class CopilotItem(Out):
    text: str
    refs: list[str]


class CopilotModel(Out):
    provider: Literal["ollama"]
    model: str
    model_digest: str | None


class CopilotResponse(Out):
    request_id: str
    intent: Literal[
        "ACCOUNT_SUMMARY",
        "RISK_EXPLANATION",
        "GRAPH_CONTEXT",
        "TEMPORAL_CONTEXT",
        "MONEY_FLOW",
        "RING_SUMMARY",
        "CASE_SUMMARY",
        "UNSUPPORTED",
    ]
    facts: list[CopilotItem]
    observed_signals: list[CopilotItem]
    possible_interpretation: list[CopilotItem]
    limitations: list[str]
    source_references: list[str]
    model: CopilotModel | None
    context_id: str | None
    generated_at: str
    ai_generated: bool
    label: Literal["AI INTERPRETATION"]


# ── cases, audit ────────────────────────────────────────────────────────────


class CaseOut(Out):
    case_id: str
    title: str
    status: str
    priority: str
    assigned_to: str | None
    created_by: str
    created_at: str | None
    updated_at: str | None
    closed_at: str | None
    version: int


class SubjectOut(Out):
    case_id: str
    subject_type: str
    subject_id: str
    added_by: str
    added_at: str | None
    removed_by: str | None
    removed_at: str | None
    active: bool


class FindingOut(Out):
    finding_id: str
    case_id: str
    type: str
    description: str
    evidence: list[dict[str, Any]]
    source: str
    created_by: str
    created_at: str | None
    label: Literal["INVESTIGATOR FINDING"]


class AuditEventOut(Out):
    event_id: str
    user_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    outcome: Literal["SUCCESS", "DENIED", "FAILED"]
    timestamp: str
    request_id: str | None
    metadata: dict[str, Any]
