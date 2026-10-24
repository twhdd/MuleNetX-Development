import { ArrowUpRight, FolderPlus, Network } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { accountService } from "../api/accounts";
import { ApiError } from "../api/client";
import { graphService } from "../api/graph";
import { riskService } from "../api/risk";
import type { Account, Assessment, Shap } from "../api/types";
import { RampLegend } from "../components/bits";
import { Decomposition } from "../components/Decomposition";
import { EvidenceLabel } from "../components/EvidenceLabel";
import { GraphCanvas } from "../components/GraphCanvas";
import { SignalMatrix, type MatrixRow } from "../components/SignalMatrix";
import { Skeleton, StateView } from "../components/StateView";
import ui from "../components/ui.module.css";
import { int } from "../lib/format";
import { openCaseForAccount } from "../lib/openCase";
import { pool } from "../lib/pool";
import { useApi } from "../lib/useApi";
import { useActiveContext } from "../state/context";
import { useSession } from "../state/session";
import { useUi } from "../state/ui";
import s from "./Triage.module.css";

const QUEUE_SIZE = 25;

function useQueue(enabled: boolean) {
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [total, setTotal] = useState(0);
  const [assessments, setAssessments] = useState<Record<string, Assessment | null>>({});
  const [error, setError] = useState<Error | null>(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    setError(null);
    setAccounts(null);
    setAssessments({});
    accountService
      .search({ sort: "risk_score", order: "desc", page_size: QUEUE_SIZE }, controller.signal)
      .then(async (page) => {
        if (controller.signal.aborted) return;
        setAccounts(page.items);
        setTotal(page.total);
        await pool(page.items, 6, async (acc) => {
          try {
            const a = await riskService.risk(acc.account_id, controller.signal);
            if (!controller.signal.aborted) setAssessments((prev) => ({ ...prev, [acc.account_id]: a }));
          } catch (err) {
            if (!controller.signal.aborted && (err as Error).name !== "AbortError") setAssessments((prev) => ({ ...prev, [acc.account_id]: null }));
          }
        });
      })
      .catch((err: Error) => {
        if (!controller.signal.aborted && err.name !== "AbortError") setError(err);
      });
    return () => controller.abort();
  }, [enabled, tick]);
  const rows: MatrixRow[] = (accounts ?? []).map((account) => ({
    account,
    assessment: assessments[account.account_id] ?? null,
    error: assessments[account.account_id] === null,
  }));
  return { accounts, rows, total, error, reload: () => setTick((t) => t + 1) };
}

function NoContext() {
  const role = useSession((st) => st.user?.role);
  return (
    <div className={s.emptyTeach} data-state="EMPTY">
      <h1>No active dataset yet</h1>
      <p>Triage ranks the accounts of the active analytical context. A context exists once a dataset has been ingested and its pipeline has reached READY.</p>
      <ol>
        <li>An administrator uploads a PaySim CSV under Ingestion.</li>
        <li>The pipeline profiles it, builds the graph, computes features, trains the model and scores every account.</li>
        <li>When the run reaches READY, this screen fills with the highest-risk accounts.</li>
      </ol>
      {role === "ADMIN" && (
        <Link to="/admin/ingestion" className={`${ui.button} ${ui.primary}`} style={{ alignSelf: "flex-start" }}>
          Go to ingestion
        </Link>
      )}
    </div>
  );
}

