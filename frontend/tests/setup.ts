import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";
import { useSession } from "../src/state/session";
import { useActiveContext } from "../src/state/context";
import { useUi } from "../src/state/ui";
import { server } from "./server";

beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
  // jsdom's AbortSignal is not the one Node's fetch accepts; the app still checks `signal.aborted` itself
  const intercepted = globalThis.fetch;
  globalThis.fetch = (input: RequestInfo | URL, init?: RequestInit) => intercepted(input, init ? { ...init, signal: undefined } : init);
});
afterEach(() => {
  cleanup();
  server.resetHandlers();
  useSession.getState().signOut();
  useActiveContext.getState().reset();
  useUi.setState({ triageAccount: null, explorerAccount: null });
});
afterAll(() => server.close());

// jsdom lacks these browser APIs used by layout code
if (!("ResizeObserver" in globalThis)) {
  (globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
