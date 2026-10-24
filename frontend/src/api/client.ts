/**
 * The only module that performs HTTP (SRS §20.2). Base path `/api/v1`, bearer token from the in-memory
 * session, `X-Request-ID` on every request, and the §19.3 error envelope parsed into `ApiError`.
 */
import { useSession } from "../state/session";
import type { ErrorEnvelope } from "./types";

export const BASE = "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;
  readonly details: Record<string, unknown>;

  constructor(status: number, code: string, message: string, requestId: string | null, details: Record<string, unknown>) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
    this.details = details;
  }
}

export type Query = Record<string, string | number | boolean | null | undefined>;

export interface RequestOptions {
  query?: Query;
  body?: unknown;
  form?: FormData;
  signal?: AbortSignal;
  /** Request without the session token (login). */
  anonymous?: boolean;
}

export function newRequestId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`;
}

export function buildUrl(path: string, query?: Query): string {
  const url = path.startsWith("/api/") || path === "/health" || path === "/ready" ? path : `${BASE}${path}`;
  if (!query) return url;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

async function parseError(resp: Response, requestId: string): Promise<ApiError> {
  let envelope: ErrorEnvelope | null = null;
  try {
    envelope = (await resp.json()) as ErrorEnvelope;
  } catch {
    envelope = null;
  }
  const body = envelope?.error;
  if (body && typeof body.code === "string") {
    return new ApiError(resp.status, body.code, body.message, body.request_id ?? requestId, body.details ?? {});
  }
  return new ApiError(resp.status, resp.status >= 500 ? "INTERNAL" : "HTTP_ERROR", resp.statusText || "Request failed", requestId, {});
}

export async function request<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
  const requestId = newRequestId();
  const headers: Record<string, string> = { "X-Request-ID": requestId, Accept: "application/json" };
  const token = useSession.getState().token;
  if (token && !options.anonymous) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (options.form) {
    body = options.form;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }
  let resp: Response;
  try {
    resp = await fetch(buildUrl(path, options.query), { method, headers, body, signal: options.signal });
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    throw new ApiError(0, "NETWORK_ERROR", "The server could not be reached.", requestId, {});
  }
  if (!resp.ok) {
    const error = await parseError(resp, requestId);
    if (error.status === 401 && token && !options.anonymous) useSession.getState().expire();
    throw error;
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export const api = {
  get: <T>(path: string, query?: Query, signal?: AbortSignal) => request<T>("GET", path, { query, signal }),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, { body }),
  patch: <T>(path: string, body: unknown) => request<T>("PATCH", path, { body }),
  del: <T = void>(path: string) => request<T>("DELETE", path),
};

export const enc = encodeURIComponent;