export function Triage() {
  const context = useActiveContext((st) => st.context);
  const active = context?.is_active ?? false;
  const navigate = useNavigate();
  const selected = useUi((st) => st.triageAccount);
  const select = useUi((st) => st.selectTriage);
  const queue = useQueue(active);
  const [opening, setOpening] = useState(false);
  const [openError, setOpenError] = useState<string | null>(null);

  useEffect(() => {
    if (queue.accounts && queue.accounts.length > 0 && (!selected || !queue.accounts.some((a) => a.account_id === selected))) {
      select(queue.accounts[0]!.account_id);
    }
  }, [queue.accounts, selected, select]);

  const selectedAccount = useMemo(() => queue.accounts?.find((a) => a.account_id === selected) ?? null, [queue.accounts, selected]);

  const neighborhood = useApi(selected && active ? (sig) => graphService.neighborhood({ account_id: selected, depth: 2 }, sig) : null, [selected, active]);
  const risk = useApi(selected && active ? (sig) => riskService.risk(selected, sig) : null, [selected, active]);
  const shap = useApi<Shap | null>(
    selected && active
      ? async (sig) => {
          try {
            return await riskService.shap(selected, 6, sig);
          } catch (err) {
            if (err instanceof ApiError && (err.status === 404 || err.status === 409 || err.status === 503)) return null;
            throw err;
          }
        }
      : null,
    [selected, active],
  );

  if (context && !context.is_active) return <NoContext />;

  const openWorkspace = (id: string) => navigate(`/accounts/${encodeURIComponent(id)}`);
  const openCase = async () => {
    if (!selectedAccount) return;
    setOpening(true);
    setOpenError(null);
    try {
      const caseId = await openCaseForAccount(selectedAccount.account_id, selectedAccount.source_account_ref, selectedAccount.risk_tier);
      navigate(`/cases/${caseId}`);
    } catch (err) {
      setOpenError((err as Error).message);
      setOpening(false);
    }
  };

  return (
    <div className={s.page}>
      <section className={s.col} aria-labelledby="queue-h">
        <div className={s.colHead}>
          <div>
            <h2 id="queue-h">Signal matrix</h2>
            <span className={s.colSub}>Top {QUEUE_SIZE} of {int(queue.total)} accounts by final score</span>
          </div>
          <EvidenceLabel kind="MODEL OUTPUT" />
        </div>
        <div className={s.scroll}>
          {queue.error ? (
            <StateView result={{ state: "ERROR", data: null, error: queue.error, reload: queue.reload }}>{() => null}</StateView>
          ) : !queue.accounts ? (
            <Skeleton rows={10} />
          ) : queue.accounts.length === 0 ? (
            <StateView result={{ state: "EMPTY", data: null, error: null, reload: queue.reload }} empty="The active scoring run has no scored accounts.">
              {() => null}
            </StateView>
          ) : (
            <SignalMatrix rows={queue.rows} selectedId={selected} onSelect={select} onOpen={openWorkspace} />
          )}
        </div>
        <div className={s.foot}>
          <RampLegend low="0 low" high="1 high" />
          <Link to="/accounts" className={`${ui.button} ${ui.ghost} ${ui.small}`}>
            All accounts
          </Link>
        </div>
      </section>

      <section className={`${s.col} ${s.center}`} aria-labelledby="graph-h">
        <div className={s.colHead}>
          <div className={s.graphTitle}>
            <h2 id="graph-h" className="visually-hidden">
              Money graph
            </h2>
            {selectedAccount ? <span className="entity">{selectedAccount.source_account_ref}</span> : <span className={s.colSub}>Select an account</span>}
            <span className={`${s.colSub} ${s.optional}`}>two hops · aggregated transfers</span>
            {neighborhood.data?.truncated && (
              <span
                className={s.truncated}
                title={`Truncated at ${neighborhood.data.applied_limits.max_nodes} accounts / ${neighborhood.data.applied_limits.max_edges} transfers`}
                aria-label={`Truncated at ${neighborhood.data.applied_limits.max_nodes} accounts and ${neighborhood.data.applied_limits.max_edges} transfers`}
              >
                Truncated · {neighborhood.data.applied_limits.max_nodes} / {neighborhood.data.applied_limits.max_edges}
              </span>
            )}
          </div>
          {selected && (
            <Link to={`/graph?account=${encodeURIComponent(selected)}`} className={`${ui.button} ${ui.small}`}>
              <Network size={14} aria-hidden />
              Explore
            </Link>
          )}
        </div>
        <div className={s.graph}>
          {selected ? (
            <StateView result={neighborhood} rows={8} empty="This account has no transfers in the active snapshot.">
              {(nb) => <GraphCanvas nodes={nb.nodes} edges={nb.edges} focusId={nb.account_id} onSelect={select} onOpen={openWorkspace} />}
            </StateView>
          ) : (
            <Skeleton rows={6} />
          )}
        </div>
      </section>

      <aside className={`${s.col} ${s.right}`} aria-label="Score decomposition">
        {selected ? (
          <StateView result={risk} rows={10} unavailable="No risk assessment exists for this account in the active scoring run.">
            {(a) => (
              <Decomposition
                label={selectedAccount?.source_account_ref ?? a.account_id}
                assessment={a}
                shap={shap.data}
                shapNote={shap.state === "LOADING" ? "Loading explanation…" : a.ml_score === null ? "The ML component was unavailable, so there is nothing to explain." : null}
                actions={
                  <>
                    <button type="button" className={`${ui.button} ${ui.primary}`} onClick={() => openWorkspace(a.account_id)}>
                      <ArrowUpRight size={15} aria-hidden />
                      Open workspace
                    </button>
                    <button type="button" className={ui.button} onClick={openCase} disabled={opening}>
                      <FolderPlus size={15} aria-hidden />
                      {opening ? "Opening…" : "Open case"}
                    </button>
                    {openError && <span className={ui.error}>{openError}</span>}
                  </>
                }
              />
            )}
          </StateView>
        ) : (
          <Skeleton rows={10} />
        )}
      </aside>
    </div>
  );
}
