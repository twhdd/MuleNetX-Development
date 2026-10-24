/** §19.12 lineage: snapshot, analytics run, scoring run, model and risk logic behind a value. */
import { GitCommitVertical } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import type { Lineage } from "../api/types";
import { dateTime } from "../lib/format";
import s from "./LineageBadge.module.css";

const FIELDS: [keyof Lineage, string][] = [
  ["graph_snapshot_id", "Graph snapshot"],
  ["analytics_run_id", "Analytics run"],
  ["scoring_run_id", "Scoring run"],
  ["model_version", "Model"],
  ["risk_logic_version", "Risk logic"],
];

export function LineageBadge({ lineage, computedAt, isStale }: { lineage: Lineage; computedAt?: string | null; isStale?: boolean }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);
  return (
    <div className={s.wrap} ref={ref}>
      <button
        type="button"
        className={`${s.badge} ${isStale ? s.stale : ""}`}
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
      >
        <GitCommitVertical size={13} aria-hidden />
        {isStale ? "Lineage · stale" : "Lineage"}
      </button>
      {open && (
        <div className={s.pop} id={id} role="dialog" aria-label="Lineage">
          <dl>
            {FIELDS.map(([key, label]) => (
              <div key={key} style={{ display: "contents" }}>
                <dt>{label}</dt>
                <dd>{lineage[key] ?? "—"}</dd>
              </div>
            ))}
            <dt>Computed</dt>
            <dd>{dateTime(computedAt)} UTC</dd>
          </dl>
        </div>
      )}
    </div>
  );
}
