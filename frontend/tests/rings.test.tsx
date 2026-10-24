import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { Motif, Ring } from "../src/api/types";
import * as fx from "./fixtures";
import { renderAt, signIn } from "./render";
import { server } from "./server";

const lineage = fx.lineage;

function ring(id: string, cls: Ring["candidate_class"], extra: Partial<Ring> = {}): Ring {
  return {
    ring_id: id,
    candidate_class: cls,
    candidate_status: "CANDIDATE",
    candidate_score: cls === "POTENTIAL_FRAUD_RING_CANDIDATE" ? 0.7369318 : 0.55,
    signal_summary: {
      H: { value: "0.6000000", available: true, weight: "0.35" },
      D: { value: "0.8750000", available: true, weight: "0.25" },
      C: { value: "0.8000000", available: true, weight: "0.15" },
      community_temporal_density: { value: "0.8000000", available: true, weight: "0.15" },
      M: { value: "0.0000000", available: false, weight: "0.10" },
      formula: "clamp(0.35·H + 0.25·D + 0.15·C + 0.15·community_temporal_density + 0.10·M, 0, 1)",
    },
    community_id: "c0ffee00-0000-5000-8000-000000000001",
    member_count: 5,
    transaction_count: 5,
    start_time: "2020-01-01T00:00:00Z",
    end_time: "2020-01-01T02:00:00Z",
    temporal_span_seconds: 7200,
    ring_risk_score: cls === "POTENTIAL_FRAUD_RING_CANDIDATE" ? 0.578 : null,
    ring_risk_tier: cls === "POTENTIAL_FRAUD_RING_CANDIDATE" ? "HIGH" : null,
    status_changed_by: null,
    status_changed_at: null,
    analytics_version: "nx-3.7",
    created_at: "2026-10-18T03:34:08Z",
    interpretation: "Analytical candidate: a potential fraud ring or suspicious network for investigation. Community membership is not proof of a fraud ring.",
    lineage,
    computed_at: "2026-10-18T03:34:08Z",
    is_stale: false,
    ...extra,
  };
}

const POT = ring("11111111-0000-4000-8000-000000000001", "POTENTIAL_FRAUD_RING_CANDIDATE");
const SC = ring("22222222-0000-4000-8000-000000000002", "SUSPICIOUS_COMMUNITY");

const motif: Motif = {
  motif_id: "m1",
  motif_type: "RAPID_PASS_THROUGH",
  anchor_account_id: "abc:A",
  start_time: "2020-01-01T01:00:00Z",
  end_time: "2020-01-01T01:00:00Z",
  temporal_window_seconds: 900,
  participating_account_ids: ["abc:A", "abc:B", "abc:C"],
  participating_transaction_ids: ["abc:1", "abc:2"],
  transaction_count: 2,
  motif_confidence: 1,
  confidence_components: { structural_match: "1.0000000", temporal_match: "1.0000000", participant_match: "1.0000000" },
  order_ambiguous: true,
  truncated: false,
  evidence: {},
  detector_version: "motifs-v1",
  analytics_version: "nx-3.7",
};

