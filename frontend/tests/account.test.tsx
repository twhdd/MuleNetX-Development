import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import * as fx from "./fixtures";
import { renderAt, signIn } from "./render";
import { server } from "./server";

describe("account search and workspace (T26)", () => {
  it("lists accounts from the API with tier and score", async () => {
    signIn();
    renderAt("/accounts");
    expect(await screen.findByRole("heading", { name: "Accounts" })).toBeInTheDocument();
    const table = await screen.findByRole("table");
    expect(within(table).getByRole("link", { name: "B" })).toHaveAttribute("href", "/accounts/abc%3AB");
    expect(within(table).getByText("CRITICAL")).toBeInTheDocument();
    expect(within(table).getByText("0.810")).toBeInTheDocument();
  });

  it("shows every risk component, coverage and SHAP labelled as explaining the ML component only", async () => {
    signIn();
    renderAt("/accounts/abc%3AB");
    expect(await screen.findByRole("heading", { level: 1, name: "B" })).toBeInTheDocument();
    expect(await screen.findByText("Signal coverage 100% · maximum attainable 0.812")).toBeInTheDocument();
    for (const label of ["ML model", "Graph signal", "Behavioural signal", "Rule signal", "Propagated risk"]) expect(screen.getByText(label)).toBeInTheDocument();
    expect(await screen.findByText("This explanation covers the ML component (ml_score) only.")).toBeInTheDocument();
    expect(screen.getAllByText("MODEL OUTPUT").length).toBeGreaterThan(0);
    expect(screen.getByText("R01 · rapid pass-through")).toBeInTheDocument();
    expect(screen.getByText(/not a determination of fraud/)).toBeInTheDocument();
  });

  it("renders an unavailable ML component from availability fields, not a zero", async () => {
    signIn();
    server.use(
      http.get("/api/v1/accounts/:id/risk", ({ params }) =>
        HttpResponse.json(
          fx.assessment(String(params.id), {
            ml_score: null,
            model_version: null,
            signal_availability: { ml: { state: "UNAVAILABLE", reason: "NO_COMPATIBLE_MODEL" }, graph: { state: "AVAILABLE" }, behavioral: { state: "AVAILABLE" }, rules: { state: "AVAILABLE" }, propagation: { state: "AVAILABLE" } },
            signal_coverage: 0.5,
            max_attainable_score: 0.5,
          }),
        ),
      ),
      http.get("/api/v1/accounts/:id/shap", () => HttpResponse.json(fx.envelope("EXPLANATION_NOT_AVAILABLE", "No explanation."), { status: 404 })),
    );
    renderAt("/accounts/abc%3AB");
    expect(await screen.findByText("Unavailable · NO_COMPATIBLE_MODEL")).toBeInTheDocument();
    expect(await screen.findByText("The ML component was unavailable for this assessment.")).toBeInTheDocument();
  });

  it("shows STALE only when the API says is_stale", async () => {
    signIn();
    server.use(http.get("/api/v1/accounts/:id", () => HttpResponse.json(fx.account("B", 0.81, "CRITICAL", { is_stale: true }))));
    renderAt("/accounts/abc%3AB");
    expect((await screen.findAllByText(/Stale: computed in an earlier analytical context/)).length).toBeGreaterThan(0);
  });

  it("shows UNAVAILABLE when no assessment exists in the active scoring run", async () => {
    signIn();
    server.use(http.get("/api/v1/accounts/:id/risk", () => HttpResponse.json(fx.envelope("RISK_NOT_AVAILABLE", "No risk assessment is available for this account."), { status: 404 })));
    renderAt("/accounts/abc%3AB");
    expect(await screen.findByText("No assessment exists for this account in the active scoring run.")).toBeInTheDocument();
  });

  it("lists features with their states and the transactions with direction", async () => {
    signIn();
    const { user } = renderAt("/accounts/abc%3AB?tab=features");
    expect(await screen.findByText("transaction_count")).toBeInTheDocument();
    expect(screen.getByText("UNAVAILABLE")).toBeInTheDocument();
    expect(screen.getByText("ZERO")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Transactions" }));
    expect(await screen.findByText("90.00")).toBeInTheDocument();
    expect(screen.getByText("OUT")).toBeInTheDocument();
    expect(screen.getByText("IN")).toBeInTheDocument();
    expect(await screen.findByRole("grid", { name: "Transactions per hour, by day (UTC)" })).toBeInTheDocument();
  });

});
