import { ArrowUpRight, Route } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { graphService } from "../api/graph";
import type { Neighborhood } from "../api/types";
import { TierChip } from "../components/bits";
import { EvidenceLabel } from "../components/EvidenceLabel";
import { FlowMatrix } from "../components/FlowMatrix";
import { GraphCanvas } from "../components/GraphCanvas";
import { LineageBadge } from "../components/LineageBadge";
import { StaleBanner, StateView } from "../components/StateView";
import ui from "../components/ui.module.css";
import { int, score, shortId } from "../lib/format";
import { useApi } from "../lib/useApi";
import { useUi } from "../state/ui";
import s from "./GraphExplorer.module.css";

const LIMITS = { depth: 3, max_nodes: 500, max_edges: 2000 }; // SRS §25.2 reference limits

function clampInt(value: string | null, fallback: number, maxValue: number): number {
  const n = Number(value);
  return Number.isInteger(n) && n >= 1 ? Math.min(n, maxValue) : fallback;
}

function SelectedPanel({ nb, selected, onClear }: { nb: Neighborhood; selected: string; onClear: () => void }) {
  const node = nb.nodes.find((n) => n.account_id === selected);
  const metrics = useApi((sig) => graphService.metrics(selected, sig), [selected]);
  if (!node) return null;
  const inbound = nb.edges.filter((e) => e.destination_account_id === selected);
  const outbound = nb.edges.filter((e) => e.source_account_id === selected);
  return (
    <>
      <div className={s.sideBlock}>
        <div className={ui.toolbar} style={{ justifyContent: "space-between", alignItems: "center" }}>
          <span className={s.sideRef}>{node.source_account_ref ?? node.account_id}</span>
          {selected !== nb.account_id && (
            <button type="button" className={`${ui.button} ${ui.ghost} ${ui.small}`} onClick={onClear}>
              Clear
            </button>
          )}
        </div>
        <dl className={ui.kv}>
          <dt>Account</dt>
          <dd className="num">{node.account_id}</dd>
          <dt>Score</dt>
          <dd>
            <span className="num">{score(node.risk_score)}</span> <TierChip tier={node.risk_tier} />
          </dd>
          <dt>Hop from focus</dt>
          <dd className="num">{node.hop}</dd>
          <dt>In / out here</dt>
          <dd className="num">
            {inbound.length} / {outbound.length}
          </dd>
        </dl>
        <div className={ui.toolbar}>
          <Link to={`/accounts/${encodeURIComponent(selected)}`} className={`${ui.button} ${ui.primary} ${ui.small}`}>
            <ArrowUpRight size={14} aria-hidden />
            Workspace
          </Link>
          {selected !== nb.account_id && (
            <Link to={`/paths?from=${encodeURIComponent(nb.account_id)}&to=${encodeURIComponent(selected)}`} className={`${ui.button} ${ui.small}`}>
              <Route size={14} aria-hidden />
              Trace from focus
            </Link>
          )}
        </div>
      </div>
      <div className={s.sideBlock}>
        <div className={ui.toolbar} style={{ justifyContent: "space-between", alignItems: "center" }}>
          <h2>Graph metrics</h2>
          <EvidenceLabel kind="ANALYTICAL SIGNAL" />
        </div>
        <StateView result={metrics} rows={5}>
          {(m) => (
            <dl className={ui.kv}>
              <dt>Degree (in / out)</dt>
              <dd className="num">
                {int(m.degree)} ({int(m.in_degree)} / {int(m.out_degree)})
              </dd>
              <dt>PageRank (norm.)</dt>
              <dd className="num">{score(m.pagerank_norm)}</dd>
              <dt>Betweenness</dt>
              <dd className="num">{m.betweenness_raw === null ? "—" : m.betweenness_raw.toExponential(2)}</dd>
              <dt>Component size</dt>
              <dd className="num">{int(m.component_size)}</dd>
              <dt>Community size</dt>
              <dd className="num">
                {int(m.community_size)} {m.community_id && <Link to={`/communities/${m.community_id}`}>{shortId(m.community_id)}</Link>}
              </dd>
              <dt>Engine</dt>
              <dd className="num">{m.analytics_version}</dd>
            </dl>
          )}
        </StateView>
      </div>
    </>
  );
}

