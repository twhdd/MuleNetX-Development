import { CheckCheck, CircleSlash, FlaskConical, RotateCcw } from "lucide-react";
import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { ringService, type RingStatus } from "../api/rings";
import type { Ring } from "../api/types";
import { AccountLink, Paginator, ScoreBar, TierChip } from "../components/bits";
import { EvidenceLabel } from "../components/EvidenceLabel";
import { LineageBadge } from "../components/LineageBadge";
import { CopilotPanel } from "../components/CopilotPanel";
import { MotifPanel } from "../components/MotifPanel";
import { StaleBanner, StateView } from "../components/StateView";
import ui from "../components/ui.module.css";
import { amount, dateTime, humanize, int, shortId } from "../lib/format";
import { useApi } from "../lib/useApi";
import { useSession } from "../state/session";
import ws from "./AccountWorkspace.module.css";
import p from "./page.module.css";
import { ClassChip, RingStatusChip } from "./Rings";

const FEATURE_LABEL: Record<string, string> = {
  RSD: "Suspicious transaction density",
  RC: "Risk concentration (top 3)",
  TC: "Temporal coordination",
  MFC: "Money-flow concentration (top 3 paths)",
  CS: "Centrality",
  FI: "Fan-in",
  FO: "Fan-out",
  CP: "Cycle present",
  SPD: "Suspicious path density",
};
const SIGNAL_LABEL: Record<string, string> = {
  H: "Suspicious members",
  D: "Suspicious internal amount",
  C: "Peak centrality",
  community_temporal_density: "Temporal density",
  M: "Outflow on qualifying paths",
};

function availabilityText(a: string | null | undefined) {
  if (!a || a === "AVAILABLE") return null;
  return a === "LOWER_BOUND_TRUNCATED" ? "lower bound (path enumeration truncated)" : "unavailable";
}

