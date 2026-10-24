import { ChevronDown, ChevronUp, Info } from "lucide-react";
import { Fragment, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { graphService } from "../api/graph";
import type { Path, PathQuery } from "../api/types";
import { PageHeader, Paginator } from "../components/bits";
import { EvidenceLabel } from "../components/EvidenceLabel";
import { LineageBadge } from "../components/LineageBadge";
import { StaleBanner, StateView } from "../components/StateView";
import ui from "../components/ui.module.css";
import { amount, dateTime, humanize, int, shortId } from "../lib/format";
import { useApi } from "../lib/useApi";
import p from "./page.module.css";
import s from "./PathView.module.css";

function Evidence({ path, snapshotId }: { path: Path; snapshotId: string }) {
  const [page, setPage] = useState(1);
  const detail = useApi((sig) => graphService.pathById(path.path_id, snapshotId, path.accounts, page, sig), [path.path_id, snapshotId, page]);
  return (
    <div className={s.evidence}>
      <StateView result={detail} rows={4}>
        {(d) => (
          <>
            {d.hops.map((h) => (
              <Fragment key={`${h.source_account_id}>${h.destination_account_id}`}>
                <h3>
                  {h.source_account_id} → {h.destination_account_id} · {int(h.transactions_total)} supporting transactions
                </h3>
                <div className={p.tableWrap}>
                  <div className={ui.tableScroll}><table className={ui.table}>
                    <thead>
                      <tr>
                        <th>Time (UTC)</th>
                        <th>Type</th>
                        <th className={ui.right}>Amount</th>
                        <th>Transaction</th>
                      </tr>
                    </thead>
                    <tbody>
                      {h.transactions.map((t, i) => (
                        <tr key={t}>
                          <td className="num">{dateTime(h.timestamps[i])}</td>
                          <td>{humanize(h.transaction_types[i])}</td>
                          <td className={`num ${ui.right}`}>{amount(h.amounts[i])}</td>
                          <td className={`num ${p.muted}`}>{t}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table></div>
                </div>
              </Fragment>
            ))}
            <Paginator page={d.evidence_page.page} pageSize={d.evidence_page.page_size} total={Math.max(...d.hops.map((h) => h.transactions_total))} onPage={setPage} />
          </>
        )}
      </StateView>
    </div>
  );
}

function PathCard({ path, index, snapshotId }: { path: Path; index: number; snapshotId: string }) {
  const [open, setOpen] = useState(false);
  return (
    <article className={s.path} aria-label={`Path ${index + 1}`}>
      <div className={s.pathHead}>
        <span>
          Path {index + 1} · {path.path_length} hops · total <span className="num">{amount(path.total_amount)}</span> · id <span className="num">{shortId(path.path_id)}</span>
        </span>
        <button type="button" className={`${ui.button} ${ui.small}`} aria-expanded={open} onClick={() => setOpen((o) => !o)}>
          {open ? <ChevronUp size={14} aria-hidden /> : <ChevronDown size={14} aria-hidden />}
          {open ? "Hide transactions" : "Supporting transactions"}
        </button>
      </div>
      <div className={s.chain}>
        {path.accounts.map((acc, i) => {
          const hop = path.hops[i];
          return (
            <Fragment key={acc}>
              <div className={s.acct}>
                <Link to={`/accounts/${encodeURIComponent(acc)}`}>{acc.split(":").pop()}</Link>
                <span className={s.acctId}>{acc}</span>
              </div>
              {hop && (
                <div className={s.hop}>
                  <span className="num">{amount(hop.total_amount)}</span>
                  <svg className={s.arrow} viewBox="0 0 100 10" preserveAspectRatio="none" aria-hidden>
                    <path d="M0 5H92" stroke="currentColor" strokeWidth="2" vectorEffect="non-scaling-stroke" />
                    <path d="M90 0 100 5 90 10z" fill="currentColor" />
                  </svg>
                  <span>
                    {int(hop.tx_count)} tx{hop.evidence_truncated ? " (evidence truncated)" : ""}
                  </span>
                </div>
              )}
            </Fragment>
          );
        })}
      </div>
      {open && <Evidence path={path} snapshotId={snapshotId} />}
    </article>
  );
}

export function PathView() {
  const [params, setParams] = useSearchParams();
  const from = params.get("from") ?? "";
  const to = params.get("to") ?? "";
  const mode = params.get("mode") === "ALL" ? "ALL" : "SHORTEST";
  const maxDepth = Math.min(Number(params.get("max_depth") ?? 5) || 5, 5);
  const [draft, setDraft] = useState({ from, to, mode, maxDepth: String(maxDepth) });
  const result = useApi<PathQuery>(from && to ? (sig) => graphService.path({ source_account_id: from, destination_account_id: to, mode, max_depth: maxDepth, max_results: 10 }, sig) : null, [from, to, mode, maxDepth], (d) => d.paths.length === 0);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setParams({ from: draft.from.trim(), to: draft.to.trim(), mode: draft.mode, max_depth: draft.maxDepth });
  };

  return (
    <div className={p.page}>
      <PageHeader title="Money flow" lede="Directed paths between two accounts through aggregated transfers in the active snapshot." />
      <div className={p.body}>
        <form className={ui.toolbar} onSubmit={submit}>
          <label className={ui.field} style={{ flex: "1 1 220px" }}>
            <span className={ui.label}>From account ID</span>
            <input className={ui.input} value={draft.from} onChange={(e) => setDraft({ ...draft, from: e.target.value })} />
          </label>
          <label className={ui.field} style={{ flex: "1 1 220px" }}>
            <span className={ui.label}>To account ID</span>
            <input className={ui.input} value={draft.to} onChange={(e) => setDraft({ ...draft, to: e.target.value })} />
          </label>
          <label className={ui.field}>
            <span className={ui.label}>Mode</span>
            <select className={ui.select} value={draft.mode} onChange={(e) => setDraft({ ...draft, mode: e.target.value as "SHORTEST" | "ALL" })}>
              <option value="SHORTEST">Shortest paths</option>
              <option value="ALL">All simple paths</option>
            </select>
          </label>
          <label className={ui.field}>
            <span className={ui.label}>Max hops</span>
            <select className={ui.select} value={draft.maxDepth} onChange={(e) => setDraft({ ...draft, maxDepth: e.target.value })}>
              {[1, 2, 3, 4, 5].map((d) => (
                <option key={d}>{d}</option>
              ))}
            </select>
          </label>
          <button type="submit" className={`${ui.button} ${ui.primary}`} disabled={!draft.from.trim() || !draft.to.trim()}>
            Trace
          </button>
        </form>
        {!from || !to ? (
          <p className={p.muted}>Enter two account IDs. Paths are limited to 5 hops and 10 results; queries time out after 5 seconds.</p>
        ) : (
          <StateView result={result} rows={6} empty={`No directed path within ${maxDepth} hops. A missing path is not evidence that funds did not move by other means.`}>
            {(q) => (
              <div className={p.stack}>
                <StaleBanner isStale={q.is_stale} />
                <div className={s.statement} role="note">
                  <Info size={16} aria-hidden />
                  <span>{q.statement}</span>
                </div>
                <div className={p.spread}>
                  <div className={p.row}>
                    <EvidenceLabel kind="ANALYTICAL SIGNAL" />
                    <span className={`${p.muted} ${p.small}`}>
                      {int(q.paths_found)} found{q.truncated ? `, showing ${q.paths.length} (result limit reached)` : ""} · {q.algorithm_version}
                    </span>
                  </div>
                  <LineageBadge lineage={q.lineage} computedAt={q.computed_at} isStale={q.is_stale} />
                </div>
                {q.paths.map((path, i) => (
                  <PathCard key={path.path_id} path={path} index={i} snapshotId={q.graph_snapshot_id} />
                ))}
              </div>
            )}
          </StateView>
        )}
      </div>
    </div>
  );
}
