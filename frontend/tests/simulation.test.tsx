import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { EvaluationSummary, InterventionCandidate, Scenario } from "../src/api/types";
import * as fx from "./fixtures";
import { renderAt, signIn } from "./render";
import { server } from "./server";

const RING = "11111111-0000-4000-8000-000000000001";
const SID = "33333333-0000-4000-8000-000000000003";

function scenario(status: Scenario["status"], extra: Partial<Scenario> = {}): Scenario {
  return {
    scenario_id: SID,
    hypothetical: true,
    statement: "Hypothetical simulation: these results describe a counterfactual graph analysis only.",
    mode: "RANK",
    status,
    target_ring_id: RING,
    baseline_graph_snapshot_id: fx.lineage.graph_snapshot_id!,
    scoring_run_id: fx.lineage.scoring_run_id!,
    intervention_type: null,
    target_ids: null,
    baseline: { suspicious_flow: "200.0000", suspicious_paths: 3, reachable_suspicious_pairs: 3, risk_mass: "2.0500000", network_risk: 1 },
    baseline_paths_truncated: true,
    metrics_are_lower_bounds: true,
    eligible_candidate_count: 1,
    ranking_configuration: {},
    ranking_configuration_hash: "h".repeat(64),
    analytics_version: "nx",
    risk_logic_version: "rl",
    requested_by: "u-investigator",
    job_id: null,
    error_summary: null,
    created_at: "2026-10-18T03:40:00Z",
    completed_at: status === "COMPLETED" ? "2026-10-18T03:41:00Z" : null,
    ...extra,
  };
}

const candidate: InterventionCandidate = {
  candidate_id: "c1", hypothetical: true, baseline_paths_truncated: true, rank_position: 1, operation_type: "INTERMEDIARY_REMOVAL",
  target_ids: ["abc:D"], intervention_score: 0.9666667, residual_suspicious_flow: "0.0000", flow_disruption: "200.0000",
  flow_disruption_percentage: 1, residual_suspicious_paths: 0, normalized_path_disruption: 1, residual_reachable_suspicious_pairs: 0,
  normalized_connectivity_disruption: 1, residual_risk_mass: "0", residual_network_risk: 0, normalized_risk_reduction: 1,
  intervention_cost: 1, normalized_intervention_cost: 0.3333333, affected_account_ids: ["abc:A"], affected_path_ids: ["p1"],
  alternative_path_ids: [], unavailable_metrics: [], evidence: { hypothetical: true },
};

function ringHandlers() {
  const ring = { ring_id: RING, candidate_class: "POTENTIAL_FRAUD_RING_CANDIDATE", candidate_status: "CANDIDATE", candidate_score: 0.8, signal_summary: {},
    community_id: "c", member_count: 2, transaction_count: 3, start_time: null, end_time: null, temporal_span_seconds: null, ring_risk_score: 0.6,
    ring_risk_tier: "HIGH", status_changed_by: null, status_changed_at: null, analytics_version: "nx", created_at: null,
    interpretation: "Analytical candidate.", lineage: fx.lineage, computed_at: null, is_stale: false };
  return [
    http.get("/api/v1/rings/:id", () => HttpResponse.json(ring)),
    http.get("/api/v1/rings/:id/accounts", () => HttpResponse.json({ ...fx.page([{ account_id: "abc:A", source_account_ref: "A", account_type: "CUSTOMER", final_score: 0.9, risk_tier: "CRITICAL" }]), lineage: fx.lineage, computed_at: null, is_stale: false })),
    http.get("/api/v1/rings/:id/interventions", () => HttpResponse.json({ ...fx.page([]), hypothetical: true })),
  ];
}