export function GraphExplorer() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const remembered = useUi((st) => st.explorerAccount);
  const focusExplorer = useUi((st) => st.focusExplorer);
  const account = params.get("account") ?? remembered ?? "";
  const depth = clampInt(params.get("depth"), 2, LIMITS.depth);
  const maxNodes = clampInt(params.get("max_nodes"), 100, LIMITS.max_nodes);
  const maxEdges = clampInt(params.get("max_edges"), 500, LIMITS.max_edges);
  const view = params.get("view") === "matrix" ? "matrix" : "graph";
  const [draft, setDraft] = useState({ account, depth: String(depth), maxNodes: String(maxNodes), maxEdges: String(maxEdges) });
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    if (account) focusExplorer(account);
    setSelected(null);
  }, [account, focusExplorer]);

  const result = useApi(account ? (sig) => graphService.neighborhood({ account_id: account, depth, max_nodes: maxNodes, max_edges: maxEdges }, sig) : null, [account, depth, maxNodes, maxEdges]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const next = new URLSearchParams(params);
    next.set("account", draft.account.trim());
    next.set("depth", draft.depth);
    next.set("max_nodes", draft.maxNodes);
    next.set("max_edges", draft.maxEdges);
    setParams(next);
  };
  const setView = (v: "graph" | "matrix") => {
    const next = new URLSearchParams(params);
    next.set("view", v);
    setParams(next, { replace: true });
  };
  const refocus = (id: string) => {
    const next = new URLSearchParams(params);
    next.set("account", id);
    setDraft((d) => ({ ...d, account: id }));
    setParams(next);
  };

  return (
    <div className={s.page}>
      <form className={s.bar} onSubmit={submit}>
        <label className={`${ui.field} ${s.grow}`}>
          <span className={ui.label}>Focus account ID</span>
          <input className={ui.input} value={draft.account} placeholder="dataset:C1231006815" onChange={(e) => setDraft({ ...draft, account: e.target.value })} />
        </label>
        <label className={ui.field}>
          <span className={ui.label}>Hops</span>
          <select className={ui.select} value={draft.depth} onChange={(e) => setDraft({ ...draft, depth: e.target.value })}>
            {[1, 2, 3].map((d) => (
              <option key={d}>{d}</option>
            ))}
          </select>
        </label>
        <label className={ui.field}>
          <span className={ui.label}>Max accounts</span>
          <input className={`${ui.input} ${s.num}`} type="number" min={1} max={LIMITS.max_nodes} value={draft.maxNodes} onChange={(e) => setDraft({ ...draft, maxNodes: e.target.value })} />
        </label>
        <label className={ui.field}>
          <span className={ui.label}>Max transfers</span>
          <input className={`${ui.input} ${s.num}`} type="number" min={1} max={LIMITS.max_edges} value={draft.maxEdges} onChange={(e) => setDraft({ ...draft, maxEdges: e.target.value })} />
        </label>
        <button type="submit" className={`${ui.button} ${ui.primary}`} disabled={!draft.account.trim()}>
          Load
        </button>
        <div className={s.segmented} role="group" aria-label="View">
          <button type="button" aria-pressed={view === "graph"} onClick={() => setView("graph")}>
            Graph
          </button>
          <button type="button" aria-pressed={view === "matrix"} onClick={() => setView("matrix")}>
            Flow matrix
          </button>
        </div>
      </form>
      <div className={s.status}>
        {result.data ? (
          <>
            <EvidenceLabel kind="FACT" />
            <span>
              Snapshot <span className="num">{shortId(result.data.graph_snapshot_id)}</span>
            </span>
            <span>
              Applied: {result.data.applied_limits.depth} hops · {int(result.data.applied_limits.max_nodes)} accounts · {int(result.data.applied_limits.max_edges)} transfers · {result.data.applied_limits.query_timeout_seconds}s timeout
            </span>
            {result.data.truncated && <span className={s.warn}>Truncated breadth-first by hop and amount: more accounts exist beyond these limits.</span>}
            <LineageBadge lineage={result.data.lineage} computedAt={result.data.computed_at} isStale={result.data.is_stale} />
          </>
        ) : (
          <span>Bounded neighbourhood of the active graph snapshot. Limits: up to 3 hops, 500 accounts, 2,000 transfers (§25.2).</span>
        )}
      </div>
      <div className={s.stage}>
        {!account ? (
          <div className={s.empty} data-state="EMPTY">
            <h1>Choose an account to explore</h1>
            <p>Enter a full account ID, or open one from Triage or Accounts. The graph shows aggregated transfers between accounts, nearest hops first.</p>
          </div>
        ) : (
          <StateView result={result} rows={10} empty="This account has no transfers in the snapshot." unavailable="The graph store is unavailable. Risk and case data remain readable.">
            {(nb) => (
              <>
                <StaleBanner isStale={nb.is_stale} />
                {view === "graph" ? (
                  <GraphCanvas nodes={nb.nodes} edges={nb.edges} focusId={nb.account_id} selectedId={selected} onSelect={setSelected} onOpen={refocus} />
                ) : (
                  <FlowMatrix nodes={nb.nodes} edges={nb.edges} focusId={nb.account_id} onSelect={setSelected} />
                )}
              </>
            )}
          </StateView>
        )}
      </div>
      <aside className={s.side} aria-label="Selection">
        {result.data ? (
          <SelectedPanel nb={result.data} selected={selected ?? result.data.account_id} onClear={() => setSelected(null)} />
        ) : (
          <div className={s.sideBlock}>
            <p className={ui.hint}>Click an account to inspect it; double-click (or Enter) to re-centre the graph on it.</p>
            <button type="button" className={`${ui.button} ${ui.ghost} ${ui.small}`} onClick={() => navigate("/")}>
              Back to triage
            </button>
          </div>
        )}
      </aside>
    </div>
  );
}
