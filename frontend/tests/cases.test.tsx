import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import * as fx from "./fixtures";
import { renderAt, signIn } from "./render";
import { server } from "./server";

function caseHandlers(current = fx.caseOf()) {
  return [
    http.get("/api/v1/cases/:id", () => HttpResponse.json(current)),
    http.get("/api/v1/cases/:id/subjects", () =>
      HttpResponse.json(fx.page([{ case_id: current.case_id, subject_type: "ACCOUNT", subject_id: "abc:B", added_by: "u-investigator", added_at: "2026-10-18T03:36:00Z", removed_by: null, removed_at: null, active: true }])),
    ),
    http.get("/api/v1/cases/:id/findings", () => HttpResponse.json(fx.page([]))),
  ];
}

describe("cases (T28)", () => {
  it("offers investigators the legal transitions and applies one", async () => {
    signIn("INVESTIGATOR");
    let patched: unknown = null;
    server.use(
      ...caseHandlers(),
      http.patch("/api/v1/cases/:id", async ({ request }) => {
        patched = await request.json();
        return HttpResponse.json(fx.caseOf({ status: "RESOLVED", version: 3 }));
      }),
    );
    const { user } = renderAt(`/cases/${fx.caseOf().case_id}`);
    const group = await screen.findByRole("group", { name: "Status transitions" });
    expect(within(group).getAllByRole("button").map((b) => b.textContent)).toEqual(["Escalate", "Resolve", "Mark false positive"]);
    await user.click(within(group).getByRole("button", { name: "Resolve" }));
    expect(patched).toEqual({ version: 2, status: "RESOLVED" });
    expect(await screen.findByText("Resolved")).toBeInTheDocument();
  });

  it("shows a reload prompt on 409 CASE_VERSION_CONFLICT and reloads the latest version", async () => {
    signIn("INVESTIGATOR");
    let version = 2;
    server.use(
      http.get("/api/v1/cases/:id", () => HttpResponse.json(fx.caseOf({ version, title: version === 2 ? "Review account B" : "Renamed elsewhere" }))),
      ...caseHandlers().slice(1),
      http.patch("/api/v1/cases/:id", () => {
        version = 3;
        return HttpResponse.json(fx.envelope("CASE_VERSION_CONFLICT", "The case was modified."), { status: 409 });
      }),
    );
    const { user } = renderAt(`/cases/${fx.caseOf().case_id}`);
    await user.click(await screen.findByRole("button", { name: "Escalate" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("This case changed since you loaded it.");
    await user.click(screen.getByRole("button", { name: "Reload latest" }));
    expect(await screen.findByRole("heading", { name: "Renamed elsewhere" })).toBeInTheDocument();
  });

  it("offers an analyst who is not a participant no transitions, and surfaces a server 403", async () => {
    signIn("ANALYST", "u-analyst");
    server.use(...caseHandlers(), http.post("/api/v1/cases/:id/subjects", () => HttpResponse.json(fx.envelope("FORBIDDEN", "Forbidden."), { status: 403 })));
    const { user } = renderAt(`/cases/${fx.caseOf().case_id}`);
    const group = await screen.findByRole("group", { name: "Status transitions" });
    expect(within(group).queryAllByRole("button")).toHaveLength(0);
    expect(screen.queryByRole("button", { name: "Assign" })).toBeNull();
    await user.type(screen.getByLabelText("ID"), "abc:C");
    await user.click(screen.getByRole("button", { name: "Link" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Your role cannot make this change on this case.");
  });

  it("labels findings and reports a missing evidence reference by position", async () => {
    signIn("INVESTIGATOR");
    server.use(...caseHandlers(), http.post("/api/v1/cases/:id/findings", () => HttpResponse.json(fx.envelope("VALIDATION_ERROR", "Invalid.", { field: "evidence.0" }), { status: 400 })));
    const { user } = renderAt(`/cases/${fx.caseOf().case_id}`);
    expect(await screen.findByText("INVESTIGATOR FINDING")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Finding"), "Pass-through within the hour.");
    await user.click(screen.getByRole("button", { name: "Evidence reference" }));
    await user.type(screen.getByLabelText("Evidence 1 ID"), "abc:NOPE");
    await user.click(screen.getByRole("button", { name: "Record finding" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Evidence reference 1 does not exist.");
  });

  it("reads pipeline progress from /pipeline-runs/{id}, never from the ingestion response", async () => {
    signIn("ADMIN", "u-admin");
    server.use(http.get("/api/v1/pipeline-runs/:id", () => HttpResponse.json(fx.run("GRAPH_BUILDING"))));
    renderAt(`/admin/pipelines/${fx.run("x").pipeline_run_id}`);
    expect(await screen.findByText("Graph building")).toBeInTheDocument();
    const stages = screen.getByLabelText("Stages");
    expect(within(stages).getAllByText("done")).toHaveLength(2);
    expect(within(stages).getByText("running")).toBeInTheDocument();
  });

  it("hides admin-only pages from other roles", async () => {
    signIn("ANALYST", "u-analyst");
    renderAt("/admin/audit");
    expect(await screen.findByText("Your role cannot open this page.")).toBeInTheDocument();
  });
});
