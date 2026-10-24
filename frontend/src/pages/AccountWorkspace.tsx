import { ArrowDownLeft, ArrowUpRight, FolderPlus, Network, Route } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { accountService } from "../api/accounts";
import { ApiError } from "../api/client";
import { communityService } from "../api/graph";
import { riskService } from "../api/risk";
import type { Assessment, FeatureValue, Shap, Transaction } from "../api/types";
import { motifService } from "../api/rings";
import { ActivityHeatmap } from "../components/ActivityHeatmap";
import { CopilotPanel } from "../components/CopilotPanel";
import { MotifPanel } from "../components/MotifPanel";
import { AccountLink, Paginator, ScoreBar, TierChip } from "../components/bits";
import { Decomposition } from "../components/Decomposition";
import { EvidenceLabel } from "../components/EvidenceLabel";
import { LineageBadge } from "../components/LineageBadge";
import { Skeleton, StaleBanner, StateView } from "../components/StateView";
import ui from "../components/ui.module.css";
import { amount, dateTime, humanize, int, score, shortId } from "../lib/format";
import { openCaseForAccount } from "../lib/openCase";
import { useApi } from "../lib/useApi";
import p from "./page.module.css";
import s from "./AccountWorkspace.module.css";

const TABS = [
  ["risk", "Risk"],
  ["transactions", "Transactions"],
  ["features", "Features"],
  ["temporal", "Temporal"],
  ["motifs", "Motifs"],
  ["community", "Community"],
  ["copilot", "Copilot"],
] as const;
type Tab = (typeof TABS)[number][0];

