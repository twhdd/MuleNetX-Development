import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { CopilotResponse } from "../src/api/types";
import { refTarget } from "../src/lib/copilotRefs";
import * as fx from "./fixtures";
import { renderAt, signIn } from "./render";
import { server } from "./server";

function answer(extra: Partial<CopilotResponse> = {}): CopilotResponse {
  return {
    request_id: "r-1",
    intent: "RISK_EXPLANATION",
    facts: [{ text: "The account's final score is 0.81 in the active run.", refs: ["assessment:a1", "account:abc:B"] }],
    observed_signals: [{ text: "Outflow follows inflow within minutes.", refs: ["transaction:abc:0001"] }],
    possible_interpretation: [{ text: "This could be consistent with pass-through activity.", refs: ["assessment:a1"] }],
    limitations: ["Scores are analytical signals, not determinations."],
    source_references: ["account:abc:B", "edge:snap-1:abc:A>abc:B"],
    model: { provider: "ollama", model: "qwen2.5:7b-instruct", model_digest: "sha256:feed" },
    context_id: "c0c0c0c0-0000-4000-8000-000000000001",
    generated_at: "2026-10-18T04:00:00Z",
    ai_generated: true,
    label: "AI INTERPRETATION",
    ...extra,
  };
}

describe("copilot panel (T41)", () => {
  it("shows facts, signals, interpretation and limitations apart, with clickable refs and the AI label", async () => {
    signIn("ANALYST");
    let sent: Record<string, unknown> | null = null;
    server.use(
      http.post("/api/v1/copilot/query", async ({ request }) => {
        sent = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(answer());
      }),
    );
    const { user } = renderAt("/accounts/abc%3AB?tab=copilot");
    const panel = await screen.findByRole("region", { name: "Copilot" });
    expect(within(panel).getByText("AI INTERPRETATION")).toBeInTheDocument();
    await user.click(within(panel).getByRole("button", { name: "Why is this account scored this way?" }));
    expect(await within(panel).findByText("The account's final score is 0.81 in the active run.")).toBeInTheDocument();
    expect(sent).toEqual({ question: "Why is this account scored this way?", account_id: "abc:B" });
    for (const title of ["Facts", "Observed signals", "Possible interpretation", "Limitations", "Sources"])
      expect(within(panel).getByRole("heading", { name: title })).toBeInTheDocument();
    expect(within(panel).getByText("Scores are analytical signals, not determinations.")).toBeInTheDocument();
    const accountRefs = within(panel).getAllByRole("link", { name: /account\s*abc:B/i });
    expect(accountRefs[0]).toHaveAttribute("href", "/accounts/abc%3AB");
    expect(within(panel).getAllByRole("link", { name: /assessment/i })[0]).toHaveAttribute("href", "/accounts/abc%3AB?tab=risk");
    expect(within(panel).getByRole("link", { name: /edge/i })).toHaveAttribute("href", "/paths?from=abc%3AA&to=abc%3AB");
    expect(within(panel).getByRole("link", { name: /transaction/i })).toHaveAttribute("href", "/accounts/abc%3AB?tab=transactions");
    expect(within(panel).getByText("qwen2.5:7b-instruct")).toBeInTheDocument();
  });

  it("shows a clear unavailable state while the rest of the workspace keeps working", async () => {
    signIn("ANALYST");
    server.use(
      http.post("/api/v1/copilot/query", () =>
        HttpResponse.json(fx.envelope("COPILOT_UNAVAILABLE", "The copilot is unavailable."), { status: 503 }),
      ),
    );
    const { user } = renderAt("/accounts/abc%3AB?tab=copilot");
    const panel = await screen.findByRole("region", { name: "Copilot" });
    await user.type(within(panel).getByRole("textbox"), "Summarise this account");
    await user.click(within(panel).getByRole("button", { name: "Ask" }));
    const alert = await within(panel).findByRole("alert");
    expect(alert).toHaveAttribute("data-code", "COPILOT_UNAVAILABLE");
    expect(within(alert).getByText("Copilot unavailable")).toBeInTheDocument();
    expect(within(alert).getByText(/Everything else in this workspace works without it/)).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Risk" }));
    expect(await screen.findByText("Signal coverage 100% · maximum attainable 0.812")).toBeInTheDocument();
  });

  it("explains a discarded answer and a busy model", async () => {
    signIn("ANALYST");
    let calls = 0;
    server.use(
      http.post("/api/v1/copilot/query", () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json(fx.envelope("AI_RESPONSE_INVALID", "Invalid.", { rule: 2 }), { status: 503 })
          : HttpResponse.json(fx.envelope("COPILOT_BUSY", "Busy."), { status: 429 });
      }),
    );
    const { user } = renderAt("/accounts/abc%3AB?tab=copilot");
    const panel = await screen.findByRole("region", { name: "Copilot" });
    await user.click(within(panel).getByRole("button", { name: "Where did money flow?" }));
    expect(await within(panel).findByText("Answer discarded")).toBeInTheDocument();
    expect(within(panel).getByText(/cited a reference that was not in the evidence/)).toBeInTheDocument();
    await user.click(within(panel).getByRole("button", { name: "Where did money flow?" }));
    expect(await within(panel).findByText("Copilot busy")).toBeInTheDocument();
  });

  it("renders an unsupported question without the AI sections", async () => {
    signIn("ANALYST");
    server.use(
      http.post("/api/v1/copilot/query", () =>
        HttpResponse.json(
          answer({ intent: "UNSUPPORTED", facts: [], observed_signals: [], possible_interpretation: [], source_references: [], model: null, context_id: null, ai_generated: false, limitations: ["The copilot answers questions about a referenced account, case or ring."] }),
        ),
      ),
    );
    const { user } = renderAt("/accounts/abc%3AB?tab=copilot");
    const panel = await screen.findByRole("region", { name: "Copilot" });
    await user.type(within(panel).getByRole("textbox"), "Write a poem");
    await user.click(within(panel).getByRole("button", { name: "Ask" }));
    expect(await within(panel).findByText("Not a question the copilot answers")).toBeInTheDocument();
    expect(within(panel).queryByRole("heading", { name: "Facts" })).toBeNull();
  });

  it("appears in the case workspace with the case as scope", async () => {
    signIn("INVESTIGATOR");
    let sent: Record<string, unknown> | null = null;
    server.use(
      http.get("/api/v1/cases/:id", () => HttpResponse.json(fx.caseOf())),
      http.get("/api/v1/cases/:id/subjects", () => HttpResponse.json(fx.page([]))),
      http.get("/api/v1/cases/:id/findings", () => HttpResponse.json(fx.page([]))),
      http.post("/api/v1/copilot/query", async ({ request }) => {
        sent = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(answer({ intent: "CASE_SUMMARY", facts: [{ text: "The case has one finding.", refs: ["finding:f1"] }] }));
      }),
    );
    const { user } = renderAt(`/cases/${fx.caseOf().case_id}`);
    const panel = await screen.findByRole("region", { name: "Copilot" });
    await user.click(within(panel).getByRole("button", { name: "Summarise this case" }));
    expect(await within(panel).findByText("The case has one finding.")).toBeInTheDocument();
    expect(sent).toEqual({ question: "Summarise this case", case_id: fx.caseOf().case_id });
    expect(within(panel).getByRole("link", { name: /finding/i })).toHaveAttribute("href", `/cases/${fx.caseOf().case_id}`);
  });
});

describe("copilot reference targets", () => {
  it("parses account IDs that contain colons", () => {
    expect(refTarget("feature:abc:B:in_degree", {})).toEqual({ kind: "feature", label: "in_degree", href: "/accounts/abc%3AB?tab=features" });
    expect(refTarget("metrics:run-1:abc:B", {}).href).toBe("/graph?account=abc%3AB");
    expect(refTarget("motif:m1", { ring_id: "r1" }).href).toBe("/rings/r1?tab=motifs");
    expect(refTarget("transaction:abc:1", {}).href).toBeNull();
    expect(refTarget("mystery", {}).href).toBeNull();
  });
});
