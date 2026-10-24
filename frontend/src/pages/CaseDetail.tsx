import { Plus, RefreshCw, Trash2, X } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { caseService, type CasePatch, type EvidenceRef, type SubjectType } from "../api/cases";
import type { Case, CaseStatus, Priority } from "../api/types";
import { AccountLink, Paginator } from "../components/bits";
import { EvidenceLabel } from "../components/EvidenceLabel";
import { StateView } from "../components/StateView";
import ui from "../components/ui.module.css";
import { dateTime, humanize, shortId } from "../lib/format";
import { can, offeredTransitions } from "../lib/permissions";
import { useApi } from "../lib/useApi";
import { useSession } from "../state/session";
import { StatusChip } from "./Cases";
import p from "./page.module.css";
import { CopilotPanel } from "../components/CopilotPanel";
import s from "./CaseDetail.module.css";

const TRANSITION_LABEL: Partial<Record<CaseStatus, string>> = {
  IN_REVIEW: "Start review",
  ESCALATED: "Escalate",
  RESOLVED: "Resolve",
  FALSE_POSITIVE: "Mark false positive",
  CLOSED: "Close",
};

function describe(err: unknown): { conflict: boolean; message: string } {
  if (err instanceof ApiError) {
    if (err.code === "CASE_VERSION_CONFLICT") return { conflict: true, message: "This case changed since you loaded it." };
    if (err.status === 403) return { conflict: false, message: "Your role cannot make this change on this case." };
    if (err.code === "INVALID_CASE_TRANSITION") return { conflict: false, message: "That transition is not allowed from the current status." };
    return { conflict: false, message: err.message };
  }
  return { conflict: false, message: (err as Error).message };
}

