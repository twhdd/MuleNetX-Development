import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { communityService } from "../api/graph";
import { AccountLink, PageHeader, Paginator, ScoreBar, TierChip } from "../components/bits";
import { EvidenceLabel } from "../components/EvidenceLabel";
import { LineageBadge } from "../components/LineageBadge";
import { StaleBanner, StateView } from "../components/StateView";
import ui from "../components/ui.module.css";
import { dateTime, int, shortId } from "../lib/format";
import { useApi } from "../lib/useApi";
import p from "./page.module.css";

export function Communities() {
  const [page, setPage] = useState(1);
  const navigate = useNavigate();
  const result = useApi((sig) => communityService.list(page, sig), [page], (d) => d.items.length === 0);
  return (
    <div className={p.page}>
      <PageHeader title="Communities" lede="Louvain communities of the active analytics run, largest first. Membership is a structural grouping, not evidence of a ring." actions={<EvidenceLabel kind="ANALYTICAL SIGNAL" />} />
      <div className={p.body}>
        <div className={ui.panel}>
          <StateView result={result} rows={10} empty="The active analytics run produced no communities.">
            {(data) => (
              <>
                <StaleBanner isStale={data.is_stale} />
                <div className={ui.panelHead}>
                  <span className={`${p.muted} ${p.small}`}>Analytics run {shortId(data.lineage.analytics_run_id)}</span>
                  <LineageBadge lineage={data.lineage} computedAt={data.computed_at} isStale={data.is_stale} />
                </div>
                <div className={p.tableWrap}>
                  <div className={ui.tableScroll}><table className={ui.table}>
                    <thead>
                      <tr>
                        <th>Community</th>
                        <th className={ui.right}>Members</th>
                        <th>Algorithm</th>
                        <th>Computed</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.items.map((c) => (
                        <tr key={c.community_id} data-clickable="true" onClick={() => navigate(`/communities/${c.community_id}`)}>
                          <td>
                            <Link to={`/communities/${c.community_id}`} className="num">
                              {c.community_id}
                            </Link>
                          </td>
                          <td className={`num ${ui.right}`}>{int(c.member_count)}</td>
                          <td>
                            {c.algorithm} <span className={p.muted}>{c.algorithm_version}</span>
                          </td>
                          <td className="num">{dateTime(c.computed_at)}</td>
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

export function CommunityDetail() {
  const { id = "" } = useParams();
  const [page, setPage] = useState(1);
  const result = useApi((sig) => communityService.get(id, page, sig), [id, page]);
  return (
    <div className={p.page}>
      <StateView result={result} rows={10}>
        {(c) => (
          <>
            <StaleBanner isStale={c.is_stale} />
            <PageHeader
              title={
                <>
                  Community <span className="num">{shortId(c.community_id)}</span>
                </>
              }
              lede={c.interpretation}
              actions={
                <>
                  <EvidenceLabel kind="ANALYTICAL SIGNAL" />
                  <LineageBadge lineage={c.lineage} isStale={c.is_stale} />
                </>
              }
            />
            <div className={p.body}>
              <dl className={ui.kv}>
                <dt>Members</dt>
                <dd className="num">{int(c.member_count)}</dd>
                <dt>Algorithm</dt>
                <dd>
                  {c.algorithm} {c.algorithm_version}
                </dd>
                <dt>Snapshot</dt>
                <dd className="num">{c.graph_snapshot_id}</dd>
                <dt>Computed</dt>
                <dd className="num">{dateTime(c.computed_at)} UTC</dd>
              </dl>
              <div className={ui.panel}>
                <div className={ui.tableScroll}><table className={ui.table}>
                  <thead>
                    <tr>
                      <th>Member</th>
                      <th>Type</th>
                      <th>Tier</th>
                      <th style={{ width: 220 }}>Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {c.members.items.map((m) => (
                      <tr key={m.account_id}>
                        <td>
                          <AccountLink id={m.account_id}>{m.source_account_ref ?? m.account_id}</AccountLink>
                        </td>
                        <td>{m.account_type ?? "—"}</td>
                        <td>
                          <TierChip tier={m.risk_tier} />
                        </td>
                        <td>
                          <ScoreBar value={m.risk_score} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table></div>
                <Paginator page={c.members.page} pageSize={c.members.page_size} total={c.members.total} capped={c.members.total_is_capped} onPage={setPage} />
              </div>
            </div>
          </>
        )}
      </StateView>
    </div>
  );
}
