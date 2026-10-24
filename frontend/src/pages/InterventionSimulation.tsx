/**
 * Network intervention simulation (SRS §16A, §19.15, §20.6). Every result is labelled Hypothetical Simulation;
 * no control here maps to a real blocking, freezing or rerouting action.
 */
import { FlaskConical, Info } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { interventionService, type OperationType } from "../api/interventions";
import { ringService } from "../api/rings";
import type { Scenario } from "../api/types";
import { AccountLink, PageHeader, Paginator, ScoreBar } from "../components/bits";
import { EvidenceLabel } from "../components/EvidenceLabel";
import { Running, StateView } from "../components/StateView";
import ui from "../components/ui.module.css";
import { amount, dateTime, humanize, int, percent, shortId } from "../lib/format";
import { useApi } from "../lib/useApi";
import p from "./page.module.css";
import s from "./InterventionSimulation.module.css";

const TYPES: OperationType[] = ["ACCOUNT_REMOVAL", "INTERMEDIARY_REMOVAL", "ACCOUNT_SET_REMOVAL", "EDGE_REMOVAL"];

function Results({ scenarioId }: { scenarioId: string }) {
  const [page, setPage] = useState(1);
  const scenario = useApi((sig) => interventionService.get(scenarioId, sig), [scenarioId]);
  const pending = scenario.data && (scenario.data.status === "QUEUED" || scenario.data.status === "RUNNING");
  useEffect(() => {
    if (!pending) return;
    const t = window.setInterval(scenario.reload, 2500);
    return () => window.clearInterval(t);
  }, [pending, scenario.reload]);
  const done = scenario.data?.status === "COMPLETED";
  const candidates = useApi(done ? (sig) => interventionService.candidates(scenarioId, page, sig) : null, [scenarioId, page, done]);
  return (
    <section className={ui.panel} aria-label="Simulation results">
      <div className={ui.panelHead}>
        <h2 className={ui.panelTitle}>Scenario {shortId(scenarioId)}</h2>
        <EvidenceLabel kind="HYPOTHETICAL SIMULATION" />
      </div>
      <StateView result={scenario} rows={4}>
        {(sc: Scenario) => (
          <div className={p.stack} style={{ padding: "var(--sp-4)" }}>
            <p className={`${p.muted} ${p.small}`}>{sc.statement}</p>
            {sc.status === "QUEUED" && <Running label="Queued" queued />}
            {sc.status === "RUNNING" && <Running label="Simulating" />}
            {sc.status === "FAILED" && <p className={ui.error}>Simulation failed: {sc.error_summary}</p>}
            {done && (
              <>
                {sc.metrics_are_lower_bounds && (
                  <div className={ui.notice} role="note">
                    Baseline path enumeration reached its analytical bound: every figure below is a lower bound.
                  </div>
                )}
                <div className={s.baseline}>
                  <div className={s.stat}>
                    <span>Suspicious flow (baseline)</span>
                    <span className="num">{amount(sc.baseline.suspicious_flow as string)}</span>
                  </div>
                  <div className={s.stat}>
                    <span>Qualifying paths</span>
                    <span className="num">{int(sc.baseline.suspicious_paths as number)}</span>
                  </div>
                  <div className={s.stat}>
                    <span>Reachable suspicious pairs</span>
                    <span className="num">{int(sc.baseline.reachable_suspicious_pairs as number)}</span>
                  </div>
                  <div className={s.stat}>
                    <span>Risk mass</span>
                    <span className="num">{Number(sc.baseline.risk_mass).toFixed(3)}</span>
                  </div>
                </div>
                <StateView result={candidates} rows={6} empty="No candidate: the ring has no qualifying paths in this context.">
                  {(data) => (
                    <>
                      <div className={p.tableWrap}>
                        <div className={ui.tableScroll}><table className={ui.table}>
                          <thead>
                            <tr>
                              <th>Rank</th>
                              <th>Hypothetical change</th>
                              <th>Targets</th>
                              <th style={{ width: 170 }}>Intervention score</th>
                              <th className={ui.right}>Flow disrupted</th>
                              <th className={ui.right}>Risk reduction</th>
                              <th className={ui.right}>Connectivity</th>
                              <th className={ui.right}>Paths</th>
                              <th className={ui.right}>Alternatives</th>
                            </tr>
                          </thead>
                          <tbody>
                            {data.items.map((c) => (
                              <tr key={c.candidate_id}>
                                <td className="num">{c.rank_position}</td>
                                <td>{humanize(c.operation_type)}</td>
                                <td style={{ whiteSpace: "normal" }}>
                                  {c.operation_type === "EDGE_REMOVAL" ? (
                                    <span className="num">{c.target_ids[0]}</span>
                                  ) : (
                                    c.target_ids.map((t) => <AccountLink key={t} id={t} />)
                                  )}
                                </td>
                                <td>
                                  <ScoreBar value={c.intervention_score} />
                                </td>
                                <td className={`num ${ui.right}`}>{percent(c.flow_disruption_percentage, 1)}</td>
                                <td className={`num ${ui.right}`}>{percent(c.normalized_risk_reduction, 1)}</td>
                                <td className={`num ${ui.right}`}>{percent(c.normalized_connectivity_disruption, 1)}</td>
                                <td className={`num ${ui.right}`}>
                                  {int(c.residual_suspicious_paths)} left
                                </td>
                                <td className={`num ${ui.right}`}>{int(c.alternative_path_ids.length)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table></div>
                      </div>
                      <Paginator page={data.page} pageSize={data.page_size} total={data.total} capped={data.total_is_capped} onPage={setPage} />
                    </>
                  )}
                </StateView>
              </>
            )}
          </div>
        )}
      </StateView>
    </section>
  );
}

export function InterventionSimulation() {
  const { id = "" } = useParams();
  const ring = useApi((sig) => ringService.get(id, sig), [id]);
  const members = useApi((sig) => ringService.accounts(id, 1, sig), [id]);
  const [history, setHistory] = useState(0);
  const scenarios = useApi((sig) => interventionService.ofRing(id, 1, sig), [id, history], (d) => d.items.length === 0);
  const [mode, setMode] = useState<"RANK" | "EVALUATE">("RANK");
  const [type, setType] = useState<OperationType>("ACCOUNT_SET_REMOVAL");
  const [targets, setTargets] = useState<string[]>([]);
  const [edge, setEdge] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const toggle = (a: string) => setTargets((t) => (t.includes(a) ? t.filter((x) => x !== a) : [...t, a]));
  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const body = mode === "RANK" ? { mode } : { mode, intervention_type: type, target_ids: type === "EDGE_REMOVAL" ? [edge.trim()] : targets };
      const res = await interventionService.simulate(id, body);
      setSelected(res.scenario_id);
      setHistory((h) => h + 1);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) setError("You already have two simulations queued or running. Wait for one to finish.");
      else if (err instanceof ApiError && err.code === "INTERVENTION_TARGET_INVALID") setError(`Targets not valid for this ring: ${err.message}`);
      else setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={p.page}>
      <PageHeader
        title={
          <>
            Simulate disruption · <span className="entity">Ring {shortId(id)}</span>
          </>
        }
        lede={
          <>
            Counterfactual graph analysis on the ring's qualifying paths. <Link to={`/rings/${id}`}>Back to the ring</Link>
          </>
        }
        actions={<EvidenceLabel kind="HYPOTHETICAL SIMULATION" />}
      />
      <div className={p.body}>
        <div className={s.banner} role="note">
          <Info size={16} aria-hidden />
          <span>
            Simulation only. MuleNetX never blocks, freezes, rejects or reroutes any real account, transaction or payment. Results estimate the analytical effect of removing accounts or links from the graph and are not recommendations to act.
          </span>
        </div>
        <StateView result={ring} rows={2}>
          {(r) =>
            r.candidate_class !== "POTENTIAL_FRAUD_RING_CANDIDATE" ? (
              <p className={p.muted}>Simulation is available for potential fraud ring candidates only.</p>
            ) : (
              <section className={ui.panel}>
                <div className={ui.panelHead}>
                  <h2 className={ui.panelTitle}>New simulation</h2>
                </div>
                <div className={s.form}>
                  <div className={s.segmented} role="group" aria-label="Mode">
                    <button type="button" aria-pressed={mode === "RANK"} onClick={() => setMode("RANK")}>
                      Rank every candidate
                    </button>
                    <button type="button" aria-pressed={mode === "EVALUATE"} onClick={() => setMode("EVALUATE")}>
                      Evaluate my choice
                    </button>
                  </div>
                  {mode === "EVALUATE" && (
                    <label className={ui.field}>
                      <span className={ui.label}>Hypothetical change</span>
                      <select className={ui.select} value={type} onChange={(e) => { setType(e.target.value as OperationType); setTargets([]); }}>
                        {TYPES.map((t) => (
                          <option key={t} value={t}>
                            {humanize(t)}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                  <button type="button" className={`${ui.button} ${ui.primary}`} disabled={busy || (mode === "EVALUATE" && (type === "EDGE_REMOVAL" ? !edge.trim() : targets.length === 0))} onClick={() => void submit()}>
                    <FlaskConical size={15} aria-hidden />
                    {busy ? "Queuing…" : "Run simulation"}
                  </button>
                  {error && <span className={ui.error} role="alert">{error}</span>}
                </div>
                {mode === "EVALUATE" && type !== "EDGE_REMOVAL" && (
                  <div className={s.form} style={{ paddingTop: 0 }}>
                    <span className={ui.label}>Accounts to remove from the simulated graph {type === "ACCOUNT_SET_REMOVAL" ? "(1–3)" : "(exactly 1)"}</span>
                    <div className={s.targets}>
                      {(members.data?.items ?? []).map((m) => (
                        <button key={m.account_id} type="button" className={s.target} aria-pressed={targets.includes(m.account_id)} onClick={() => toggle(m.account_id)}>
                          {m.source_account_ref ?? m.account_id}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {mode === "EVALUATE" && type === "EDGE_REMOVAL" && (
                  <div className={s.form} style={{ paddingTop: 0 }}>
                    <label className={ui.field} style={{ minWidth: 360 }}>
                      <span className={ui.label}>Link to remove (source&gt;destination account IDs)</span>
                      <input className={ui.input} value={edge} onChange={(e) => setEdge(e.target.value)} placeholder="ds:C1>ds:C2" />
                    </label>
                  </div>
                )}
              </section>
            )
          }
        </StateView>
        {selected && <Results key={selected} scenarioId={selected} />}
        <section className={ui.panel}>
          <div className={ui.panelHead}>
            <h2 className={ui.panelTitle}>Earlier simulations of this ring</h2>
          </div>
          <StateView result={scenarios} rows={3} empty="No simulation yet.">
            {(data) => (
              <div className={p.tableWrap}>
              <div className={ui.tableScroll}><table className={ui.table}>
                <thead>
                  <tr>
                    <th>Scenario</th>
                    <th>Mode</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((sc) => (
                    <tr key={sc.scenario_id} aria-selected={sc.scenario_id === selected}>
                      <td className="num">{shortId(sc.scenario_id)}</td>
                      <td>
                        {sc.mode === "RANK" ? "Rank" : `Evaluate · ${humanize(sc.intervention_type)}`}
                      </td>
                      <td>{humanize(sc.status)}</td>
                      <td className="num">{dateTime(sc.created_at)}</td>
                      <td className={ui.right}>
                        <button type="button" className={`${ui.button} ${ui.small}`} onClick={() => setSelected(sc.scenario_id)}>
                          Show results
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table></div>
              </div>
            )}
          </StateView>
        </section>
      </div>
    </div>
  );
}