function Overview({ ring }: { ring: Ring }) {
  const potential = ring.candidate_class === "POTENTIAL_FRAUD_RING_CANDIDATE";
  const risk = useApi(potential ? (sig) => ringService.risk(ring.ring_id, sig) : null, [ring.ring_id]);
  const features = useApi(potential ? (sig) => ringService.features(ring.ring_id, sig) : null, [ring.ring_id]);
  const signals = ring.signal_summary as Record<string, { value: string; available: boolean; weight: string } | unknown>;
  return (
    <div className={p.grid2}>
      <section className={ui.panel}>
        <div className={ui.panelHead}>
          <h2 className={ui.panelTitle}>Why this community was flagged</h2>
          <EvidenceLabel kind="ANALYTICAL SIGNAL" />
        </div>
        <div className={ui.panelBody}>
          <div className={p.stack}>
            {Object.keys(SIGNAL_LABEL).map((k) => {
              const sig = signals[k] as { value: string; available: boolean; weight: string } | undefined;
              return (
                <div key={k} className={p.spread} style={{ gap: "var(--sp-4)" }}>
                  <span style={{ minWidth: 190 }}>
                    {SIGNAL_LABEL[k]} <span className={`${p.muted} ${p.small}`}>× {sig?.weight}</span>
                  </span>
                  <div style={{ flex: 1 }}>{sig?.available === false ? <span className={p.muted}>unavailable</span> : <ScoreBar value={Number(sig?.value ?? 0)} />}</div>
                </div>
              );
            })}
            <p className={`${p.muted} ${p.small}`}>{String(signals.formula ?? "")}</p>
          </div>
        </div>
      </section>
      {potential ? (
        <section className={ui.panel}>
          <div className={ui.panelHead}>
            <h2 className={ui.panelTitle}>Ring risk assessment</h2>
            <EvidenceLabel kind="ANALYTICAL SIGNAL" />
          </div>
          <StateView result={risk} rows={6}>
            {(r) => (
              <div className={ui.panelBody}>
                <div className={p.stack}>
                  <div className={p.row}>
                    <span className="num" style={{ fontSize: "var(--fs-3xl)", fontWeight: 600 }}>
                      {r.ring_risk_score.toFixed(3)}
                    </span>
                    <TierChip tier={r.risk_tier} />
                  </div>
                  {r.components.map((c) => (
                    <div key={c.component} className={p.spread} style={{ gap: "var(--sp-4)" }}>
                      <span style={{ minWidth: 190 }}>
                        {humanize(c.component)} <span className={`${p.muted} ${p.small}`}>× {c.weight.toFixed(2)}</span>
                      </span>
                      <div style={{ flex: 1 }}>
                        <ScoreBar value={c.value} />
                        {availabilityText(c.availability) && <span className={`${p.muted} ${p.small}`}>{availabilityText(c.availability)}</span>}
                      </div>
                    </div>
                  ))}
                  <p className={`${p.muted} ${p.small}`}>{r.interpretation}</p>
                </div>
              </div>
            )}
          </StateView>
        </section>
      ) : (
        <section className={ui.panel}>
          <div className={ui.panelBody}>
            <p className={p.muted}>Ring intelligence (features, ring risk, evidence) is computed for potential fraud ring candidates only. This suspicious community scored between 0.50 and 0.70.</p>
          </div>
        </section>
      )}
      {potential && (
        <section className={ui.panel} style={{ gridColumn: "1 / -1" }}>
          <div className={ui.panelHead}>
            <h2 className={ui.panelTitle}>Ring features</h2>
            <EvidenceLabel kind="ANALYTICAL SIGNAL" />
          </div>
          <StateView result={features} rows={6}>
            {(f) => (
              <>
                {f.paths_truncated && <div className={ui.notice}>Path enumeration reached its analytical bound; path-based features are lower bounds.</div>}
                <div className={ui.tableScroll}><table className={ui.table}>
                  <thead>
                    <tr>
                      <th>Feature</th>
                      <th style={{ width: 260 }}>Value</th>
                      <th>Availability</th>
                    </tr>
                  </thead>
                  <tbody>
                    {f.features.map((x) => (
                      <tr key={x.feature}>
                        <td>
                          <span className="num">{x.feature}</span> {FEATURE_LABEL[x.feature]}
                        </td>
                        <td>
                          <ScoreBar value={x.value} />
                        </td>
                        <td className={p.muted}>{availabilityText(x.availability) ?? "available"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table></div>
                <div className={ui.panelBody}>
                  <span className={`${p.muted} ${p.small}`}>
                    {int(f.qualifying_path_count)} qualifying of {int(f.eligible_path_count)} eligible paths in ring scope · span {int(f.temporal_span_seconds)} s
                  </span>
                </div>
              </>
            )}
          </StateView>
        </section>
      )}
    </div>
  );
}

function Members({ ring }: { ring: Ring }) {
  const [page, setPage] = useState(1);
  const result = useApi((sig) => ringService.accounts(ring.ring_id, page, sig), [ring.ring_id, page]);
  return (
    <section className={ui.panel}>
      <StateView result={result} rows={6}>
        {(data) => (
          <>
            <div className={ui.tableScroll}><table className={ui.table}>
              <thead>
                <tr>
                  <th>Member</th>
                  <th>Type</th>
                  <th>Tier</th>
                  <th style={{ width: 220 }}>Final score</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((m) => (
                  <tr key={m.account_id}>
                    <td>
                      <AccountLink id={m.account_id}>{m.source_account_ref ?? m.account_id}</AccountLink>
                    </td>
                    <td>{m.account_type ?? "—"}</td>
                    <td>
                      <TierChip tier={m.risk_tier} />
                    </td>
                    <td>
                      <ScoreBar value={m.final_score} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table></div>
            <Paginator page={data.page} pageSize={data.page_size} total={data.total} capped={data.total_is_capped} onPage={setPage} />
          </>
        )}
      </StateView>
    </section>
  );
}

function Transactions({ ring }: { ring: Ring }) {
  const [cursor, setCursor] = useState<string | undefined>();
  const [trail, setTrail] = useState<(string | undefined)[]>([]);
  const result = useApi((sig) => ringService.transactions(ring.ring_id, cursor, sig), [ring.ring_id, cursor], (d) => d.items.length === 0);
  return (
    <section className={ui.panel}>
      <div className={ui.panelHead}>
        <h2 className={ui.panelTitle}>Constituent transactions</h2>
        <EvidenceLabel kind="FACT" />
      </div>
      <StateView result={result} rows={6} empty="No transaction runs between two members of this ring.">
        {(data) => (
          <>
            <div className={ui.tableScroll}><table className={ui.table}>
              <thead>
                <tr>
                  <th>Time (UTC)</th>
                  <th>From</th>
                  <th>To</th>
                  <th>Type</th>
                  <th className={ui.right}>Amount</th>
                  <th>Transaction</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((t) => (
                  <tr key={t.transaction_id}>
                    <td className="num">{dateTime(t.timestamp)}</td>
                    <td>
                      <AccountLink id={t.source_account_id} />
                    </td>
                    <td>
                      <AccountLink id={t.destination_account_id} />
                    </td>
                    <td>{humanize(t.transaction_type)}</td>
                    <td className={`num ${ui.right}`}>{amount(t.amount)}</td>
                    <td className={`num ${p.muted}`}>{t.transaction_id}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
            <div className={ui.panelHead} style={{ borderTop: "1px solid var(--line)", borderBottom: 0 }}>
              <span />
              <div className={p.row}>
                <button type="button" className={`${ui.button} ${ui.small}`} disabled={trail.length === 0} onClick={() => { const prev = [...trail]; setCursor(prev.pop()); setTrail(prev); }}>
                  Earlier
                </button>
                <button type="button" className={`${ui.button} ${ui.small}`} disabled={!data.next_cursor} onClick={() => { setTrail([...trail, cursor]); setCursor(data.next_cursor ?? undefined); }}>
                  Later
                </button>
              </div>
            </div>
          </>
        )}
      </StateView>
    </section>
  );
}

type Item = Record<string, unknown>;

function EvidenceItems({ section, items }: { section: string; items: Item[] }) {
  if (section === "paths")
    return (
      <div className={ui.tableScroll}><table className={ui.table}>
        <thead>
          <tr>
            <th>Path</th>
            <th className={ui.right}>Hops</th>
            <th className={ui.right}>Suspicious flow</th>
            <th>Path ID</th>
          </tr>
        </thead>
        <tbody>
          {items.map((x) => (
            <tr key={String(x.path_id)}>
              <td style={{ whiteSpace: "normal" }}>
                {(x.accounts as string[]).map((a, i) => (
                  <span key={a}>
                    {i > 0 && <span className={p.muted}> → </span>}
                    <AccountLink id={a}>{a.split(":").pop()}</AccountLink>
                  </span>
                ))}
              </td>
              <td className={`num ${ui.right}`}>{String(x.path_length)}</td>
              <td className={`num ${ui.right}`}>{amount(String(x.suspicious_flow))}</td>
              <td className={`num ${p.muted}`}>{shortId(String(x.path_id))}</td>
            </tr>
          ))}
        </tbody>
      </table></div>
    );
  if (section === "relationships")
    return (
      <div className={ui.tableScroll}><table className={ui.table}>
        <thead>
          <tr>
            <th>From</th>
            <th>To</th>
            <th className={ui.right}>Transactions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((x) => (
            <tr key={`${x.source_account_id}>${x.destination_account_id}`}>
              <td>
                <AccountLink id={String(x.source_account_id)} />
              </td>
              <td>
                <AccountLink id={String(x.destination_account_id)} />
              </td>
              <td className={`num ${ui.right}`}>{(x.transaction_ids as string[]).length}</td>
            </tr>
          ))}
        </tbody>
      </table></div>
    );
  return (
    <pre className={p.small} style={{ margin: 0, padding: "var(--sp-3) var(--sp-4)", fontFamily: "var(--font-data)", whiteSpace: "pre-wrap", overflowWrap: "anywhere", color: "var(--text-2)" }}>
      {items.map((item) => JSON.stringify(item)).join("\n")}
    </pre>
  );
}

function Evidence({ ring }: { ring: Ring }) {
  const [section, setSection] = useState("paths");
  const [page, setPage] = useState(1);
  const result = useApi((sig) => ringService.evidence(ring.ring_id, section, page, sig), [ring.ring_id, section, page]);
  return (
    <section className={ui.panel}>
      <div className={ui.panelHead}>
        <div className={ui.tabs} role="tablist" aria-label="Evidence sections" style={{ border: 0 }}>
          {["paths", "relationships", "motifs", "accounts", "transactions"].map((x) => (
            <button key={x} type="button" role="tab" className={ui.tab} aria-selected={section === x} onClick={() => { setSection(x); setPage(1); }}>
              {humanize(x)}
            </button>
          ))}
        </div>
        <EvidenceLabel kind="ANALYTICAL SIGNAL" />
      </div>
      <StateView result={result} rows={6}>
        {(ev) => {
          const sec = ev.sections[section];
          return (
            <>
              <div className={ui.panelBody}>
                <p className={`${p.muted} ${p.small}`}>{ev.statement}</p>
              </div>
              {sec && sec.items.length > 0 ? (
                <EvidenceItems section={section} items={sec.items} />
              ) : (
                <div className={ui.panelBody}>
                  <span className={p.muted}>Nothing in this section.</span>
                </div>
              )}
              {sec && <Paginator page={sec.page} pageSize={sec.page_size} total={sec.total} capped={sec.total_is_capped} onPage={setPage} />}
            </>
          );
        }}
      </StateView>
    </section>
  );
}

const TABS = ["overview", "members", "transactions", "motifs", "evidence", "copilot"] as const;

export function RingWorkspace() {
  const { id = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const role = useSession((st) => st.user?.role);
  const result = useApi((sig) => ringService.get(id, sig), [id]);
  const [override, setOverride] = useState<Ring | null>(null);
  const [error, setError] = useState<string | null>(null);
  const tab = (params.get("tab") as (typeof TABS)[number]) ?? "overview";
  const canReview = role === "ADMIN" || role === "INVESTIGATOR";

  const setStatus = async (status: RingStatus) => {
    setError(null);
    try {
      setOverride(await ringService.setStatus(id, status));
    } catch (err) {
      setError(err instanceof ApiError && err.status === 403 ? "Your role cannot review rings." : (err as Error).message);
    }
  };

  return (
    <div className={p.page}>
      <StateView result={result} rows={6}>
        {(fetched) => {
          const ring = override ?? fetched;
          const potential = ring.candidate_class === "POTENTIAL_FRAUD_RING_CANDIDATE";
          const tabs = TABS.filter((t) => potential || t !== "evidence");
          return (
            <>
              <StaleBanner isStale={ring.is_stale} />
              <header className={ws.head}>
                <div className={ws.ident}>
                  <h1 className={ws.ref}>Ring {shortId(ring.ring_id)}</h1>
                  <div className={ws.facts}>
                    <ClassChip ring={ring} />
                    <RingStatusChip status={ring.candidate_status} />
                    <span>
                      Community <span className="num">{shortId(ring.community_id)}</span>
                    </span>
                    <span>
                      {int(ring.member_count)} members · {int(ring.transaction_count)} internal transactions
                      {ring.start_time && ` · ${dateTime(ring.start_time)} – ${dateTime(ring.end_time)}`}
                    </span>
                    <LineageBadge lineage={ring.lineage} computedAt={ring.computed_at} isStale={ring.is_stale} />
                    <EvidenceLabel kind="ANALYTICAL CANDIDATE" />
                  </div>
                </div>
                <div className={ws.score}>
                  <span className={ws.bigScore}>{ring.candidate_score.toFixed(3)}</span>
                  <span className={`${p.muted} ${p.small}`}>candidate score</span>
                </div>
                {potential && (
                  <div className={ws.actions}>
                    <Link to={`/rings/${ring.ring_id}/simulate`} className={ui.button}>
                      <FlaskConical size={15} aria-hidden />
                      Simulate disruption
                    </Link>
                  </div>
                )}
                {canReview && (
                  <div className={ws.actions} role="group" aria-label="Review status">
                    {ring.candidate_status !== "REVIEWED" && (
                      <button type="button" className={`${ui.button} ${ui.primary}`} onClick={() => void setStatus("REVIEWED")}>
                        <CheckCheck size={15} aria-hidden />
                        Mark reviewed
                      </button>
                    )}
                    {ring.candidate_status !== "DISMISSED" ? (
                      <button type="button" className={ui.button} onClick={() => void setStatus("DISMISSED")}>
                        <CircleSlash size={15} aria-hidden />
                        Dismiss
                      </button>
                    ) : (
                      <span className={`${p.muted} ${p.small}`}>
                        <RotateCcw size={12} aria-hidden /> Dismissed; mark reviewed to restore
                      </span>
                    )}
                    {error && <span className={ui.error} role="alert">{error}</span>}
                  </div>
                )}
              </header>
              <div className={`${ui.tabs} ${ws.tabs}`} role="tablist" aria-label="Ring sections">
                {tabs.map((t) => (
                  <button key={t} type="button" role="tab" className={ui.tab} aria-selected={tab === t} onClick={() => setParams({ tab: t }, { replace: true })}>
                    {humanize(t)}
                  </button>
                ))}
              </div>
              <div className={ws.content} role="tabpanel">
                <p className={`${p.muted} ${p.small}`} style={{ marginBottom: "var(--sp-3)", maxWidth: "90ch" }}>
                  {ring.interpretation}
                </p>
                {tab === "overview" && <Overview ring={ring} />}
                {tab === "members" && <Members ring={ring} />}
                {tab === "transactions" && <Transactions ring={ring} />}
                {tab === "motifs" && <MotifPanel load={(q, sig) => ringService.motifs(ring.ring_id, q, sig)} deps={[ring.ring_id]} />}
                {tab === "evidence" && potential && <Evidence ring={ring} />}
                {tab === "copilot" && <CopilotPanel scope={{ ring_id: ring.ring_id }} kind="ring" />}
                {tab === "evidence" && !potential && <Link to={`/rings/${ring.ring_id}`}>Back to overview</Link>}
              </div>
            </>
          );
        }}
      </StateView>
    </div>
  );
}
