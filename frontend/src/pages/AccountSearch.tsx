import { Search } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { accountService, type AccountSearch as Query } from "../api/accounts";
import { AccountLink, PageHeader, Paginator, ScoreBar, TierChip } from "../components/bits";
import { EvidenceLabel } from "../components/EvidenceLabel";
import { StateView } from "../components/StateView";
import ui from "../components/ui.module.css";
import { shortId } from "../lib/format";
import { useApi } from "../lib/useApi";
import p from "./page.module.css";

const TIERS = ["", "CRITICAL", "HIGH", "MEDIUM", "LOW"];
const TYPES = ["", "CUSTOMER", "MERCHANT"];

export function AccountSearch() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const query: Query = {
    q: params.get("q") ?? undefined,
    risk_tier: params.get("tier") ?? undefined,
    account_type: params.get("type") ?? undefined,
    sort: (params.get("sort") as Query["sort"]) ?? "risk_score",
    order: (params.get("order") as Query["order"]) ?? "desc",
    page: Number(params.get("page") ?? 1),
    page_size: 50,
  };
  const [draft, setDraft] = useState(query.q ?? "");
  const result = useApi((sig) => accountService.search(query, sig), [params.toString()], (d) => d.items.length === 0);

  const update = (next: Record<string, string | undefined>) => {
    const merged = new URLSearchParams(params);
    for (const [k, v] of Object.entries(next)) {
      if (v) merged.set(k, v);
      else merged.delete(k);
    }
    if (!("page" in next)) merged.delete("page");
    setParams(merged);
  };
  const submit = (e: FormEvent) => {
    e.preventDefault();
    update({ q: draft.trim() || undefined });
  };

  return (
    <div className={p.page}>
      <PageHeader title="Accounts" lede="Search the active dataset by source reference (exact or prefix). Scores are analytical signals, not determinations." />
      <div className={p.body}>
        <form className={ui.toolbar} onSubmit={submit} role="search">
          <label className={ui.field} style={{ flex: "1 1 260px" }}>
            <span className={ui.label}>Source reference</span>
            <input className={ui.input} value={draft} placeholder="e.g. C1231006815 or C12" onChange={(e) => setDraft(e.target.value)} maxLength={128} />
          </label>
          <label className={ui.field}>
            <span className={ui.label}>Tier</span>
            <select className={ui.select} value={query.risk_tier ?? ""} onChange={(e) => update({ tier: e.target.value || undefined })}>
              {TIERS.map((t) => (
                <option key={t} value={t}>
                  {t || "Any tier"}
                </option>
              ))}
            </select>
          </label>
          <label className={ui.field}>
            <span className={ui.label}>Type</span>
            <select className={ui.select} value={query.account_type ?? ""} onChange={(e) => update({ type: e.target.value || undefined })}>
              {TYPES.map((t) => (
                <option key={t} value={t}>
                  {t || "Any type"}
                </option>
              ))}
            </select>
          </label>
          <label className={ui.field}>
            <span className={ui.label}>Sort</span>
            <select
              className={ui.select}
              value={`${query.sort}:${query.order}`}
              onChange={(e) => {
                const [sort, order] = e.target.value.split(":");
                update({ sort, order });
              }}
            >
              <option value="risk_score:desc">Highest score</option>
              <option value="risk_score:asc">Lowest score</option>
              <option value="account_id:asc">Account ID</option>
              <option value="source_account_ref:asc">Source reference</option>
            </select>
          </label>
          <button type="submit" className={`${ui.button} ${ui.primary}`}>
            <Search size={15} aria-hidden />
            Search
          </button>
        </form>
        <div className={ui.panel}>
          <StateView result={result} rows={10} empty="No accounts match. Widen the filters or check the reference prefix.">
            {(page) => (
              <>
                <div className={p.tableWrap}>
                  <div className={ui.tableScroll}><table className={ui.table}>
                    <thead>
                      <tr>
                        <th>Account</th>
                        <th>Type</th>
                        <th>Tier</th>
                        <th style={{ width: 200 }}>
                          Final score <EvidenceLabel kind="MODEL OUTPUT" />
                        </th>
                        <th>Community</th>
                        <th>Account ID</th>
                      </tr>
                    </thead>
                    <tbody>
                      {page.items.map((a) => (
                        <tr key={a.account_id} data-clickable="true" onClick={(e) => (e.target as HTMLElement).tagName !== "A" && navigate(`/accounts/${encodeURIComponent(a.account_id)}`)}>
                          <td>
                            <AccountLink id={a.account_id}>{a.source_account_ref}</AccountLink>
                          </td>
                          <td>{a.account_type}</td>
                          <td>
                            <TierChip tier={a.risk_tier} />
                          </td>
                          <td>
                            <ScoreBar value={a.risk_score} />
                          </td>
                          <td className="num">{shortId(a.community_id)}</td>
                          <td className={`num ${p.muted}`}>{a.account_id}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table></div>
                </div>
                <Paginator page={page.page} pageSize={page.page_size} total={page.total} capped={page.total_is_capped} onPage={(n) => update({ page: String(n) })} />
              </>
            )}
          </StateView>
        </div>
      </div>
    </div>
  );
}
