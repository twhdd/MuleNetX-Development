import { Upload } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { pipelineService } from "../../api/pipeline";
import { PageHeader, Paginator } from "../../components/bits";
import { StateView } from "../../components/StateView";
import ui from "../../components/ui.module.css";
import { dateTime, humanize, int, shortId } from "../../lib/format";
import { can } from "../../lib/permissions";
import { useApi } from "../../lib/useApi";
import { useSession } from "../../state/session";
import p from "../page.module.css";
import s from "./admin.module.css";

function UploadForm({ onDone }: { onDone: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("paysim");
  const [version, setVersion] = useState("v1");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string; run?: string } | null>(null);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setMessage(null);
    try {
      const res = await pipelineService.upload({ file, name, dataset_version: version, source: "paysim", schema_version: "paysim-1", adapter: "paysim-v1" });
      setMessage({ ok: true, text: `Accepted as ${res.dataset_key}. Follow the pipeline run for progress.`, run: res.pipeline_run_id });
      onDone();
    } catch (err) {
      setMessage({ ok: false, text: (err as Error).message });
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className={`${ui.panel} ${s.drop}`} onSubmit={submit}>
      <div className={s.formGrid}>
        <label className={ui.field}>
          <span className={ui.label}>PaySim CSV</span>
          <input className={ui.input} style={{ paddingTop: 5 }} type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </label>
        <label className={ui.field}>
          <span className={ui.label}>Dataset name</span>
          <input className={ui.input} value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className={ui.field}>
          <span className={ui.label}>Version</span>
          <input className={ui.input} value={version} onChange={(e) => setVersion(e.target.value)} />
        </label>
      </div>
      <div className={ui.toolbar}>
        <button type="submit" className={`${ui.button} ${ui.primary}`} disabled={!file || busy || !name || !version}>
          <Upload size={15} aria-hidden />
          {busy ? "Uploading…" : "Upload and start pipeline"}
        </button>
        <span className={ui.hint}>Adapter paysim-v1 · schema paysim-1. Large reference files can be registered with the CLI instead.</span>
      </div>
      {message && (
        <p className={message.ok ? ui.hint : ui.error} role={message.ok ? "status" : "alert"}>
          {message.text} {message.run && <Link to={`/admin/pipelines/${message.run}`}>Open run {shortId(message.run)}</Link>}
        </p>
      )}
    </form>
  );
}

export function Ingestion() {
  const role = useSession((st) => st.user?.role);
  const [page, setPage] = useState(1);
  const [tick, setTick] = useState(0);
  const result = useApi((sig) => pipelineService.ingestions(page, sig), [page, tick], (d) => d.items.length === 0);
  return (
    <div className={p.page}>
      <PageHeader title="Ingestion" lede="Datasets registered for analysis. The ingestion response never means the data is ready; readiness is read from the pipeline run." />
      <div className={p.body}>
        {can.ingest(role) && <UploadForm onDone={() => setTick((t) => t + 1)} />}
        <div className={ui.panel}>
          <StateView result={result} rows={6} empty="No datasets ingested yet.">
            {(data) => (
              <>
                <div className={p.tableWrap}>
                  <div className={ui.tableScroll}><table className={ui.table}>
                    <thead>
                      <tr>
                        <th>Dataset</th>
                        <th>Status</th>
                        <th className={ui.right}>Seen</th>
                        <th className={ui.right}>Accepted</th>
                        <th className={ui.right}>Rejected</th>
                        <th className={ui.right}>Duplicate</th>
                        <th>Started</th>
                        <th>Pipeline</th>
                        <th>Profile</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.items.map((r) => (
                        <tr key={r.ingestion_run_id}>
                          <td>
                            <span className="entity">{r.dataset_name ?? "—"}</span> <span className={`num ${p.muted}`}>{r.dataset_key}</span>
                          </td>
                          <td>{humanize(r.status)}</td>
                          <td className={`num ${ui.right}`}>{int(r.records_seen)}</td>
                          <td className={`num ${ui.right}`}>{int(r.records_accepted)}</td>
                          <td className={`num ${ui.right}`}>{int(r.records_rejected)}</td>
                          <td className={`num ${ui.right}`}>{int(r.records_duplicate)}</td>
                          <td className="num">{dateTime(r.started_at)}</td>
                          <td>{r.pipeline_run_id ? <Link to={`/admin/pipelines/${r.pipeline_run_id}`} className="num">{shortId(r.pipeline_run_id)}</Link> : "—"}</td>
                          <td>
                            <Link to={`/admin/datasets/${r.dataset_id}/profile`}>Profile</Link>
                          </td>
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