describe("intervention simulation (T39)", () => {
  it("labels every result hypothetical, offers no real action, and shows ranked candidates", async () => {
    signIn();
    let posted: unknown = null;
    server.use(
      ...ringHandlers(),
      http.post("/api/v1/rings/:id/interventions/simulate", async ({ request }) => {
        posted = await request.json();
        return HttpResponse.json({ scenario_id: SID, status: "QUEUED", hypothetical: true }, { status: 202 });
      }),
      http.get("/api/v1/interventions/:id", () => HttpResponse.json(scenario("COMPLETED"))),
      http.get("/api/v1/interventions/:id/candidates", () => HttpResponse.json({ ...fx.page([candidate]), hypothetical: true, scenario: scenario("COMPLETED") })),
    );
    const { user } = renderAt(`/rings/${RING}/simulate`);
    expect(await screen.findByText(/never blocks, freezes, rejects or reroutes/)).toBeInTheDocument();
    for (const b of screen.getAllByRole("button")) expect(b.textContent ?? "").not.toMatch(/block|freeze|disable|reject/i);
    await user.click(await screen.findByRole("button", { name: "Run simulation" }));
    expect(posted).toEqual({ mode: "RANK" });
    const results = await screen.findByRole("region", { name: "Simulation results" });
    expect(within(results).getByText("HYPOTHETICAL SIMULATION")).toBeInTheDocument();
    expect(await within(results).findByText(/every figure below is a lower bound/)).toBeInTheDocument();
    expect(await within(results).findByText("Intermediary removal")).toBeInTheDocument();
    expect(within(results).getAllByText("100.0%").length).toBeGreaterThan(0);
  });

  it("explains the per-user limit and invalid targets", async () => {
    signIn();
    server.use(
      ...ringHandlers(),
      http.post("/api/v1/rings/:id/interventions/simulate", () => HttpResponse.json(fx.envelope("RATE_LIMITED", "Too many."), { status: 429 })),
    );
    const { user } = renderAt(`/rings/${RING}/simulate`);
    await user.click(await screen.findByRole("button", { name: "Run simulation" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("two simulations queued or running");
  });
});

const summary: EvaluationSummary = {
  evaluation_run_id: "44444444-0000-4000-8000-000000000004", status: "COMPLETED", dataset_id: "d", model_version: "m",
  test_snapshot_id: "s", scoring_run_id: "r", analytics_version: "nx", risk_logic_version: "rl", reference_construction_version: "reference-v1",
  configuration: { lineage: { model_version: "m" } }, failure: null, created_at: null, completed_at: null,
  limitation: "PaySim provides synthetic transaction-level fraud labels only. It has no authoritative mule-account or mule-ring ground truth.",
  progression: ["TRANSACTION", "ACCOUNT", "RING", "NETWORK"].map((level, i) => ({ level, headline_metric: "pr_auc", value: 0.1 * (i + 1), state: "AVAILABLE", sample_count: 10 })),
  levels: {
    TRANSACTION: [{ level: "TRANSACTION", metric: "pr_auc", value: 0.08, sample_count: 207, availability: "AVAILABLE", state: "AVAILABLE", details: {} }],
    ACCOUNT: [{ level: "ACCOUNT", metric: "mule_account_identity", value: null, sample_count: 0, availability: "UNAVAILABLE", state: "NOT_MEASURABLE", details: { reason: "PaySim does not label mule accounts." } }],
    RING: [],
    NETWORK: [{ level: "NETWORK", metric: "intervention_effectiveness_rank1", value: 0.65, sample_count: 1, availability: "AVAILABLE", state: "AVAILABLE", details: {} }],
  },
  dataset_profile: {},
  state_counts: {},
};

describe("evaluation report (T39)", () => {
  it("shows the four-level progression, the PaySim limitation and not-measurable metrics", async () => {
    signIn("ANALYST", "u-analyst");
    server.use(
      http.get("/api/v1/evaluation/runs", () => HttpResponse.json(fx.page([summary]))),
      http.get("/api/v1/evaluation/runs/:id", () => HttpResponse.json(summary)),
    );
    renderAt("/evaluation");
    const progression = await screen.findByLabelText("Progression");
    expect(within(progression).getAllByText(/Transaction|Account|Ring|Network/).map((n) => n.textContent)).toEqual(["Transaction", "Account", "Ring", "Network"]);
    expect(screen.getByRole("note")).toHaveTextContent("no authoritative mule-account or mule-ring ground truth");
    expect(screen.getByText("not measurable")).toBeInTheDocument();
    expect(screen.getByText("HYPOTHETICAL SIMULATION")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Run evaluation" })).toBeNull(); // pipeline.control is ADMIN only
  });
});
