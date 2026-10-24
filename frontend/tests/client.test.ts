import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { ApiError, api, buildUrl } from "../src/api/client";
import { useSession } from "../src/state/session";
import { envelope } from "./fixtures";
import { server } from "./server";

describe("api client (SRS §20.2, §19.3)", () => {
  it("sends the bearer token and a request id, and builds /api/v1 urls", async () => {
    useSession.getState().signIn("tok-xyz", { user_id: "u", username: "u", role: "ADMIN" }, 60);
    let seen: Headers | null = null;
    server.use(
      http.get("/api/v1/models", ({ request }) => {
        seen = request.headers;
        return HttpResponse.json({ items: [], page: 1, page_size: 25, total: 0, total_is_capped: false });
      }),
    );
    await api.get("/models", { page: 2, empty: "", nothing: undefined });
    expect(seen!.get("authorization")).toBe("Bearer tok-xyz");
    expect(seen!.get("x-request-id")).toMatch(/[0-9a-f-]{8,}/);
    expect(buildUrl("/models", { page: 2, empty: "", nothing: undefined })).toBe("/api/v1/models?page=2");
    expect(buildUrl("/health")).toBe("/health");
  });

  it("parses the error envelope into ApiError", async () => {
    server.use(http.get("/api/v1/cases/x", () => HttpResponse.json(envelope("CASE_VERSION_CONFLICT", "Stale version.", { current_version: 3 }), { status: 409 })));
    const err = await api.get("/cases/x").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 409, code: "CASE_VERSION_CONFLICT", message: "Stale version.", requestId: "req-fixture", details: { current_version: 3 } });
  });

  it("falls back when the body is not an envelope", async () => {
    server.use(http.get("/api/v1/context", () => new HttpResponse("<html>bad gateway</html>", { status: 502, statusText: "Bad Gateway" })));
    const err = (await api.get("/context").catch((e: unknown) => e)) as ApiError;
    expect(err.status).toBe(502);
    expect(err.code).toBe("INTERNAL");
  });

  it("drops an expired session on 401 and marks it expired", async () => {
    useSession.getState().signIn("tok-old", { user_id: "u", username: "u", role: "ANALYST" }, 60);
    server.use(http.get("/api/v1/context", () => HttpResponse.json(envelope("UNAUTHENTICATED", "Session expired."), { status: 401 })));
    await expect(api.get("/context")).rejects.toMatchObject({ status: 401 });
    expect(useSession.getState().token).toBeNull();
    expect(useSession.getState().expired).toBe(true);
  });

  it("reports a network failure as NETWORK_ERROR", async () => {
    server.use(http.get("/api/v1/context", () => HttpResponse.error()));
    await expect(api.get("/context")).rejects.toMatchObject({ code: "NETWORK_ERROR", status: 0 });
  });
});
