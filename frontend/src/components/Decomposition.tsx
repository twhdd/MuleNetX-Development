/** Score decomposition for one assessment: final score, coverage, components, rules and top SHAP. */
import type { Assessment, Shap } from "../api/types";
import { percent, score } from "../lib/format";
import { availability, COMPONENTS } from "../lib/signals";
import { ScoreBar, TierChip } from "./bits";
import { EvidenceLabel } from "./EvidenceLabel";
import { LineageBadge } from "./LineageBadge";
import s from "./Decomposition.module.css";
import { ShapBars } from "./ShapBars";
import { StaleBanner } from "./StateView";
import ui from "./ui.module.css";
import type { ReactNode } from "react";

interface Props {
  label: string;
  assessment: Assessment;
  shap: Shap | null;
  shapNote?: string | null;
  actions?: ReactNode;
  /** Embedded under a header that already shows identity, score and lineage. */
  compact?: boolean;
}

export function Decomposition({ label, assessment: a, shap, shapNote, actions, compact }: Props) {
  const firedRules = a.fired_rules as { rule_id?: string; name?: string }[];
  return (
    <div>
      <StaleBanner isStale={a.is_stale} />
      <div className={s.wrap}>
        <div className={s.head}>
          {!compact && (
            <>
              <div className={s.idline}>
                <span className={s.ref}>{label}</span>
                <LineageBadge lineage={a.lineage} computedAt={a.computed_at} isStale={a.is_stale} />
              </div>
              <div className={s.final}>
                <span className={s.big}>{score(a.final_score)}</span>
                <TierChip tier={a.risk_tier} />
              </div>
            </>
          )}
          <span className={s.coverage}>
            Signal coverage {percent(a.signal_coverage)} · maximum attainable {score(a.max_attainable_score)}
          </span>
          <p className={s.interp}>{a.interpretation}</p>
        </div>

        <section className={s.section}>
          <div className={s.sectionHead}>
            <h3>Components</h3>
            <EvidenceLabel kind="ANALYTICAL SIGNAL" />
          </div>
          {COMPONENTS.map((c) => {
            const av = availability(a, c.key);
            return (
              <div key={c.key} className={s.comp}>
                <span>{c.label}</span>
                {av.available ? <ScoreBar value={c.value(a)} label={c.label} /> : <span className={s.compNa}>Unavailable · {av.reason}</span>}
              </div>
            );
          })}
          <div className={s.comp}>
            <span>Before propagation</span>
            <ScoreBar value={a.pre_propagation_score} cap={a.max_attainable_score} label="Pre-propagation score" />
          </div>
        </section>

        {firedRules.length > 0 && (
          <section className={s.section}>
            <div className={s.sectionHead}>
              <h3>Rules fired</h3>
            </div>
            <div className={s.rules}>
              {firedRules.map((r, i) => (
                <span key={r.rule_id ?? i} className={ui.chip} title={r.name}>
                  {r.rule_id ?? "rule"} {r.name ? `· ${r.name}` : ""}
                </span>
              ))}
            </div>
          </section>
        )}

        <section className={s.section}>
          <div className={s.sectionHead}>
            <h3>Why the model scored it</h3>
            <EvidenceLabel kind="MODEL OUTPUT" />
          </div>
          {shap ? (
            <ShapBars contributions={shap.contributions} statement={shap.statement} />
          ) : (
            <p className={s.compNa}>{shapNote ?? "No model explanation for this assessment."}</p>
          )}
        </section>

        {actions && <div className={s.actions}>{actions}</div>}
      </div>
    </div>
  );
}