function Header({ c, onChange, reload }: { c: Case; onChange: (next: Case) => void; reload: () => void }) {
  const user = useSession((st) => st.user);
  const role = user?.role ?? "ANALYST";
  const participant = !!user && (c.created_by === user.user_id || c.assigned_to === user.user_id);
  const editable = c.status !== "CLOSED" && can.editCase(role, participant);
  const [title, setTitle] = useState(c.title);
  const [editingTitle, setEditingTitle] = useState(false);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<{ conflict: boolean; message: string } | null>(null);
  const [assignee, setAssignee] = useState(c.assigned_to ?? "");

  const patch = async (changes: Omit<CasePatch, "version">) => {
    setBusy(true);
    setProblem(null);
    try {
      const next = await caseService.patch(c.case_id, { version: c.version, ...changes });
      onChange(next);
      setTitle(next.title);
      setAssignee(next.assigned_to ?? "");
      setEditingTitle(false);
    } catch (err) {
      setProblem(describe(err));
    } finally {
      setBusy(false);
    }
  };
  const submitTitle = (e: FormEvent) => {
    e.preventDefault();
    if (title.trim() && title.trim() !== c.title) void patch({ title: title.trim() });
    else setEditingTitle(false);
  };

  return (
    <header className={s.head}>
      <div className={s.titleRow}>
        {editingTitle ? (
          <form onSubmit={submitTitle} className={ui.toolbar} style={{ flex: 1 }}>
            <input className={ui.input} style={{ flex: 1, fontSize: "var(--fs-lg)", height: 40 }} value={title} maxLength={250} onChange={(e) => setTitle(e.target.value)} autoFocus aria-label="Case title" />
            <button type="submit" className={`${ui.button} ${ui.primary}`} disabled={busy}>
              Save
            </button>
            <button type="button" className={`${ui.button} ${ui.ghost}`} onClick={() => { setTitle(c.title); setEditingTitle(false); }}>
              Cancel
            </button>
          </form>
        ) : (
          <>
            <h1 className={s.title}>{c.title}</h1>
            {editable && (
              <button type="button" className={`${ui.button} ${ui.ghost} ${ui.small}`} onClick={() => setEditingTitle(true)}>
                Rename
              </button>
            )}
          </>
        )}
      </div>
      <div className={s.meta}>
        <StatusChip status={c.status} />
        <span>
          Case <span className="num">{c.case_id}</span>
        </span>
        <span>
          Opened {dateTime(c.created_at)} by {c.created_by === user?.user_id ? "you" : <span className="num">{shortId(c.created_by)}</span>}
        </span>
        <span>
          Version <span className="num">{c.version}</span>
        </span>
        {c.closed_at && <span>Closed {dateTime(c.closed_at)}</span>}
      </div>
      {problem && (
        <div className={s.conflict} role="alert">
          {problem.message}
          {problem.conflict && (
            <button type="button" className={`${ui.button} ${ui.small}`} onClick={reload}>
              <RefreshCw size={13} aria-hidden />
              Reload latest
            </button>
          )}
        </div>
      )}
      {c.status === "CLOSED" ? (
        <p className={ui.hint}>Closed cases are read-only.</p>
      ) : (
        <div className={s.controls}>
          <label className={ui.field}>
            <span className={ui.label}>Priority</span>
            <select className={ui.select} value={c.priority} disabled={!editable || busy} onChange={(e) => void patch({ priority: e.target.value as Priority })}>
              {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((pr) => (
                <option key={pr} value={pr}>
                  {humanize(pr)}
                </option>
              ))}
            </select>
          </label>
          {can.assignCases(role) && (
            <form className={ui.toolbar} onSubmit={(e) => { e.preventDefault(); void patch({ assigned_to: assignee.trim() || null }); }}>
              <label className={ui.field}>
                <span className={ui.label}>Assignee user ID</span>
                <input className={ui.input} style={{ width: 300 }} value={assignee} onChange={(e) => setAssignee(e.target.value)} placeholder="unassigned" />
              </label>
              <button type="submit" className={ui.button} disabled={busy || assignee === (c.assigned_to ?? "")}>
                Assign
              </button>
              {user && c.assigned_to !== user.user_id && (
                <button type="button" className={`${ui.button} ${ui.ghost}`} disabled={busy} onClick={() => void patch({ assigned_to: user.user_id })}>
                  Assign to me
                </button>
              )}
            </form>
          )}
          <div className={s.transitions} role="group" aria-label="Status transitions">
            {offeredTransitions(role, c.status as CaseStatus, participant).map((to) => (
              <button key={to} type="button" className={`${ui.button} ${to === "RESOLVED" || to === "IN_REVIEW" ? ui.primary : ""}`} disabled={busy} onClick={() => void patch({ status: to })}>
                {TRANSITION_LABEL[to] ?? humanize(to)}
              </button>
            ))}
          </div>
        </div>
      )}
    </header>
  );
}

