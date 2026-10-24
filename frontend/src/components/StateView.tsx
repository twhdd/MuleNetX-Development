/** The §20.4 states. Every state is driven by API fields: `is_stale`, availability fields, status codes. */
import { AlertTriangle, CircleSlash, Clock, Lock, PlugZap, SearchX } from "lucide-react";
import type { ReactNode } from "react";
import { ApiError } from "../api/client";
import type { ApiResult } from "../lib/useApi";
import s from "./StateView.module.css";
import ui from "./ui.module.css";

export type UiState =
  | "LOADING"
  | "SUCCESS"
  | "EMPTY"
  | "ERROR"
  | "UNAUTHORIZED"
  | "UNAVAILABLE"
  | "STALE"
  | "QUEUED"
  | "RUNNING";

export function Skeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className={s.skeleton} aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className={s.bar} style={{ width: `${92 - ((i * 17) % 40)}%` }} />
      ))}
    </div>
  );
}

export function StaleBanner({ isStale }: { isStale: boolean | undefined }) {
  if (!isStale) return null;
  return (
    <div className={s.stale} role="status" data-state="STALE">
      <Clock size={14} aria-hidden />
      Stale: computed in an earlier analytical context. The active context has moved on.
    </div>
  );
}

export function Running({ label, queued }: { label: string; queued?: boolean }) {
  return (
    <span className={s.running} role="status" data-state={queued ? "QUEUED" : "RUNNING"}>
      <span className={s.pulse} aria-hidden />
      {label}
    </span>
  );
}

interface MessageProps {
  icon: ReactNode;
  title: string;
  children?: ReactNode;
  state: UiState;
  error?: Error | null;
  action?: ReactNode;
}

function Message({ icon, title, children, state, error, action }: MessageProps) {
  const requestId = error instanceof ApiError ? error.requestId : null;
  return (
    <div className={s.state} data-state={state} role={state === "ERROR" ? "alert" : "status"}>
      <h3>
        {icon}
        {title}
      </h3>
      {children && <p>{children}</p>}
      {requestId && <span className={s.meta}>request {requestId}</span>}
      {action}
    </div>
  );
}

interface Props<T> {
  result: ApiResult<T>;
  children: (data: T) => ReactNode;
  empty?: ReactNode;
  unavailable?: ReactNode;
  rows?: number;
}

export function StateView<T>({ result, children, empty, unavailable, rows }: Props<T>) {
  const { state, data, error, reload } = result;
  if (state === "LOADING") return <Skeleton rows={rows} />;
  if (state === "UNAUTHORIZED")
    return (
      <Message icon={<Lock size={16} aria-hidden />} title="Session expired" state="UNAUTHORIZED">
        Sign in again to continue.
      </Message>
    );
  if (state === "UNAVAILABLE")
    return (
      <Message icon={<PlugZap size={16} aria-hidden />} title="Unavailable" state="UNAVAILABLE" error={error}>
        {unavailable ?? error?.message ?? "This signal is not available for the current context."}
      </Message>
    );
  if (state === "ERROR") {
    const forbidden = error instanceof ApiError && error.status === 403;
    return (
      <Message
        icon={forbidden ? <CircleSlash size={16} aria-hidden /> : <AlertTriangle size={16} aria-hidden />}
        title={forbidden ? "Not permitted for your role" : "Could not load"}
        state="ERROR"
        error={error}
        action={
          forbidden ? undefined : (
            <button type="button" className={ui.button} onClick={reload}>
              Retry
            </button>
          )
        }
      >
        {error?.message}
      </Message>
    );
  }
  if (state === "EMPTY" || data === null)
    return (
      <Message icon={<SearchX size={16} aria-hidden />} title="Nothing here yet" state="EMPTY">
        {empty}
      </Message>
    );
  return <>{children(data)}</>;
}
