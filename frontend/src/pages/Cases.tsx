import { Plus } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { caseService } from "../api/cases";
import type { Priority } from "../api/types";
import { PageHeader, Paginator } from "../components/bits";
import { StateView } from "../components/StateView";
import ui from "../components/ui.module.css";
import { dateTime, humanize, shortId } from "../lib/format";
import { tierColor } from "../lib/ramp";
import { useApi } from "../lib/useApi";
import { useSession } from "../state/session";
import p from "./page.module.css";

const STATUSES = ["", "OPEN", "IN_REVIEW", "ESCALATED", "RESOLVED", "FALSE_POSITIVE", "CLOSED"];

export function StatusChip({ status }: { status: string }) {
  const color = { OPEN: "var(--text-1)", IN_REVIEW: "var(--text-1)", ESCALATED: "var(--text-1)", RESOLVED: "var(--text-2)", FALSE_POSITIVE: "var(--text-2)", CLOSED: "var(--text-3)" }[status] ?? "var(--text-2)";
  const filled = status === "ESCALATED";
  return (
    <span className={ui.chip} style={{ color, background: filled ? "var(--ink-3)" : undefined, borderStyle: status === "CLOSED" ? "dashed" : undefined }}>
      <span className={ui.dot} aria-hidden style={{ background: status === "IN_REVIEW" || status === "ESCALATED" ? "currentColor" : "transparent", border: "1px solid currentColor" }} />
      {humanize(status)}
    </span>
  );
}

function NewCase({ onCreated }: { onCreated: (id: string) => void }) {
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState<Priority>("MEDIUM");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onCreated((await caseService.create({ title: title.trim(), priority })).case_id);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };
  return (
    <form className={ui.toolbar} onSubmit={submit} aria-label="New case">
      <label className={ui.field} style={{ flex: "1 1 320px" }}>
        <span className={ui.label}>Title</span>
        <input className={ui.input} value={title} maxLength={250} onChange={(e) => setTitle(e.target.value)} placeholder="What is being investigated" />
      </label>
      <label className={ui.field}>
        <span className={ui.label}>Priority</span>
        <select className={ui.select} value={priority} onChange={(e) => setPriority(e.target.value as Priority)}>
          {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((pr) => (
            <option key={pr} value={pr}>
              {humanize(pr)}
            </option>
          ))}
        </select>
      </label>
      <button type="submit" className={`${ui.button} ${ui.primary}`} disabled={busy || !title.trim()}>
        <Plus size={15} aria-hidden />
        Create case
      </button>
      {error && <span className={ui.error}>{error}</span>}
    </form>
  );
}

export function Cases() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const user = useSession((st) => st.user);
  const status = params.get("status") ?? "";
  const mine = params.get("mine") === "1";
  const page = Number(params.get("page") ?? 1);
  const result = useApi((sig) => caseService.list({ status: status || undefined, assigned_to: mine ? user?.user_id : undefined, page }, sig), [status, mine, page], (d) => d.items.length === 0);
  const set = (k: string, v: string) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v);
    else next.delete(k);
    if (k !== "page") next.delete("page");
    setParams(next);
  };
  return (
    <div className={p.page}>
      <PageHeader title="Cases" lede="Investigations, their subjects and findings. Transitions are enforced by the server for your role." />
      <div className={p.body}>
        <NewCase onCreated={(id) => navigate(`/cases/${id}`)} />
        <div className={ui.toolbar}>
          <label className={ui.field}>
            <span className={ui.label}>Status</span>
            <select className={ui.select} value={status} onChange={(e) => set("status", e.target.value)}>
              {STATUSES.map((st) => (
                <option key={st} value={st}>
                  {st ? humanize(st) : "Any status"}
                </option>
              ))}
            </select>
          </label>
          <label className={ui.field}>
            <span className={ui.label}>Assignment</span>
            <select className={ui.select} value={mine ? "1" : ""} onChange={(e) => set("mine", e.target.value)}>
              <option value="">Everyone</option>
              <option value="1">Assigned to me</option>
            </select>
          </label>
        </div>
        <div className={ui.panel}>
          <StateView result={result} rows={8} empty={mine || status ? "No cases match these filters." : "No cases yet. Open one from Triage or an account workspace, or create one above."}>
            {(data) => (
              <>
                <div className={p.tableWrap}>
                  <div className={ui.tableScroll}><table className={ui.table}>
                    <thead>
                      <tr>
                        <th>Case</th>
                        <th>Status</th>
                        <th>Priority</th>
                        <th>Assigned</th>
                        <th>Updated</th>
                        <th>ID</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.items.map((c) => (
                        <tr key={c.case_id} data-clickable="true" onClick={() => navigate(`/cases/${c.case_id}`)}>
                          <td style={{ whiteSpace: "normal" }}>
                            <Link to={`/cases/${c.case_id}`} className="entity">
                              {c.title}
                            </Link>
                          </td>
                          <td>
                            <StatusChip status={c.status} />
                          </td>
                          <td style={{ color: tierColor(c.priority) }}>{humanize(c.priority)}</td>
                          <td className={p.muted}>{c.assigned_to ? (c.assigned_to === user?.user_id ? "you" : shortId(c.assigned_to)) : "unassigned"}</td>
                          <td className="num">{dateTime(c.updated_at)}</td>
                          <td className={`num ${p.muted}`}>{shortId(c.case_id)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table></div>
                </div>
                <Paginator page={data.page} pageSize={data.page_size} total={data.total} capped={data.total_is_capped} onPage={(n) => set("page", String(n))} />
              </>
            )}
          </StateView>
        </div>
      </div>
    </div>
  );
}
