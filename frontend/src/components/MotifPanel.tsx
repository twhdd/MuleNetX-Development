/**
 * Temporal motifs (SRS §15.9, §20.6): type, participants, span, confidence with its three components, and
 * `order_ambiguous`. Confidence is a pattern-strength score, shown with its temporal component and never as risk.
 */
import { useState } from "react";
import type { Motif, MotifPage } from "../api/types";
import { dateTime, humanize, int } from "../lib/format";
import { useApi } from "../lib/useApi";
import { AccountLink, Paginator } from "./bits";
import { EvidenceLabel } from "./EvidenceLabel";
import { StaleBanner, StateView } from "./StateView";
import s from "./MotifPanel.module.css";
import ui from "./ui.module.css";

const TYPES = ["", "RAPID_PASS_THROUGH", "FAN_IN", "FAN_OUT", "CIRCULAR_FLOW", "LAYERED_MOVEMENT", "BURST_ACTIVITY"];

function span(m: Motif): string {
  const secs = (new Date(m.end_time).getTime() - new Date(m.start_time).getTime()) / 1000;
  if (secs === 0) return "same timestamp";
  if (secs < 3600) return `${Math.round(secs / 60)} min`;
  return `${(secs / 3600).toFixed(secs % 3600 ? 1 : 0)} h`;
}

function Component({ label, value }: { label: string; value: string | undefined }) {
  const v = Number(value ?? 0);
  return (
    <>
      <span>{label}</span>
      <span className={s.bar} aria-hidden>
        <span style={{ width: `${v * 100}%` }} />
      </span>
      <span className="num">{v.toFixed(3)}</span>
    </>
  );
}

export function MotifRow({ m }: { m: Motif }) {
  const c = m.confidence_components as Record<string, string>;
  const accounts = m.participating_account_ids;
  return (
    <article className={s.motif} aria-label={`${humanize(m.motif_type)} anchored at ${m.anchor_account_id}`}>
      <div className={s.type}>
        <strong>{humanize(m.motif_type)}</strong>
        <span className={s.meta}>
          {dateTime(m.start_time)} · {span(m)} · {int(m.transaction_count)} tx
        </span>
        <div className={s.flags}>
          {m.order_ambiguous && (
            <span className={ui.chip} title="Hops share a timestamp; the data cannot establish their true order.">
              order ambiguous
            </span>
          )}
          {m.truncated && <span className={ui.chip}>enumeration truncated</span>}
        </div>
      </div>
      <div className={s.chain}>
        <span className={s.meta}>anchor</span> <AccountLink id={m.anchor_account_id} />
        <span className={s.sep}>·</span>
        {accounts.slice(0, 8).map((a) => (
          <AccountLink key={a} id={a}>
            {a.split(":").pop()}
          </AccountLink>
        ))}
        {accounts.length > 8 && <span className={s.meta}>+{accounts.length - 8} more</span>}
      </div>
      <div className={s.conf} aria-label={`Pattern confidence ${m.motif_confidence.toFixed(3)}`}>
        <Component label="Structure" value={c.structural_match} />
        <Component label="Timing" value={c.temporal_match} />
        <Component label="Participants" value={c.participant_match} />
        <span>
          <b>Confidence</b>
        </span>
        <span />
        <span className="num">
          <b>{m.motif_confidence.toFixed(3)}</b>
        </span>
      </div>
    </article>
  );
}

export function MotifPanel({ load, deps }: { load: (q: { type?: string; page?: number }, signal: AbortSignal) => Promise<MotifPage>; deps: unknown[] }) {
  const [type, setType] = useState("");
  const [page, setPage] = useState(1);
  const result = useApi((sig) => load({ type: type || undefined, page }, sig), [...deps, type, page], (d) => d.items.length === 0);
  return (
    <section className={ui.panel}>
      <div className={ui.panelHead}>
        <h2 className={ui.panelTitle}>Temporal motifs</h2>
        <EvidenceLabel kind="ANALYTICAL SIGNAL" />
      </div>
      <div className={s.filters}>
        <label className={ui.field}>
          <span className={ui.label}>Type</span>
          <select className={ui.select} value={type} onChange={(e) => { setType(e.target.value); setPage(1); }}>
            {TYPES.map((t) => (
              <option key={t} value={t}>
                {t ? humanize(t) : "All types"}
              </option>
            ))}
          </select>
        </label>
      </div>
      <StateView result={result} rows={5} empty="No motif involves these accounts in this analytics run.">
        {(data) => (
          <>
            <StaleBanner isStale={data.is_stale} />
            <p className={s.note}>{data.interpretation} Most detected instances score between 0.67 and 1 by construction; compare timing, not confidence.</p>
            <div className={s.list}>
              {data.items.map((m) => (
                <MotifRow key={m.motif_id} m={m} />
              ))}
            </div>
            <Paginator page={data.page} pageSize={data.page_size} total={data.total} capped={data.total_is_capped} onPage={setPage} />
          </>
        )}
      </StateView>
    </section>
  );
}