function FeatureTable({ features }: { features: FeatureValue[] }) {
  return (
    <div className={p.tableWrap}>
      <div className={ui.tableScroll}><table className={ui.table}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Feature</th>
            <th className={ui.right}>Value</th>
            <th>State</th>
            <th>Window</th>
            <th>Unit</th>
          </tr>
        </thead>
        <tbody>
          {features.map((f) => (
            <tr key={f.feature_id} title={f.description}>
              <td className="num">{f.feature_id}</td>
              <td style={{ whiteSpace: "normal" }}>{f.name}</td>
              <td className={`num ${ui.right}`}>{f.value === null ? "—" : Number.isInteger(f.value) ? int(f.value) : f.value.toFixed(4)}</td>
              <td>
                <span className={ui.chip} style={{ color: f.state === "UNAVAILABLE" ? "var(--text-3)" : f.state === "ZERO" ? "var(--text-2)" : "var(--text-1)" }}>
                  {f.state}
                </span>
              </td>
              <td className={p.muted}>{f.window ?? "—"}</td>
              <td className={p.muted}>{f.unit ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table></div>
    </div>
  );
}

function RiskTab({ id, label }: { id: string; label: string }) {
  const risk = useApi((sig) => riskService.risk(id, sig), [id]);
  const shap = useApi<Shap | null>(
    async (sig) => {
      try {
        return await riskService.shap(id, 12, sig);
      } catch (err) {
        if (err instanceof ApiError && [404, 409, 503].includes(err.status)) return null;
        throw err;
      }
    },
    [id],
  );
  const propagation = useApi((sig) => riskService.propagation(id, sig), [id], (d) => d.contributions.length === 0);
  const [historyPage, setHistoryPage] = useState(1);
  const history = useApi((sig) => riskService.history(id, historyPage, sig), [id, historyPage], (d) => d.items.length === 0);
  return (
    <div className={p.grid3}>
      <div className={ui.panel}>
        <StateView result={risk} rows={10} unavailable="No assessment exists for this account in the active scoring run.">
          {(a) => <Decomposition compact label={label} assessment={a} shap={shap.data} shapNote={a.ml_score === null ? "The ML component was unavailable for this assessment." : null} />}
        </StateView>
      </div>
      <div className={p.stack}>
        <section className={ui.panel}>
          <div className={ui.panelHead}>
            <h2 className={ui.panelTitle}>Propagated from</h2>
            <EvidenceLabel kind="ANALYTICAL SIGNAL" />
          </div>
          <StateView result={propagation} empty="No upstream risk reached this account within three hops.">
            {(prop) => (
              <>
                <StaleBanner isStale={prop.is_stale} />
                <div className={p.tableWrap}>
                  <div className={ui.tableScroll}><table className={ui.table}>
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Source</th>
                        <th className={ui.right}>Hops</th>
                        <th className={ui.right}>Source score</th>
                        <th className={ui.right}>Decay</th>
                        <th className={ui.right}>Contribution</th>
                      </tr>
                    </thead>
                    <tbody>
                      {prop.contributions.map((c) => (
                        <tr key={c.source_account_id}>
                          <td className="num">{c.rank}</td>
                          <td>
                            <AccountLink id={c.source_account_id} />
                          </td>
                          <td className={`num ${ui.right}`}>{c.distance}</td>
                          <td className={`num ${ui.right}`}>{score(c.source_score)}</td>
                          <td className={`num ${ui.right}`}>{score(c.decay_value)}</td>
                          <td className={`num ${ui.right}`}>{score(c.contribution, 4)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table></div>
                </div>
              </>
            )}
          </StateView>
        </section>
        <section className={ui.panel}>
          <div className={ui.panelHead}>
            <h2 className={ui.panelTitle}>Assessment history</h2>
          </div>
          <StateView result={history} empty="No earlier assessments.">
            {(page) => (
              <>
                <div className={ui.tableScroll}><table className={ui.table}>
                  <thead>
                    <tr>
                      <th>As of</th>
                      <th>Final</th>
                      <th>Tier</th>
                      <th>Model</th>
                    </tr>
                  </thead>
                  <tbody>
                    {page.items.map((h: Assessment) => (
                      <tr key={h.assessment_id}>
                        <td className="num">{dateTime(h.as_of)}</td>
                        <td style={{ width: 160 }}>
                          <ScoreBar value={h.final_score} />
                        </td>
                        <td>
                          <TierChip tier={h.risk_tier} />
                        </td>
                        <td className={`num ${p.muted}`}>{h.model_version ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table></div>
                <Paginator page={page.page} pageSize={page.page_size} total={page.total} capped={page.total_is_capped} onPage={setHistoryPage} />
              </>
            )}
          </StateView>
        </section>
      </div>
    </div>
  );
}

const MAX_HEATMAP_PAGES = 10;

function TransactionsTab({ id }: { id: string }) {
  const [direction, setDirection] = useState<"" | "in" | "out">("");
  const [type, setType] = useState("");
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [trail, setTrail] = useState<string[]>([]);
  const page = useApi(
    (sig) => accountService.transactions(id, { page_size: 50, cursor, direction: direction || undefined, type: type || undefined }, sig),
    [id, cursor, direction, type],
    (d) => d.items.length === 0,
  );
  const [activity, setActivity] = useState<{ tx: Transaction[]; start: string; end: string; capped: boolean } | null>(null);
  const [activityError, setActivityError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setActivity(null);
    setActivityError(null);
    (async () => {
      const tx: Transaction[] = [];
      let next: string | undefined;
      let range: { start: string | null; end: string | null } | null = null;
      for (let i = 0; i < MAX_HEATMAP_PAGES; i++) {
        const res = await accountService.transactions(id, { page_size: 100, cursor: next }, controller.signal);
        range = range ?? res.range ?? null;
        tx.push(...res.items);
        next = res.next_cursor ?? undefined;
        if (!next) break;
      }
      if (!controller.signal.aborted) setActivity({ tx, start: range?.start ?? tx[0]?.timestamp ?? new Date().toISOString(), end: range?.end ?? tx.at(-1)?.timestamp ?? new Date().toISOString(), capped: next !== undefined });
    })().catch((err: Error) => {
      if (!controller.signal.aborted && err.name !== "AbortError") setActivityError(err.message);
    });
    return () => controller.abort();
  }, [id]);

  return (
    <div className={p.stack}>
      <section className={ui.panel}>
        <div className={ui.panelHead}>
          <h2 className={ui.panelTitle}>Activity by hour</h2>
          <EvidenceLabel kind="FACT" />
        </div>
        <div className={ui.panelBody}>
          {activityError ? <p className={ui.error}>{activityError}</p> : activity ? activity.tx.length ? <ActivityHeatmap transactions={activity.tx} start={activity.start} end={activity.end} capped={activity.capped} /> : <p className={p.muted}>No transactions in the window.</p> : <Skeleton rows={5} />}
        </div>
      </section>
      <section className={ui.panel}>
        <div className={ui.panelHead}>
          <h2 className={ui.panelTitle}>Transactions</h2>
          <div className={s.window}>
            <select className={ui.select} aria-label="Direction" value={direction} onChange={(e) => { setDirection(e.target.value as "" | "in" | "out"); setCursor(undefined); setTrail([]); }}>
              <option value="">Both directions</option>
              <option value="in">Incoming</option>
              <option value="out">Outgoing</option>
            </select>
            <select className={ui.select} aria-label="Type" value={type} onChange={(e) => { setType(e.target.value); setCursor(undefined); setTrail([]); }}>
              <option value="">All types</option>
              {["PAYMENT", "TRANSFER", "CASH_OUT", "CASH_IN", "DEBIT"].map((t) => (
                <option key={t} value={t}>
                  {humanize(t)}
                </option>
              ))}
            </select>
          </div>
        </div>
        <StateView result={page} rows={8} empty="No transactions match in the most recent 31 days of activity.">
          {(data) => (
            <>
              <div className={p.tableWrap}>
                <div className={ui.tableScroll}><table className={ui.table}>
                  <thead>
                    <tr>
                      <th>Time (UTC)</th>
                      <th>Dir.</th>
                      <th>Type</th>
                      <th>Counterparty</th>
                      <th className={ui.right}>Amount</th>
                      <th>Label</th>
                      <th>Transaction</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((t) => {
                      const other = t.direction === "in" ? t.source_account_id : t.destination_account_id;
                      return (
                        <tr key={t.transaction_id}>
                          <td className="num">{dateTime(t.timestamp)}</td>
                          <td>
                            <span className={`${s.dir} ${t.direction === "in" ? s.in : s.out}`}>
                              {t.direction === "in" ? <ArrowDownLeft size={13} aria-hidden /> : <ArrowUpRight size={13} aria-hidden />}
                              {t.direction === "in" ? "IN" : "OUT"}
                            </span>
                          </td>
                          <td>{humanize(t.transaction_type)}</td>
                          <td>{other === id ? <span className={p.muted}>self</span> : <AccountLink id={other} />}</td>
                          <td className={`num ${ui.right}`} title={t.amount}>
                            {amount(t.amount)}
                          </td>
                          <td>{t.fraud_label ? <span className={ui.chip} style={{ color: "var(--danger)" }} title="Dataset label (FACT)">labelled fraud</span> : <span className={p.muted}>—</span>}</td>
                          <td className={`num ${p.muted}`}>{t.transaction_id}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table></div>
              </div>
              <div className={ui.panelHead} style={{ borderTop: "1px solid var(--line)", borderBottom: 0 }}>
                <span className={`${p.muted} ${p.small}`}>
                  Window {dateTime(data.range?.start)} – {dateTime(data.range?.end)}
                </span>
                <div className={p.row}>
                  <button type="button" className={`${ui.button} ${ui.small}`} disabled={trail.length === 0} onClick={() => { const prev = [...trail]; const c = prev.pop(); setTrail(prev); setCursor(c === "" ? undefined : c); }}>
                    Newer
                  </button>
                  <button type="button" className={`${ui.button} ${ui.small}`} disabled={!data.next_cursor} onClick={() => { setTrail([...trail, cursor ?? ""]); setCursor(data.next_cursor ?? undefined); }}>
                    Older
                  </button>
                </div>
              </div>
            </>
          )}
        </StateView>
      </section>
    </div>
  );
}

function FeaturesTab({ id }: { id: string }) {
  const result = useApi((sig) => accountService.features(id, sig), [id]);
  return (
    <section className={ui.panel}>
      <StateView result={result} rows={12} unavailable="No feature snapshot backs an assessment of this account.">
        {(f) => (
          <>
            <StaleBanner isStale={f.is_stale} />
            <div className={ui.panelHead}>
              <h2 className={ui.panelTitle}>
                Feature vector {f.feature_version} <span className={`${p.muted} ${p.small}`}>as of {dateTime(f.as_of)} UTC</span>
              </h2>
              <div className={p.row}>
                <EvidenceLabel kind="ANALYTICAL SIGNAL" />
                <LineageBadge lineage={f.lineage} computedAt={f.computed_at} isStale={f.is_stale} />
              </div>
            </div>
            <FeatureTable features={f.features} />
          </>
        )}
      </StateView>
    </section>
  );
}

function TemporalTab({ id }: { id: string }) {
  const result = useApi((sig) => accountService.temporal(id, sig), [id]);
  return (
    <section className={ui.panel}>
      <StateView result={result} rows={8}>
        {(t) => (
          <>
            <StaleBanner isStale={t.is_stale} />
            <div className={ui.panelHead}>
              <h2 className={ui.panelTitle}>
                Temporal features <span className={`${p.muted} ${p.small}`}>cutoff {dateTime(t.cutoff)} UTC</span>
              </h2>
              <EvidenceLabel kind="ANALYTICAL SIGNAL" />
            </div>
            <FeatureTable features={t.features} />
          </>
        )}
      </StateView>
    </section>
  );
}

function CommunityTab({ id }: { id: string }) {
  const [page, setPage] = useState(1);
  const result = useApi((sig) => communityService.ofAccount(id, page, sig), [id, page]);
  return (
    <section className={ui.panel}>
      <StateView result={result} rows={8} empty="This account belongs to no community in the active analytics run.">
        {(c) => (
          <>
            <StaleBanner isStale={c.is_stale} />
            <div className={ui.panelHead}>
              <h2 className={ui.panelTitle}>
                Community <span className="num">{shortId(c.community_id)}</span> · {int(c.member_count)} members
              </h2>
              <div className={p.row}>
                <EvidenceLabel kind="ANALYTICAL SIGNAL" />
                <Link to={`/communities/${c.community_id}`} className={`${ui.button} ${ui.small}`}>
                  Open community
                </Link>
              </div>
            </div>
            <div className={ui.panelBody}>
              <p className={`${p.muted} ${p.small}`}>
                {c.interpretation} {c.algorithm} {c.algorithm_version}.
              </p>
            </div>
            <div className={ui.tableScroll}><table className={ui.table}>
              <thead>
                <tr>
                  <th>Member</th>
                  <th>Type</th>
                  <th>Tier</th>
                  <th style={{ width: 200 }}>Score</th>
                </tr>
              </thead>
              <tbody>
                {c.members.items.map((m) => (
                  <tr key={m.account_id} aria-current={m.account_id === id ? "true" : undefined}>
                    <td>
                      <AccountLink id={m.account_id}>{m.source_account_ref ?? m.account_id}</AccountLink>
                      {m.account_id === id && <span className={`${p.muted} ${p.small}`}> (this account)</span>}
                    </td>
                    <td>{m.account_type ?? "—"}</td>
                    <td>
                      <TierChip tier={m.risk_tier} />
                    </td>
                    <td>
                      <ScoreBar value={m.risk_score} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table></div>
            <Paginator page={c.members.page} pageSize={c.members.page_size} total={c.members.total} capped={c.members.total_is_capped} onPage={setPage} />
          </>
        )}
      </StateView>
    </section>
  );
}

export function AccountWorkspace() {
  const { id = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const tab = (params.get("tab") as Tab) ?? "risk";
  const navigate = useNavigate();
  const account = useApi((sig) => accountService.get(id, sig), [id]);
  const [opening, setOpening] = useState(false);
  const [openError, setOpenError] = useState<string | null>(null);

  const openCase = async () => {
    if (!account.data) return;
    setOpening(true);
    setOpenError(null);
    try {
      navigate(`/cases/${await openCaseForAccount(account.data.account_id, account.data.source_account_ref, account.data.risk_tier)}`);
    } catch (err) {
      setOpenError((err as Error).message);
      setOpening(false);
    }
  };

  return (
    <div className={p.page}>
      <StateView result={account} rows={4}>
        {(a) => (
          <>
            <StaleBanner isStale={a.is_stale} />
            <header className={s.head}>
              <div className={s.ident}>
                <h1 className={s.ref}>{a.source_account_ref}</h1>
                <div className={s.facts}>
                  <span className="num">{a.account_id}</span>
                  <span>{a.account_type}</span>
                  <span>
                    Dataset <span className="num">{a.dataset_key ?? shortId(a.dataset_id)}</span>
                  </span>
                  <LineageBadge lineage={a.lineage} computedAt={a.computed_at} isStale={a.is_stale} />
                </div>
              </div>
              <div className={s.score}>
                <span className={s.bigScore}>{score(a.risk_score)}</span>
                <TierChip tier={a.risk_tier} />
              </div>
              <div className={s.actions}>
                <Link className={ui.button} to={`/graph?account=${encodeURIComponent(a.account_id)}`}>
                  <Network size={15} aria-hidden />
                  Explore graph
                </Link>
                <Link className={ui.button} to={`/paths?from=${encodeURIComponent(a.account_id)}`}>
                  <Route size={15} aria-hidden />
                  Trace money
                </Link>
                <button type="button" className={`${ui.button} ${ui.primary}`} onClick={openCase} disabled={opening}>
                  <FolderPlus size={15} aria-hidden />
                  {opening ? "Opening…" : "Open case"}
                </button>
                {openError && <span className={ui.error}>{openError}</span>}
              </div>
            </header>
            <div className={`${ui.tabs} ${s.tabs}`} role="tablist" aria-label="Account sections">
              {TABS.map(([key, label]) => (
                <button key={key} type="button" role="tab" className={ui.tab} aria-selected={tab === key} onClick={() => setParams({ tab: key }, { replace: true })}>
                  {label}
                </button>
              ))}
            </div>
            <div className={s.content} role="tabpanel">
              {tab === "risk" && <RiskTab id={a.account_id} label={a.source_account_ref} />}
              {tab === "transactions" && <TransactionsTab id={a.account_id} />}
              {tab === "features" && <FeaturesTab id={a.account_id} />}
              {tab === "temporal" && <TemporalTab id={a.account_id} />}
              {tab === "community" && <CommunityTab id={a.account_id} />}
              {tab === "copilot" && <CopilotPanel scope={{ account_id: a.account_id }} kind="account" />}
              {tab === "motifs" && <MotifPanel load={(q, sig) => motifService.ofAccount(a.account_id, q, sig)} deps={[a.account_id]} />}
            </div>
          </>
        )}
      </StateView>
    </div>
  );
}
