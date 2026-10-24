import { useNavigate, useSearchParams } from "react-router-dom";
import { ringService } from "../api/rings";
import type { Ring } from "../api/types";
import { PageHeader, Paginator, ScoreBar, TierChip } from "../components/bits";
import { EvidenceLabel } from "../components/EvidenceLabel";
import { StateView } from "../components/StateView";
import ui from "../components/ui.module.css";
import { dateTime, humanize, int, shortId } from "../lib/format";
import { useApi } from "../lib/useApi";
import p from "./page.module.css";

export const CLASS_LABEL: Record<string, string> = {
  POTENTIAL_FRAUD_RING_CANDIDATE: "Potential fraud ring",
  SUSPICIOUS_COMMUNITY: "Suspicious community",
};

export function RingStatusChip({ status }: { status: string }) {
  return (
    <span className={ui.chip} style={{ borderStyle: status === "DISMISSED" ? "dashed" : undefined, color: status === "CANDIDATE" ? "var(--text-1)" : "var(--text-2)" }}>
      {humanize(status)}
    </span>
  );
}

export function ClassChip({ ring }: { ring: Pick<Ring, "candidate_class"> }) {
  const potential = ring.candidate_class === "POTENTIAL_FRAUD_RING_CANDIDATE";
  return (
    <span className={ui.chip} style={potential ? { background: "var(--ink-3)", borderColor: "var(--text-2)" } : undefined}>
      {CLASS_LABEL[ring.candidate_class]}
    </span>
  );
}

export function Rings() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const q = { class: params.get("class") ?? undefined, status: params.get("status") ?? undefined, min_score: params.get("min") ?? undefined, page: Number(params.get("page") ?? 1) };
  const result = useApi((sig) => ringService.list(q, sig), [params.toString()], (d) => d.items.length === 0);
  const set = (k: string, v: string) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v);
    else next.delete(k);
    if (k !== "page") next.delete("page");
    setParams(next);
  };
  return (
    <div className={p.page}>
      <PageHeader
        title="Rings"
        lede="Communities whose members, money and timing score as suspicious networks. Candidates for investigation, not confirmed criminal organisations."
        actions={<EvidenceLabel kind="ANALYTICAL CANDIDATE" />}
      />
      <div className={p.body}>
        <div className={ui.toolbar}>
          <label className={ui.field}>
            <span className={ui.label}>Class</span>
            <select className={ui.select} value={q.class ?? ""} onChange={(e) => set("class", e.target.value)}>
              <option value="">Both classes</option>
              <option value="POTENTIAL_FRAUD_RING_CANDIDATE">Potential fraud ring</option>
              <option value="SUSPICIOUS_COMMUNITY">Suspicious community</option>
            </select>
          </label>
          <label className={ui.field}>
            <span className={ui.label}>Review status</span>
            <select className={ui.select} value={q.status ?? ""} onChange={(e) => set("status", e.target.value)}>
              <option value="">Any status</option>
              {["CANDIDATE", "REVIEWED", "DISMISSED"].map((st) => (
                <option key={st} value={st}>
                  {humanize(st)}
                </option>
              ))}
            </select>
          </label>
          <label className={ui.field}>
            <span className={ui.label}>Minimum candidate score</span>
            <select className={ui.select} value={q.min_score ?? ""} onChange={(e) => set("min", e.target.value)}>
              <option value="">0.50 (all persisted)</option>
              <option value="0.6">0.60</option>
              <option value="0.7">0.70</option>
              <option value="0.8">0.80</option>
            </select>
          </label>
        </div>
        <div className={ui.panel}>
          <StateView result={result} rows={8} empty="No candidate in the active scoring run matches. Communities scoring below 0.50 are not persisted.">
            {(data) => (
              <>
                <div className={p.tableWrap}>
                  <div className={ui.tableScroll}><table className={ui.table}>
                    <thead>
                      <tr>
                        <th>Ring</th>
                        <th>Class</th>
                        <th style={{ width: 180 }}>Candidate score</th>
                        <th>Ring risk</th>
                        <th className={ui.right}>Members</th>
                        <th className={ui.right}>Transactions</th>
                        <th>Status</th>
                        <th>Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.items.map((r) => (
                        <tr key={r.ring_id} data-clickable="true" onClick={() => navigate(`/rings/${r.ring_id}`)}>
                          <td>
                            <span className="entity">Ring {shortId(r.ring_id)}</span>
                          </td>
                          <td>
                            <ClassChip ring={r} />
                          </td>
                          <td>
                            <ScoreBar value={r.candidate_score} />
                          </td>
                          <td>{r.ring_risk_score === null ? <span className={p.muted}>not computed</span> : <span className="num">{r.ring_risk_score.toFixed(3)} <TierChip tier={r.ring_risk_tier} /></span>}</td>
                          <td className={`num ${ui.right}`}>{int(r.member_count)}</td>
                          <td className={`num ${ui.right}`}>{int(r.transaction_count)}</td>
                          <td>
                            <RingStatusChip status={r.candidate_status} />
                          </td>
                          <td className="num">{dateTime(r.created_at)}</td>
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
