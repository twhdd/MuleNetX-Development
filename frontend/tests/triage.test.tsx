import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import * as fx from "./fixtures";
import { renderAt, signIn } from "./render";
import { server } from "./server";

describe("triage (T27)", () => {
  it("triage ranks accounts in the signal matrix from API scores", async () => {
    signIn();
    renderAt("/");
    const matrix = await screen.findByRole("table", { name: /Signal matrix/ });
    const rows = within(matrix).getAllByRole("row").slice(1);
    expect(rows.map((r) => within(r).getByRole("rowheader").textContent)).toEqual(["BCRITICAL", "AMEDIUM", "CLOW"]);
    expect(await within(rows[0]!).findByTitle("Final score: 0.8123456")).toBeInTheDocument();
    expect(await screen.findByRole("img", { name: /Neighbourhood graph of abc:B/ })).toBeInTheDocument();
  });

  it("triage teaches the empty state when no context is active", async () => {
    signIn();
    server.use(http.get("/api/v1/context", () => HttpResponse.json({ ...fx.context, dataset_id: null, is_active: false })));
    renderAt("/");
    expect(await screen.findByRole("heading", { name: "No active dataset yet" })).toBeInTheDocument();
  });
});