function Subjects({ c }: { c: Case }) {
  const [page, setPage] = useState(1);
  const [tick, setTick] = useState(0);
  const result = useApi((sig) => caseService.subjects(c.case_id, page, sig), [c.case_id, page, tick], (d) => d.items.length === 0);
  const [type, setType] = useState<SubjectType>("ACCOUNT");
  const [subjectId, setSubjectId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const closed = c.status === "CLOSED";

  const add = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await caseService.addSubject(c.case_id, type, subjectId.trim());
      setSubjectId("");
      setTick((t) => t + 1);
    } catch (err) {
      setError(err instanceof ApiError && err.status === 404 ? `No ${humanize(type).toLowerCase()} with that ID exists.` : describe(err).message);
    }
  };
  const remove = async (t: SubjectType, id: string) => {
    setError(null);
    try {
      await caseService.removeSubject(c.case_id, t, id);
      setTick((x) => x + 1);
    } catch (err) {
      setError(describe(err).message);
    }
  };

  return (
    <section className={ui.panel}>
      <div className={ui.panelHead}>
        <h2 className={ui.panelTitle}>Subjects</h2>
        <EvidenceLabel kind="FACT" />
      </div>
      <StateView result={result} rows={4} empty="No subjects linked yet.">
        {(data) => (
          <>
            <div className={ui.tableScroll}><table className={ui.table}>
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Subject</th>
                  <th>Added</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.items.map((sub) => (
                  <tr key={`${sub.subject_type}:${sub.subject_id}:${sub.added_at}`} className={sub.active ? undefined : s.removed}>
                    <td>{humanize(sub.subject_type)}</td>
                    <td>{sub.subject_type === "ACCOUNT" && sub.active ? <AccountLink id={sub.subject_id} /> : <span className="num">{sub.subject_id}</span>}</td>
                    <td className="num">{dateTime(sub.added_at)}</td>
                    <td className={ui.right}>
                      {sub.active && !closed ? (
                        <button type="button" className={`${ui.button} ${ui.ghost} ${ui.small}`} onClick={() => void remove(sub.subject_type as SubjectType, sub.subject_id)} aria-label={`Remove ${sub.subject_id}`}>
                          <Trash2 size={13} aria-hidden />
                        </button>
                      ) : (
                        !sub.active && <span className={p.small}>removed {dateTime(sub.removed_at)}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table></div>
            <Paginator page={data.page} pageSize={data.page_size} total={data.total} capped={data.total_is_capped} onPage={setPage} />
          </>
        )}
      </StateView>
      {!closed && (
        <form className={s.form} onSubmit={add}>
          <div className={ui.toolbar}>
            <label className={ui.field}>
              <span className={ui.label}>Type</span>
              <select className={ui.select} value={type} onChange={(e) => setType(e.target.value as SubjectType)}>
                <option value="ACCOUNT">Account</option>
                <option value="TRANSACTION">Transaction</option>
                <option value="RING">Ring</option>
                <option value="SCENARIO">Scenario</option>
              </select>
            </label>
            <label className={ui.field} style={{ flex: 1 }}>
              <span className={ui.label}>ID</span>
              <input className={ui.input} value={subjectId} onChange={(e) => setSubjectId(e.target.value)} />
            </label>
            <button type="submit" className={ui.button} disabled={!subjectId.trim()}>
              <Plus size={14} aria-hidden />
              Link
            </button>
          </div>
          {error && <span className={ui.error} role="alert">{error}</span>}
        </form>
      )}
    </section>
  );
}

const EVIDENCE_TYPES: EvidenceRef["type"][] = ["account", "transaction", "community", "ring", "path"];

function Findings({ c }: { c: Case }) {
  const [page, setPage] = useState(1);
  const [tick, setTick] = useState(0);
  const result = useApi((sig) => caseService.findings(c.case_id, page, sig), [c.case_id, page, tick], (d) => d.items.length === 0);
  const [type, setType] = useState("OBSERVATION");
  const [description, setDescription] = useState("");
  const [refs, setRefs] = useState<{ type: EvidenceRef["type"]; id: string; snapshot: string; accounts: string }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const closed = c.status === "CLOSED";

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const evidence: EvidenceRef[] = refs
      .filter((r) => r.id.trim())
      .map((r) => (r.type === "path" ? { type: r.type, id: r.id.trim(), graph_snapshot_id: r.snapshot.trim(), accounts: r.accounts.split(",").map((a) => a.trim()).filter(Boolean) } : { type: r.type, id: r.id.trim() }));
    try {
      await caseService.addFinding(c.case_id, { type, description: description.trim(), evidence, source: "investigator" });
      setDescription("");
      setRefs([]);
      setTick((t) => t + 1);
    } catch (err) {
      const field = err instanceof ApiError ? (err.details.field as string | undefined) : undefined;
      setError(field?.startsWith("evidence.") ? `Evidence reference ${Number(field.split(".")[1]) + 1} does not exist.` : describe(err).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className={ui.panel}>
      <div className={ui.panelHead}>
        <h2 className={ui.panelTitle}>Findings</h2>
        <EvidenceLabel kind="INVESTIGATOR FINDING" />
      </div>
      <StateView result={result} rows={4} empty="No findings recorded. Findings are append-only once saved.">
        {(data) => (
          <>
            {data.items.map((f) => (
              <article key={f.finding_id} className={s.finding}>
                <div className={s.findingMeta}>
                  <span className={ui.chip}>{humanize(f.type)}</span>
                  <span className="num">{dateTime(f.created_at)}</span>
                  <span>by <span className="num">{shortId(f.created_by)}</span></span>
                </div>
                <p>{f.description}</p>
                {f.evidence.length > 0 && (
                  <div className={s.refs}>
                    {(f.evidence as unknown as EvidenceRef[]).map((r, i) => (
                      <span key={i} className={ui.chip}>
                        {r.type}: {r.type === "account" ? <AccountLink id={r.id} /> : <span className="num">{r.id}</span>}
                      </span>
                    ))}
                  </div>
                )}
              </article>
            ))}
            <Paginator page={data.page} pageSize={data.page_size} total={data.total} capped={data.total_is_capped} onPage={setPage} />
          </>
        )}
      </StateView>
      {!closed && (
        <form className={s.form} onSubmit={submit} aria-label="Record a finding">
          <div className={ui.toolbar}>
            <label className={ui.field}>
              <span className={ui.label}>Type</span>
              <select className={ui.select} value={type} onChange={(e) => setType(e.target.value)}>
                {["OBSERVATION", "PATTERN", "CONCLUSION", "NOTE"].map((t) => (
                  <option key={t} value={t}>
                    {humanize(t)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className={ui.field}>
            <span className={ui.label}>Finding</span>
            <textarea className={ui.textarea} value={description} maxLength={20000} onChange={(e) => setDescription(e.target.value)} placeholder="What you observed and why it matters" />
          </label>
          {refs.map((r, i) => (
            <div key={i} className={s.evRow}>
              <select className={ui.select} aria-label={`Evidence ${i + 1} type`} value={r.type} onChange={(e) => setRefs(refs.map((x, j) => (j === i ? { ...x, type: e.target.value as EvidenceRef["type"] } : x)))}>
                {EVIDENCE_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <div className={p.stack} style={{ gap: 6 }}>
                <input className={ui.input} aria-label={`Evidence ${i + 1} ID`} placeholder={r.type === "path" ? "path_id" : "ID"} value={r.id} onChange={(e) => setRefs(refs.map((x, j) => (j === i ? { ...x, id: e.target.value } : x)))} />
                {r.type === "path" && (
                  <>
                    <input className={ui.input} aria-label="Graph snapshot ID" placeholder="graph_snapshot_id" value={r.snapshot} onChange={(e) => setRefs(refs.map((x, j) => (j === i ? { ...x, snapshot: e.target.value } : x)))} />
                    <input className={ui.input} aria-label="Path accounts" placeholder="ordered account IDs, comma-separated" value={r.accounts} onChange={(e) => setRefs(refs.map((x, j) => (j === i ? { ...x, accounts: e.target.value } : x)))} />
                  </>
                )}
              </div>
              <button type="button" className={`${ui.button} ${ui.ghost} ${ui.small}`} aria-label={`Remove evidence ${i + 1}`} onClick={() => setRefs(refs.filter((_, j) => j !== i))}>
                <X size={13} aria-hidden />
              </button>
            </div>
          ))}
          <div className={ui.toolbar}>
            <button type="button" className={`${ui.button} ${ui.ghost}`} onClick={() => setRefs([...refs, { type: "account", id: "", snapshot: "", accounts: "" }])} disabled={refs.length >= 100}>
              <Plus size={14} aria-hidden />
              Evidence reference
            </button>
            <button type="submit" className={`${ui.button} ${ui.primary}`} disabled={busy || !description.trim()}>
              Record finding
            </button>
          </div>
          {error && <span className={ui.error} role="alert">{error}</span>}
        </form>
      )}
    </section>
  );
}

export function CaseDetail() {
  const { id = "" } = useParams();
  const result = useApi((sig) => caseService.get(id, sig), [id]);
  const [override, setOverride] = useState<Case | null>(null);
  const current = override && override.case_id === id && result.data && override.version >= result.data.version ? override : result.data;
  return (
    <div className={p.page}>
      <StateView result={result} rows={6}>
        {() =>
          current && (
            <>
              <Header key={current.version} c={current} onChange={setOverride} reload={() => { setOverride(null); result.reload(); }} />
              <div className={s.body}>
                <Subjects c={current} />
                <Findings c={current} />
                <div className={s.wide}>
                  <CopilotPanel scope={{ case_id: current.case_id }} kind="case" />
                </div>
              </div>
            </>
          )
        }
      </StateView>
    </div>
  );
}
