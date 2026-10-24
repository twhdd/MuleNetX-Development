import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ApiError } from "../src/api/client";
import { EVIDENCE_LABELS, EvidenceLabel } from "../src/components/EvidenceLabel";
import { Running, StaleBanner, StateView } from "../src/components/StateView";
import { stateFromError, type ApiResult } from "../src/lib/useApi";

function result<T>(partial: Partial<ApiResult<T>>): ApiResult<T> {
  return { state: "SUCCESS", data: null, error: null, reload: () => {}, ...partial };
}

describe("StateView (SRS §20.4)", () => {
  it.each([
    ["EMPTY", { state: "EMPTY" as const }, "Nothing here yet"],
    ["UNAUTHORIZED", { state: "UNAUTHORIZED" as const }, "Session expired"],
    ["UNAVAILABLE", { state: "UNAVAILABLE" as const, error: new ApiError(503, "GRAPH_UNAVAILABLE", "The graph store is unavailable.", "r1", {}) }, "Unavailable"],
    ["ERROR", { state: "ERROR" as const, error: new ApiError(500, "INTERNAL", "Boom", "r2", {}) }, "Could not load"],
  ])("renders %s", (_name, partial, text) => {
    render(<StateView result={result<string>(partial)}>{(d) => d}</StateView>);
    expect(screen.getAllByText(text, { exact: false }).length).toBeGreaterThan(0);
  });

  it("renders LOADING as a busy skeleton", () => {
    render(<StateView result={result<string>({ state: "LOADING" })}>{(d) => d}</StateView>);
    expect(screen.getByLabelText("Loading")).toHaveAttribute("aria-busy", "true");
  });

  it("renders SUCCESS children and shows the request id on errors", () => {
    const { rerender } = render(<StateView result={result({ data: "payload" })}>{(d) => <p>{d}</p>}</StateView>);
    expect(screen.getByText("payload")).toBeInTheDocument();
    rerender(<StateView result={result<string>({ state: "ERROR", error: new ApiError(500, "INTERNAL", "Boom", "req-42", {}) })}>{(d) => d}</StateView>);
    expect(screen.getByText("request req-42")).toBeInTheDocument();
  });

  it("treats 403 as a role message without retry", () => {
    render(<StateView result={result<string>({ state: "ERROR", error: new ApiError(403, "FORBIDDEN", "Denied", null, {}) })}>{(d) => d}</StateView>);
    expect(screen.getByText("Not permitted for your role")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).toBeNull();
  });

  it("derives UNAVAILABLE only from 503 or availability codes", () => {
    expect(stateFromError(new ApiError(503, "DB_UNAVAILABLE", "x", null, {}))).toBe("UNAVAILABLE");
    expect(stateFromError(new ApiError(404, "RISK_NOT_AVAILABLE", "x", null, {}))).toBe("UNAVAILABLE");
    expect(stateFromError(new ApiError(404, "NOT_FOUND", "x", null, {}))).toBe("ERROR");
    expect(stateFromError(new ApiError(401, "UNAUTHENTICATED", "x", null, {}))).toBe("UNAUTHORIZED");
  });

  it("shows STALE only when is_stale is true, and QUEUED/RUNNING markers", () => {
    const { container, rerender } = render(<StaleBanner isStale={false} />);
    expect(container).toBeEmptyDOMElement();
    rerender(<StaleBanner isStale />);
    expect(screen.getByRole("status")).toHaveAttribute("data-state", "STALE");
    rerender(<Running label="Queued" queued />);
    expect(screen.getByRole("status")).toHaveAttribute("data-state", "QUEUED");
  });
});

describe("EvidenceLabel (SRS §20.5)", () => {
  it("renders all seven labels verbatim", () => {
    render(
      <>
        {EVIDENCE_LABELS.map((k) => (
          <EvidenceLabel key={k} kind={k} />
        ))}
      </>,
    );
    expect(EVIDENCE_LABELS).toHaveLength(7);
    for (const k of EVIDENCE_LABELS) expect(screen.getByText(k)).toHaveAttribute("data-evidence", k);
  });
});
