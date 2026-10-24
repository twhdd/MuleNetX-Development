import { RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { pipelineService } from "../../api/pipeline";
import type { PipelineRun } from "../../api/types";
import { PageHeader, Paginator } from "../../components/bits";
import { Running, StateView } from "../../components/StateView";
import ui from "../../components/ui.module.css";
import { dateTime, humanize, int, shortId } from "../../lib/format";
import { can } from "../../lib/permissions";
import { useApi } from "../../lib/useApi";
import { useActiveContext } from "../../state/context";
import { useSession } from "../../state/session";
import p from "../page.module.css";
import s from "./admin.module.css";

const STAGES: { name: string; running: string; done: string[] }[] = [
  { name: "Ingest", running: "INGESTING", done: ["INGESTED"] },
  { name: "Profile", running: "PROFILING", done: ["PROFILED"] },
  { name: "Graph", running: "GRAPH_BUILDING", done: ["GRAPH_READY"] },
  { name: "Analytics", running: "ANALYTICS_RUNNING", done: ["ANALYTICS_READY"] },
  { name: "Features", running: "FEATURES_RUNNING", done: ["FEATURES_READY"] },
  { name: "Training", running: "TRAINING", done: ["MODEL_READY"] },
  { name: "Scoring", running: "SCORING", done: ["SCORED"] },
  { name: "Rings + activate", running: "RING_ANALYSIS", done: ["READY"] },
];
const ORDER = ["CREATED", "INGESTING", "INGESTED", "PROFILING", "PROFILED", "GRAPH_BUILDING", "GRAPH_READY", "ANALYTICS_RUNNING", "ANALYTICS_READY", "FEATURES_RUNNING", "FEATURES_READY", "TRAINING", "MODEL_READY", "SCORING", "SCORED", "RING_ANALYSIS", "READY"];
export const TERMINAL = new Set(["READY", "FAILED"]);

function stageState(run: PipelineRun, stage: (typeof STAGES)[number]): "done" | "running" | "failed" | "pending" | "skipped" {
  const current = run.current_state;
  if (current === "FAILED") {
    if (run.failure_stage === stage.running) return "failed";
    const at = ORDER.indexOf(run.failure_stage ?? "");
    return at > ORDER.indexOf(stage.running) ? "done" : "pending";
  }
  if (current === stage.running) return "running";
  const idx = ORDER.indexOf(current);
  const doneIdx = Math.min(...stage.done.map((d) => ORDER.indexOf(d)));
  // TRAINING may be skipped when a compatible model exists: SCORING follows FEATURES_READY directly
  if (stage.running === "TRAINING" && idx >= ORDER.indexOf("SCORING") && run.metrics && run.metrics.training_duration === undefined) return "skipped";
  return idx >= doneIdx ? "done" : "pending";
}

export function StateChip({ state }: { state: string }) {
  if (state === "READY") return <span className={ui.chip} style={{ color: "var(--ok)" }}><span className={ui.dot} aria-hidden />Ready</span>;
  if (state === "FAILED") return <span className={ui.chip} style={{ color: "var(--danger)" }}><span className={ui.dot} aria-hidden />Failed</span>;
  if (state === "CREATED") return <Running label="Queued" queued />;
  return <Running label={humanize(state)} />;
}

export function Pipelines() {
  const [page, setPage] = useState(1);
  const navigate = useNavigate();
  const result = useApi((sig) => pipelineService.runs({ page }, sig), [page], (d) => d.items.length === 0);
  const anyRunning = result.data?.items.some((r) => !TERMINAL.has(r.current_state));
  useEffect(() => {
    if (!anyRunning) return;
    const t = window.setInterval(result.reload, 4000);
    return () => window.clearInterval(t);
  }, [anyRunning, result.reload]);
  return (
    <div className={p.page}>
      <PageHeader title="Pipeline runs" lede="Each run walks the dataset from ingestion to an activated analytical context." />
      <div className={p.body}>
        <div className={ui.panel}>
          <StateView result={result} rows={6} empty="No pipeline runs yet.">
            {(data) => (
              <>
                <div className={p.tableWrap}>
                  <div className={ui.tableScroll}><table className={ui.table}>
                    <thead>
                      <tr>
                        <th>Run</th>
                        <th>State</th>
                        <th>Dataset</th>
                        <th>Model</th>
                        <th>Started</th>
                        <th>Completed</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.items.map((r) => (
                        <tr key={r.pipeline_run_id} data-clickable="true" onClick={() => navigate(`/admin/pipelines/${r.pipeline_run_id}`)}>
                          <td>
                            <Link to={`/admin/pipelines/${r.pipeline_run_id}`} className="num">
                              {shortId(r.pipeline_run_id)}
                            </Link>
                          </td>
                          <td>
                            <StateChip state={r.current_state} />
                          </td>
                          <td className="num">{shortId(r.dataset_id)}</td>
                          <td className={`num ${p.muted}`}>{r.model_version ?? "—"}</td>
                          <td className="num">{dateTime(r.started_at)}</td>
                          <td className="num">{dateTime(r.completed_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table></div>
                </div>
                <Paginator page={data.page} pageSize={data.page_size} total={data.total} capped={data.total_is_capped} onPage={setPage} />
              </>
            )}
          </StateView>
        </div>
      </div>
    </div>
  );
}

const METRIC_LABELS: [string, string][] = [
  ["records_seen", "Records seen"],
  ["records_accepted", "Accepted"],
  ["records_rejected", "Rejected"],
  ["records_duplicate", "Duplicates"],
  ["graph_nodes", "Graph accounts"],
  ["graph_edges", "Graph transfers"],
  ["ingestion_duration", "Ingest (s)"],
  ["graph_build_duration", "Graph build (s)"],
  ["analytics_duration", "Analytics (s)"],
  ["feature_generation_duration", "Features (s)"],
  ["training_duration", "Training (s)"],
  ["scoring_duration", "Scoring (s)"],
  ["job_attempts", "Job attempts"],
  ["lease_expirations", "Lease expirations"],
];

function formatMetric(v: unknown): string {
  if (typeof v === "number") return Number.isInteger(v) ? int(v) : v.toFixed(2);
  return String(v);
}

export function PipelineDetail() {
  const { id = "" } = useParams();
  const role = useSession((st) => st.user?.role);
  const refreshContext = useActiveContext((st) => st.refresh);
  const result = useApi((sig) => pipelineService.run(id, sig), [id]);
  const [retryError, setRetryError] = useState<string | null>(null);
  const running = result.data && !TERMINAL.has(result.data.current_state);
  useEffect(() => {
    if (!running) return;
    const t = window.setInterval(result.reload, 3000);
    return () => window.clearInterval(t);
  }, [running, result.reload]);
  useEffect(() => {
    if (result.data?.current_state === "READY") void refreshContext();
  }, [result.data?.current_state, refreshContext]);
  const retry = async () => {
    setRetryError(null);
    try {
      await pipelineService.retry(id);
      result.reload();
    } catch (err) {
      setRetryError((err as Error).message);
    }
  };
  return (
    <div className={p.page}>
      <StateView result={result} rows={8}>
        {(run) => (
          <>
            <PageHeader
              title={
                <>
                  Run <span className="num">{shortId(run.pipeline_run_id)}</span>
                </>
              }
              lede={<>Dataset <span className="num">{run.dataset_id}</span></>}
              actions={
                <>
                  <StateChip state={run.current_state} />
                  {run.current_state === "FAILED" && run.resumable_from && can.controlPipelines(role) && (
                    <button type="button" className={`${ui.button} ${ui.primary}`} onClick={retry}>
                      <RotateCcw size={15} aria-hidden />
                      Retry from {humanize(run.resumable_from)}
                    </button>
                  )}
                </>
              }
            />
            <div className={p.body}>
              {retryError && <p className={ui.error} role="alert">{retryError}</p>}
              <div className={s.stages} aria-label="Stages">
                {STAGES.map((st) => {
                  const state = stageState(run, st);
                  return (
                    <div key={st.name} className={`${s.stage} ${state === "done" ? s.done : state === "running" ? s.running : state === "failed" ? s.failed : ""}`}>
                      <strong>{st.name}</strong>
                      <span>{state === "running" ? "running" : state}</span>
                    </div>
                  );
                })}
              </div>
              {run.current_state === "FAILED" && (
                <div className={`${ui.notice}`} role="alert">
                  Failed in {humanize(run.failure_stage)} ({run.failure_category}): {run.safe_failure_message}
                </div>
              )}
              <div className={s.metrics}>
                {METRIC_LABELS.filter(([k]) => run.metrics && run.metrics[k] !== undefined && run.metrics[k] !== null).map(([k, label]) => (
                  <div key={k} className={s.metric}>
                    <span>{label}</span>
                    <span className="num">{formatMetric(run.metrics![k])}</span>
                  </div>
                ))}
              </div>
              <dl className={ui.kv}>
                <dt>Graph snapshot</dt>
                <dd className="num">{run.graph_snapshot_id ?? "—"}</dd>
                <dt>Analytics run</dt>
                <dd className="num">{run.analytics_run_id ?? "—"}</dd>
                <dt>Scoring run</dt>
                <dd className="num">{run.scoring_run_id ?? "—"}</dd>
                <dt>Model</dt>
                <dd className="num">{run.model_version ? <Link to={`/admin/models/${run.model_version}`}>{run.model_version}</Link> : "—"}</dd>
                <dt>Started / updated</dt>
                <dd className="num">
                  {dateTime(run.started_at)} / {dateTime(run.updated_at)}
                </dd>
              </dl>
            </div>
          </>
        )}
      </StateView>
    </div>
  );
}
