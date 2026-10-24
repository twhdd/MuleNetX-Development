/** Multi-level evaluation report (SRS §28.7, §19.16): transaction → account → ring → network. */
import { Play } from "lucide-react";
import { useEffect, useState } from "react";
import { evaluationService } from "../api/evaluation";
import type { EvaluationMetric, EvaluationSummary } from "../api/types";
import { PageHeader } from "../components/bits";
import { EvidenceLabel } from "../components/EvidenceLabel";
import { Running, StateView } from "../components/StateView";
import ui from "../components/ui.module.css";
import { dateTime, humanize, int, shortId } from "../lib/format";
import { can } from "../lib/permissions";
import { useApi } from "../lib/useApi";
import { useSession } from "../state/session";
import a from "./admin/admin.module.css";
import p from "./page.module.css";

const LEVEL_TEXT: Record<string, string> = {
  TRANSACTION: "Transactions: max endpoint score vs PaySim labels",
  ACCOUNT: "Accounts: final score vs accounts on labelled transactions",
  RING: "Rings: candidates vs components of labelled transactions",
  NETWORK: "Network: identification, flow coverage, ranking, simulated intervention",
};

function value(m: EvaluationMetric): string {
  if (m.state === "NOT_MEASURABLE") return "not measurable";
  if (m.value === null || m.availability === "UNAVAILABLE") return "unavailable";
  return m.value.toFixed(3);
}

function Level({ level, metrics }: { level: string; metrics: EvaluationMetric[] }) {
  return (
    <section className={ui.panel}>
      <div className={ui.panelHead}>
        <h2 className={ui.panelTitle}>{humanize(level)}</h2>
        <span className={`${p.muted} ${p.small}`}>{LEVEL_TEXT[level]}</span>
      </div>
      <div className={ui.tableScroll}><table className={ui.table}>
        <thead>
          <tr>
            <th>Metric</th>
            <th className={ui.right}>Value</th>
            <th className={ui.right}>Samples</th>
            <th>Note</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((m) => (
            <tr key={m.metric}>
              <td>
                {humanize(m.metric)}
                {m.metric.startsWith("intervention_effectiveness") && (
                  <>
                    {" "}
                    <EvidenceLabel kind="HYPOTHETICAL SIMULATION" />
                  </>
                )}
              </td>
              <td className={`num ${ui.right}`} style={{ color: m.availability === "AVAILABLE" ? undefined : "var(--text-3)" }}>
                {value(m)}
              </td>
              <td className={`num ${ui.right}`}>{int(m.sample_count)}</td>
              <td className={p.muted} style={{ whiteSpace: "normal", maxWidth: 420 }}>
                {String((m.details as Record<string, unknown>).reason ?? "")}
              </td>
            </tr>
          ))}
        </tbody>
      </table></div>
    </section>
  );
}

function Report({ s }: { s: EvaluationSummary }) {
  const lineage = (s.configuration as { lineage?: Record<string, string> }).lineage ?? {};
  return (
    <div className={p.stack}>
      <div className={ui.notice} role="note">
        {s.limitation}
      </div>
      <div className={a.stages} style={{ gridTemplateColumns: "repeat(4, minmax(0, 1fr))" }} aria-label="Progression">
        {s.progression.map((step) => (
          <div key={step.level} className={`${a.stage} ${a.done}`}>
            <strong>{humanize(step.level)}</strong>
            <span>
              {humanize(step.headline_metric)}{" "}
              <span className="num" style={{ color: "var(--text-1)" }}>
                {step.value === null ? "—" : step.value.toFixed(3)}
              </span>
            </span>
          </div>
        ))}
      </div>
      {(["TRANSACTION", "ACCOUNT", "RING", "NETWORK"] as const).map((lvl) => (
        <Level key={lvl} level={lvl} metrics={s.levels[lvl] ?? []} />
      ))}
      <section className={ui.panel}>
        <div className={ui.panelHead}>
          <h2 className={ui.panelTitle}>Lineage</h2>
          <EvidenceLabel kind="FACT" />
        </div>
        <div className={ui.panelBody}>
          <dl className={ui.kv}>
            {Object.entries(lineage).map(([k, v]) => (
              <div key={k} style={{ display: "contents" }}>
                <dt>{humanize(k)}</dt>
                <dd className="num">{v ?? "—"}</dd>
              </div>
            ))}
            <dt>Reference construction</dt>
            <dd className="num">{s.reference_construction_version}</dd>
          </dl>
        </div>
      </section>
    </div>
  );
}

export function Evaluation() {
  const role = useSession((st) => st.user?.role);
  const [tick, setTick] = useState(0);
  const runs = useApi((sig) => evaluationService.list(1, sig), [tick], (d) => d.items.length === 0);
  const [selected, setSelected] = useState<string | null>(null);
  const current = selected ?? runs.data?.items.find((r) => r.status === "COMPLETED")?.evaluation_run_id ?? runs.data?.items[0]?.evaluation_run_id ?? null;
  const summary = useApi(current ? (sig) => evaluationService.get(current, sig) : null, [current, tick]);
  const pending = runs.data?.items.some((r) => r.status === "QUEUED" || r.status === "RUNNING");
  useEffect(() => {
    if (!pending) return;
    const t = window.setInterval(() => setTick((x) => x + 1), 4000);
    return () => window.clearInterval(t);
  }, [pending]);
  const [error, setError] = useState<string | null>(null);
  const start = async () => {
    setError(null);
    try {
      const res = await evaluationService.start();
      setSelected(res.evaluation_run_id);
      setTick((x) => x + 1);
    } catch (err) {
      setError((err as Error).message);
    }
  };
  return (
    <div className={p.page}>
      <PageHeader
        title="Evaluation"
        lede="How the active context's scores, rings and networks agree with the dataset's labels on the model's test split."
        actions={
          can.controlPipelines(role) && (
            <button type="button" className={`${ui.button} ${ui.primary}`} onClick={() => void start()}>
              <Play size={15} aria-hidden />
              Run evaluation
            </button>
          )
        }
      />
      <div className={p.body}>
        {error && <p className={ui.error} role="alert">{error}</p>}
        <StateView result={runs} rows={3} empty="No evaluation has been run.">
          {(data) => (
            <div className={p.row}>
              {data.items.slice(0, 8).map((r) => (
                <button key={r.evaluation_run_id} type="button" className={`${ui.button} ${ui.small}`} aria-pressed={r.evaluation_run_id === current} onClick={() => setSelected(r.evaluation_run_id)} style={r.evaluation_run_id === current ? { borderColor: "var(--text-1)" } : undefined}>
                  {shortId(r.evaluation_run_id)} · {humanize(r.status)} · {dateTime(r.created_at)}
                </button>
              ))}
            </div>
          )}
        </StateView>
        {current && (
          <StateView result={summary} rows={10}>
            {(s) =>
              s.status === "COMPLETED" ? (
                <Report s={s} />
              ) : s.status === "FAILED" ? (
                <p className={ui.error}>Evaluation failed: {s.failure}</p>
              ) : (
                <Running label={s.status === "QUEUED" ? "Queued" : "Evaluating"} queued={s.status === "QUEUED"} />
              )
            }
          </StateView>
        )}
      </div>
    </div>
  );
}