function ringHandlers() {
  return [
    http.get("/api/v1/rings", () => HttpResponse.json({ ...fx.page([POT, SC]), interpretation: POT.interpretation })),
    http.get("/api/v1/rings/:id", ({ params }) => HttpResponse.json(params.id === SC.ring_id ? SC : POT)),
    http.get("/api/v1/rings/:id/risk", () =>
      HttpResponse.json({
        ring_id: POT.ring_id,
        ring_risk_assessment_id: "rr",
        ring_risk_score: 0.578,
        risk_tier: "HIGH",
        components: [
          { component: "member_risk", value: 0.56, weight: 0.25, availability: "AVAILABLE" },
          { component: "money_flow_signal", value: 0.8888889, weight: 0.15, availability: "LOWER_BOUND_TRUNCATED" },
        ],
        temporal_indicators: { RAPID_PASS_THROUGH: 1 },
        risk_logic_version: "rl-1",
        feature_version: "ring-features-v1",
        analytics_version: "nx-3.7",
        interpretation: "Ring risk assessment: an analytical score for prioritising review.",
        lineage,
        computed_at: null,
        is_stale: false,
      }),
    ),
    http.get("/api/v1/rings/:id/features", () =>
      HttpResponse.json({
        ring_id: POT.ring_id, ring_feature_set_id: "fs", feature_version: "ring-features-v1", ring_size: 5, transaction_count: 5,
        start_time: null, end_time: null, temporal_span_seconds: 7200,
        features: [{ feature: "RSD", name: "suspicious_transaction_density", value: 0.8, availability: "AVAILABLE" }],
        eligible_path_count: 18, qualifying_path_count: 9, paths_truncated: false, enumeration_counters: {},
        lineage, computed_at: null, is_stale: false,
      }),
    ),
    http.get("/api/v1/rings/:id/motifs", () => HttpResponse.json({ ...fx.page([motif]), interpretation: "A motif is an analytical pattern.", lineage, computed_at: null, is_stale: false })),
  ];
}

describe("rings and motifs (T35)", () => {
  it("lists both classes in analytical wording", async () => {
    signIn();
    server.use(...ringHandlers());
    renderAt("/rings");
    const table = await screen.findByRole("table");
    expect(within(table).getByText("Potential fraud ring")).toBeInTheDocument();
    expect(within(table).getByText("Suspicious community")).toBeInTheDocument();
    expect(within(table).getByText("not computed")).toBeInTheDocument();
    expect(screen.getByText(/not confirmed criminal organisations/)).toBeInTheDocument();
    expect(screen.queryByText(/criminal ring|fraudsters/i)).toBeNull();
  });

  it("shows ring risk components with availability for a potential fraud ring", async () => {
    signIn();
    server.use(...ringHandlers());
    renderAt(`/rings/${POT.ring_id}`);
    expect(await screen.findByText("Ring risk assessment")).toBeInTheDocument();
    expect(await screen.findByText("0.578")).toBeInTheDocument();
    expect(screen.getByText("lower bound (path enumeration truncated)")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Evidence" })).toBeInTheDocument();
    expect(await screen.findByText("9 qualifying of 18 eligible paths in ring scope · span 7,200 s")).toBeInTheDocument();
  });

  it("does not offer ring intelligence for a suspicious community", async () => {
    signIn();
    server.use(...ringHandlers());
    renderAt(`/rings/${SC.ring_id}`);
    expect(await screen.findByText(/computed for potential fraud ring candidates only/)).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Evidence" })).toBeNull();
  });

  it("offers review to investigators and records the server's answer", async () => {
    signIn("INVESTIGATOR");
    let body: unknown = null;
    server.use(
      ...ringHandlers(),
      http.patch("/api/v1/rings/:id/status", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ ...POT, candidate_status: "REVIEWED" });
      }),
    );
    const { user } = renderAt(`/rings/${POT.ring_id}`);
    await user.click(await screen.findByRole("button", { name: "Mark reviewed" }));
    expect(body).toEqual({ status: "REVIEWED" });
    expect(await screen.findByText("Reviewed")).toBeInTheDocument();
  });

  it("offers no review controls to analysts", async () => {
    signIn("ANALYST", "u-analyst");
    server.use(...ringHandlers());
    renderAt(`/rings/${POT.ring_id}`);
    await screen.findByText("Ring risk assessment");
    expect(screen.queryByRole("group", { name: "Review status" })).toBeNull();
  });

  it("shows motif confidence components and order ambiguity", async () => {
    signIn();
    server.use(...ringHandlers());
    renderAt(`/rings/${POT.ring_id}?tab=motifs`);
    const article = await screen.findByRole("article", { name: "Rapid pass through anchored at abc:A" });
    expect(within(article).getByText("order ambiguous")).toBeInTheDocument();
    expect(within(article).getByText("Timing")).toBeInTheDocument();
    expect(within(article).getByLabelText("Pattern confidence 1.000")).toBeInTheDocument();
    expect(screen.getByText(/compare timing, not confidence/)).toBeInTheDocument();
  });
});
