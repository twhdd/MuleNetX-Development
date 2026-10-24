/** The five composed components of the risk score (SRS §12.4) and their availability fields. */
import type { Assessment } from "../api/types";

export interface Component {
  key: "ml" | "graph" | "behavioral" | "rules" | "propagation";
  label: string;
  short: string;
  value: (a: Assessment) => number | null;
  evidence: "MODEL OUTPUT" | "ANALYTICAL SIGNAL";
}

export const COMPONENTS: Component[] = [
  { key: "ml", label: "ML model", short: "ML", value: (a) => a.ml_score ?? null, evidence: "MODEL OUTPUT" },
  { key: "graph", label: "Graph signal", short: "Graph", value: (a) => a.graph_signal_score, evidence: "ANALYTICAL SIGNAL" },
  { key: "behavioral", label: "Behavioural signal", short: "Behav.", value: (a) => a.behavioral_signal_score, evidence: "ANALYTICAL SIGNAL" },
  { key: "rules", label: "Rule signal", short: "Rules", value: (a) => a.rule_signal_score, evidence: "ANALYTICAL SIGNAL" },
  { key: "propagation", label: "Propagated risk", short: "Prop.", value: (a) => a.propagated_risk, evidence: "ANALYTICAL SIGNAL" },
];

export function availability(a: Assessment, key: Component["key"]): { available: boolean; reason: string | null } {
  const entry = (a.signal_availability as Record<string, { state?: string; reason?: string | null } | undefined>)[key];
  const state = entry?.state ?? "UNAVAILABLE";
  return { available: state === "AVAILABLE", reason: entry?.reason ?? (state === "AVAILABLE" ? null : state) };
}

export function componentValue(a: Assessment, c: Component): number | null {
  return availability(a, c.key).available ? c.value(a) : null;
}
