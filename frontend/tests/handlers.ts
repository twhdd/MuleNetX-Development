import { http, HttpResponse } from "msw";
import * as fx from "./fixtures";

export const handlers = [
  http.post("/api/v1/auth/login", async ({ request }) => {
    const body = (await request.json()) as { username: string; password: string };
    if (body.password !== "right-password")
      return HttpResponse.json(fx.envelope("UNAUTHENTICATED", "Authentication failed."), { status: 401 });
    return HttpResponse.json({ access_token: "tok-123", token_type: "bearer", expires_in: 3600, user: { user_id: "u-investigator", username: body.username, role: "INVESTIGATOR" } });
  }),
  http.post("/api/v1/auth/logout", () => new HttpResponse(null, { status: 204 })),
  http.get("/api/v1/context", () => HttpResponse.json(fx.context)),
  http.get("/api/v1/accounts", () => HttpResponse.json(fx.page(fx.accounts))),
  http.get("/api/v1/accounts/:id", ({ params }) => {
    const found = fx.accounts.find((a) => a.account_id === params.id);
    return found ? HttpResponse.json(found) : HttpResponse.json(fx.envelope("NOT_FOUND", "Not found."), { status: 404 });
  }),
  http.get("/api/v1/accounts/:id/risk", ({ params }) => HttpResponse.json(fx.assessment(String(params.id)))),
  http.get("/api/v1/accounts/:id/risk/history", ({ params }) => HttpResponse.json(fx.page([fx.assessment(String(params.id))]))),
  http.get("/api/v1/accounts/:id/risk/propagation", ({ params }) =>
    HttpResponse.json({ account_id: params.id, assessment_id: "a", propagated_risk: 0.12, contributions: [], lineage: fx.lineage, computed_at: null, is_stale: false }),
  ),
  http.get("/api/v1/accounts/:id/shap", () => HttpResponse.json(fx.shap)),
  http.get("/api/v1/accounts/:id/features", () => HttpResponse.json(fx.features)),
  http.get("/api/v1/accounts/:id/transactions", () => HttpResponse.json(fx.transactions)),
  http.get("/api/v1/graph/neighborhood", () => HttpResponse.json(fx.neighborhood)),
  http.get("/api/v1/graph/metrics", ({ request }) =>
    HttpResponse.json({
      account_id: new URL(request.url).searchParams.get("account_id"),
      analytics_run_id: fx.lineage.analytics_run_id,
      analytics_version: "nx-3.7",
      engine: "networkx",
      degree: 2,
      in_degree: 1,
      out_degree: 1,
      pagerank_raw: 0.3,
      pagerank_norm: 0.5,
      betweenness_raw: 0.5,
      component_id: "c",
      component_size: 3,
      community_id: "c1",
      community_size: 3,
      algorithm_configuration: {},
      lineage: fx.lineage,
      computed_at: null,
      is_stale: false,
    }),
  ),
  http.get("/api/v1/graph/path", () => HttpResponse.json(fx.pathQuery)),
];
