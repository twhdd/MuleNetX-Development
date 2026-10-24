/**
 * Request lifecycle for one view. The resulting state is the §20.4 vocabulary and is derived only from
 * the response: 401 → UNAUTHORIZED, 503 or an availability error code → UNAVAILABLE, an empty page → EMPTY.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";

export type ViewState = "LOADING" | "SUCCESS" | "EMPTY" | "ERROR" | "UNAUTHORIZED" | "UNAVAILABLE";

/** Error codes that mean "the signal or resource is unavailable", not "the request failed". */
const UNAVAILABLE_CODES = new Set(["RISK_NOT_AVAILABLE", "EXPLANATION_NOT_AVAILABLE", "EVALUATION_NOT_AVAILABLE"]);

export function stateFromError(error: unknown): ViewState {
  if (error instanceof ApiError) {
    if (error.status === 401) return "UNAUTHORIZED";
    if (error.status === 503 || UNAVAILABLE_CODES.has(error.code)) return "UNAVAILABLE";
  }
  return "ERROR";
}

export interface ApiResult<T> {
  state: ViewState;
  data: T | null;
  error: ApiError | Error | null;
  reload: () => void;
}

export function useApi<T>(
  load: ((signal: AbortSignal) => Promise<T>) | null,
  deps: unknown[],
  isEmpty?: (data: T) => boolean,
): ApiResult<T> {
  const [state, setState] = useState<ViewState>("LOADING");
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [tick, setTick] = useState(0);
  const emptyRef = useRef(isEmpty);
  emptyRef.current = isEmpty;

  useEffect(() => {
    if (!load) return;
    const controller = new AbortController();
    setState("LOADING");
    setError(null);
    load(controller.signal).then(
      (result) => {
        if (controller.signal.aborted) return;
        setData(result);
        setState(emptyRef.current?.(result) ? "EMPTY" : "SUCCESS");
      },
      (err: unknown) => {
        if (controller.signal.aborted || (err as Error).name === "AbortError") return;
        setData(null);
        setError(err as Error);
        setState(stateFromError(err));
      },
    );
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick, load === null]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { state: load ? state : "EMPTY", data, error, reload };
}
