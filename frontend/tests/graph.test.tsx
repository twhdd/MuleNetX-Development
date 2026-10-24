import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { initialPositions, layout, type LayoutNode } from "../src/lib/layout";
import * as fx from "./fixtures";
import { renderAt, signIn } from "./render";
import { server } from "./server";

describe("graph explorer and path view (T27)", () => {
  it("renders the abc_chain neighbourhood with its applied limits", async () => {
    signIn();
    renderAt("/graph?account=abc%3AB");
    const graph = await screen.findByRole("img", { name: "Neighbourhood graph of abc:B: 3 accounts, 2 aggregated transfers" });
    expect(within(graph).getByRole("button", { name: /abc:A, risk 0.520, MEDIUM, hop 1/ })).toBeInTheDocument();
    expect(screen.getByText(/Applied: 2 hops · 100 accounts · 500 transfers · 5s timeout/)).toBeInTheDocument();
    expect(screen.queryByText(/Truncated breadth-first/)).toBeNull();
    expect(await screen.findByText("Graph metrics")).toBeInTheDocument();
  });

  it("states truncation when the API truncated", async () => {
    signIn();
    server.use(http.get("/api/v1/graph/neighborhood", () => HttpResponse.json({ ...fx.neighborhood, truncated: true })));
    renderAt("/graph?account=abc%3AB");
    expect(await screen.findByText(/Truncated breadth-first by hop and amount/)).toBeInTheDocument();
  });

  it("shows the flow matrix heatmap view", async () => {
    signIn();
    renderAt("/graph?account=abc%3AB&view=matrix");
    expect(await screen.findByRole("img", { name: "Flow matrix of 3 accounts and 2 aggregated transfers" })).toBeInTheDocument();
  });

  it("maps a 503 to UNAVAILABLE", async () => {
    signIn();
    server.use(http.get("/api/v1/graph/neighborhood", () => HttpResponse.json(fx.envelope("GRAPH_UNAVAILABLE", "The graph store is unavailable."), { status: 503 })));
    renderAt("/graph?account=abc%3AB");
    expect(await screen.findByText("The graph store is unavailable. Risk and case data remain readable.")).toBeInTheDocument();
  });

  it("shows a path with the §16.9 statement that a path is connectivity, not proven fund movement", async () => {
    signIn();
    renderAt("/paths?from=abc%3AA&to=abc%3AC");
    expect(await screen.findByRole("note")).toHaveTextContent("A path establishes topological connectivity only.");
    const path = screen.getByRole("article", { name: "Path 1" });
    expect(within(path).getByText("190.00")).toBeInTheDocument();
    expect(within(path).getAllByRole("link").map((a) => a.textContent)).toEqual(["A", "B", "C"]);
  });

  it("lays out deterministically from BFS hop rings ordered by account_id", () => {
    const make = (): LayoutNode[] => [
      { id: "b", hop: 1, r: 6 },
      { id: "focus", hop: 0, r: 15 },
      { id: "a", hop: 1, r: 6 },
    ];
    const start = initialPositions(make());
    expect(start.get("focus")).toEqual({ x: 0, y: 0 });
    expect(start.get("a")!.y).toBeLessThan(start.get("b")!.y + 1e-9); // "a" sorts first on the ring
    const one = make();
    const two = make();
    layout(one, [{ source: "focus", target: "a", amount: "1" }]);
    layout(two, [{ source: "focus", target: "a", amount: "1" }]);
    expect(one.map((n) => [n.x, n.y])).toEqual(two.map((n) => [n.x, n.y]));
  });
});
