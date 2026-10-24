/** The seven evidence labels of SRS §20.5 (plus SYNTHETIC DATA, §20.6). */
import s from "./EvidenceLabel.module.css";

export const EVIDENCE_LABELS = [
  "FACT",
  "ANALYTICAL SIGNAL",
  "MODEL OUTPUT",
  "ANALYTICAL CANDIDATE",
  "HYPOTHETICAL SIMULATION",
  "INVESTIGATOR FINDING",
  "AI INTERPRETATION",
] as const;

export type EvidenceKind = (typeof EVIDENCE_LABELS)[number] | "SYNTHETIC DATA";

const TITLES: Record<EvidenceKind, string> = {
  FACT: "Recorded in the canonical dataset.",
  "ANALYTICAL SIGNAL": "Computed from the graph or transaction history; indicative, not proof.",
  "MODEL OUTPUT": "Produced by the trained model; probabilistic.",
  "ANALYTICAL CANDIDATE": "A grouping proposed by analytics for review.",
  "HYPOTHETICAL SIMULATION": "A what-if result. Nothing was changed.",
  "INVESTIGATOR FINDING": "Recorded by an investigator.",
  "AI INTERPRETATION": "Generated text; verify against the cited evidence.",
  "SYNTHETIC DATA": "Derived from a synthetic-injection dataset.",
};

export function EvidenceLabel({ kind }: { kind: EvidenceKind }) {
  return (
    <span className={`${s.label} ${s[kind.replaceAll(" ", "_")] ?? ""}`} title={TITLES[kind]} data-evidence={kind}>
      {kind}
    </span>
  );
}
