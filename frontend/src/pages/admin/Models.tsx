import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { pipelineService } from "../../api/pipeline";
import { PageHeader, Paginator } from "../../components/bits";
import { EvidenceLabel } from "../../components/EvidenceLabel";
import { StateView } from "../../components/StateView";
import ui from "../../components/ui.module.css";
import { dateTime, int, score, shortId } from "../../lib/format";
import { useApi } from "../../lib/useApi";
import p from "../page.module.css";
import s from "./admin.module.css";

type Metrics = Record<string, number | boolean | null | Record<string, number>>;

const METRICS: [string, string][] = [
  ["pr_auc", "PR-AUC"],
  ["pr_auc_baseline", "PR-AUC baseline"],
  ["roc_auc", "ROC-AUC"],
  ["precision", "Precision"],
  ["recall", "Recall"],
  ["f1", "F1"],
  ["precision_at_100", "Precision@100"],
  ["false_positive_rate", "False-positive rate"],
  ["sample_count", "Samples"],
  ["prevalence", "Prevalence"],
];

export function Models() {
  const [page, setPage] = useState(1);
  const navigate = useNavigate();
  const result = useApi((sig) => pipelineService.models(page, sig), [page], (d) => d.items.length === 0);
  return (
    <div className={p.page}>
      <PageHeader title="Models" lede="Registered XGBoost model versions with their training lineage and held-out metrics." actions={<EvidenceLabel kind="MODEL OUTPUT" />} />
      <div className={p.body}>
        <div className={ui.panel}>
          <StateView result={result} rows={6} empty="No model has been trained. Scores still compose from graph, behavioural and rule signals.">
            {(data) => (
              <>
                <div className={p.tableWrap}>
                  <div className={ui.tableScroll}><table className={ui.table}>
                    <thead>
                      <tr>
                        <th>Version</th>
                        <th>Features</th>
                        <th className={ui.right}>Test PR-AUC</th>
                        <th className={ui.right}>Threshold</th>
                        <th>Training dataset</th>
                        <th>Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.items.map((m) => {
                        const test = (m.evaluation_metrics as Record<string, Metrics>).test ?? {};
                        return (
                          <tr key={m.model_version} data-clickable="true" onClick={() => navigate(`/admin/models/${m.model_version}`)}>
                            <td>
                              <Link className="num" to={`/admin/models/${m.model_version}`}>
                                {m.model_version}
                              </Link>
                            </td>
                            <td>
                              {m.feature_version} · {m.feature_regime}
                            </td>
                            <td className={`num ${ui.right}`}>{score(test.pr_auc as number | null)}</td>
                            <td className={`num ${ui.right}`}>{m.operating_threshold}</td>
                            <td className="num">{shortId(m.training_dataset_id)}</td>
                            <td className="num">{dateTime(m.created_at)}</td>
                          </tr>
                        );
                      })}
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

export function ModelDetail() {
  const { version = "" } = useParams();
  const result = useApi((sig) => pipelineService.model(version, sig), [version]);
  return (
    <div className={p.page}>
      <StateView result={result} rows={8}>
        {(m) => {
          const ev = m.evaluation_metrics as Record<string, Metrics>;
          return (
            <>
              <PageHeader title={<span className="num">{m.model_version}</span>} lede={`${m.model_type} · feature ${m.feature_version} (${m.feature_regime}) · seed ${m.random_seed}`} actions={<EvidenceLabel kind="MODEL OUTPUT" />} />
              <div className={p.body}>
                <div className={p.tableWrap}>
                  <div className={ui.tableScroll}><table className={ui.table}>
                    <thead>
                      <tr>
                        <th>Metric</th>
                        <th className={ui.right}>Validation</th>
                        <th className={ui.right}>Test</th>
                      </tr>
                    </thead>
                    <tbody>
                      {METRICS.map(([k, label]) => (
                        <tr key={k}>
                          <td>{label}</td>
                          {(["validation", "test"] as const).map((split) => {
                            const v = ev[split]?.[k];
                            return (
                              <td key={split} className={`num ${ui.right}`}>
                                {typeof v === "number" ? (k === "sample_count" ? int(v) : score(v)) : "—"}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table></div>
                </div>
                <dl className={ui.kv}>
                  <dt>Operating threshold</dt>
                  <dd className="num">
                    {m.operating_threshold} <span className={p.muted}>({String(ev.operating_threshold_rule ?? "")})</span>
                  </dd>
                  <dt>Artifact SHA-256</dt>
                  <dd className="num">{m.artifact_sha256}</dd>
                  <dt>Implementation</dt>
                  <dd className="num">{m.implementation_version}</dd>
                  <dt>Created</dt>
                  <dd className="num">{dateTime(m.created_at)} UTC</dd>
                </dl>
                <div className={p.grid2}>
                  {(
                    [
                      ["Split boundaries", m.split_boundaries],
                      ["Class distribution", m.class_distribution],
                      ["Target definition", m.target_definition],
                      ["Training configuration", m.training_config],
                    ] as const
                  ).map(([title, data]) => (
                    <section key={title} className={ui.panel}>
                      <div className={ui.panelHead}>
                        <h2 className={ui.panelTitle}>{title}</h2>
                      </div>
                      <pre className={s.json}>{JSON.stringify(data, null, 2)}</pre>
                    </section>
                  ))}
                </div>
              </div>
            </>
          );
        }}
      </StateView>
    </div>
  );
}
