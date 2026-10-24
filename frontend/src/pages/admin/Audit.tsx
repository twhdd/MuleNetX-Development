import { useState, type FormEvent } from "react";
import { auditService, type AuditQuery } from "../../api/admin";
import { PageHeader, Paginator } from "../../components/bits";
import { StateView } from "../../components/StateView";
import ui from "../../components/ui.module.css";
import { dateTime, shortId } from "../../lib/format";
import { useApi } from "../../lib/useApi";
import p from "../page.module.css";

const OUTCOME_COLOR: Record<string, string> = { SUCCESS: "var(--text-2)", DENIED: "var(--warn)", FAILED: "var(--danger)" };

export function Audit() {
  const [query, setQuery] = useState<AuditQuery>({ page: 1 });
  const [draft, setDraft] = useState({ action: "", resource_type: "", outcome: "", user_id: "" });
  const result = useApi((sig) => auditService.list(query, sig), [JSON.stringify(query)], (d) => d.items.length === 0);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    setQuery({ page: 1, action: draft.action || undefined, resource_type: draft.resource_type || undefined, outcome: draft.outcome || undefined, user_id: draft.user_id || undefined });
  };
  return (
    <div className={p.page}>
      <PageHeader title="Audit log" lede="Append-only record of sign-ins, denials, administration, pipeline and case activity. Newest first." />
      <div className={p.body}>
        <form className={ui.toolbar} onSubmit={submit}>
          <label className={ui.field}>
            <span className={ui.label}>Action</span>
            <input className={ui.input} placeholder="case.create" value={draft.action} onChange={(e) => setDraft({ ...draft, action: e.target.value })} />
          </label>
          <label className={ui.field}>
            <span className={ui.label}>Resource type</span>
            <input className={ui.input} placeholder="case" value={draft.resource_type} onChange={(e) => setDraft({ ...draft, resource_type: e.target.value })} />
          </label>
          <label className={ui.field}>
            <span className={ui.label}>Outcome</span>
            <select className={ui.select} value={draft.outcome} onChange={(e) => setDraft({ ...draft, outcome: e.target.value })}>
              <option value="">Any</option>
              <option>SUCCESS</option>
              <option>DENIED</option>
              <option>FAILED</option>
            </select>
          </label>
          <label className={ui.field} style={{ flex: "1 1 260px" }}>
            <span className={ui.label}>User ID</span>
            <input className={ui.input} value={draft.user_id} onChange={(e) => setDraft({ ...draft, user_id: e.target.value })} />
          </label>
          <button type="submit" className={`${ui.button} ${ui.primary}`}>
            Filter
          </button>
        </form>
        <div className={ui.panel}>
          <StateView result={result} rows={10} empty="No audit events match.">
            {(data) => (
              <>
                <div className={p.tableWrap}>
                  <div className={ui.tableScroll}><table className={ui.table}>
                    <thead>
                      <tr>
                        <th>Time (UTC)</th>
                        <th>Action</th>
                        <th>Outcome</th>
                        <th>Resource</th>
                        <th>User</th>
                        <th>Request</th>
                        <th>Metadata</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.items.map((e) => (
                        <tr key={e.event_id}>
                          <td className="num">{dateTime(e.timestamp)}</td>
                          <td className="num">{e.action}</td>
                          <td style={{ color: OUTCOME_COLOR[e.outcome] }}>{e.outcome}</td>
                          <td>
                            {e.resource_type} <span className={`num ${p.muted}`}>{e.resource_id ? shortId(e.resource_id, 12) : ""}</span>
                          </td>
                          <td className="num">{shortId(e.user_id)}</td>
                          <td className={`num ${p.muted}`}>{shortId(e.request_id)}</td>
                          <td className={`num ${p.muted}`} style={{ whiteSpace: "normal", maxWidth: 360 }}>
                            {Object.keys(e.metadata).length ? JSON.stringify(e.metadata) : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table></div>
                </div>
                <Paginator page={data.page} pageSize={data.page_size} total={data.total} capped={data.total_is_capped} onPage={(n) => setQuery({ ...query, page: n })} />
              </>
            )}
          </StateView>
        </div>
      </div>
    </div>
  );
}
