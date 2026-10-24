/**
 * Flow matrix: the neighbourhood as an adjacency heatmap. Rows send, columns receive; cell shade is the
 * aggregated amount (log scale). Row and column swatches carry each account's risk on the shared ramp,
 * so blocks of hot senders feeding a few receivers (fan-in) or the reverse (fan-out) stand out.
 */
import { interpolateRgb, max, scaleLog } from "d3";
import { useEffect, useMemo, useRef, useState } from "react";
import type { NeighborhoodEdge, NeighborhoodNode } from "../api/types";
import { amount, compactAmount } from "../lib/format";
import { ramp } from "../lib/ramp";
import s from "./FlowMatrix.module.css";

const MAX_ACCOUNTS = 40;
const shade = interpolateRgb("#1b2531", "#f2f5f8");

export function FlowMatrix({ nodes, edges, focusId, onSelect }: { nodes: NeighborhoodNode[]; edges: NeighborhoodEdge[]; focusId: string; onSelect?: (id: string) => void }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const measure = () => setWidth(el.clientWidth);
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const { order, cells, scale, dropped, lo, hi } = useMemo(() => {
    const degree = new Map<string, number>();
    for (const e of edges) {
      degree.set(e.source_account_id, (degree.get(e.source_account_id) ?? 0) + 1);
      degree.set(e.destination_account_id, (degree.get(e.destination_account_id) ?? 0) + 1);
    }
    const ranked = [...nodes].sort((a, b) => (a.account_id === focusId ? -1 : b.account_id === focusId ? 1 : (degree.get(b.account_id) ?? 0) - (degree.get(a.account_id) ?? 0) || (a.account_id < b.account_id ? -1 : 1)));
    const kept = ranked.slice(0, MAX_ACCOUNTS);
    const ordered = [...kept].sort((a, b) => a.hop - b.hop || (a.community_id ?? "").localeCompare(b.community_id ?? "") || a.account_id.localeCompare(b.account_id));
    const idx = new Map(ordered.map((n, i) => [n.account_id, i]));
    const c = edges.filter((e) => idx.has(e.source_account_id) && idx.has(e.destination_account_id));
    const amounts = c.map((e) => Number(e.total_amount)).filter((v) => v > 0);
    const lo = Math.max(Math.min(...amounts, 1), 0.01);
    const hi = Math.max(max(amounts) ?? 1, lo * 10);
    return { order: ordered, cells: c.map((e) => ({ e, r: idx.get(e.source_account_id)!, c: idx.get(e.destination_account_id)! })), scale: scaleLog().domain([lo, hi]).range([0, 1]).clamp(true), dropped: nodes.length - kept.length, lo, hi };
  }, [nodes, edges, focusId]);

  const n = order.length;
  const label = 112;
  // fill the available width, within legible bounds
  const cell = Math.max(14, Math.min(30, Math.floor(((width || 800) - label - 40) / Math.max(n, 1))));
  const size = label + n * cell;
  const overflows = width > 0 && size + 8 > width;

  return (
    <div className={s.wrap} ref={wrapRef}>
      <div className={s.head}>
        <p className={s.note}>
          Rows send, columns receive. Shade is the aggregated amount (log scale); the swatch beside each account is its risk score.
          {dropped > 0 && ` Showing the ${MAX_ACCOUNTS} most connected of ${nodes.length} accounts.`}
        </p>
        <span className={s.key} aria-label={`Amount scale from ${compactAmount(lo)} to ${compactAmount(hi)}`}>
          <span className="num">{compactAmount(lo)}</span>
          <span className={s.keyBar} style={{ background: `linear-gradient(90deg, ${shade(0.15)}, ${shade(1)})` }} aria-hidden />
          <span className="num">{compactAmount(hi)}</span>
        </span>
      </div>
      {overflows && <p className={s.cue}>Scroll sideways to see every receiving account →</p>}
      <div className={s.scroller}>
      <svg className={s.svg} width={size + 8} height={size + 8} role="img" aria-label={`Flow matrix of ${n} accounts and ${cells.length} aggregated transfers`}>
        {order.map((node, i) => {
          const ref = node.source_account_ref ?? node.account_id;
          const isFocus = node.account_id === focusId;
          return (
            <g key={node.account_id} style={{ cursor: "pointer" }} onClick={() => onSelect?.(node.account_id)}>
              <text x={label - 10} y={label + i * cell + cell * 0.68} textAnchor="end" className={`${s.entity} ${isFocus ? s.focus : ""}`}>
                {ref.length > 11 ? `${ref.slice(0, 10)}…` : ref}
              </text>
              <rect x={label - 7} y={label + i * cell + 1} width={5} height={cell - 2} fill={ramp(node.risk_score)} />
              <text transform={`translate(${label + i * cell + cell * 0.68},${label - 10}) rotate(-60)`} className={`${s.entity} ${isFocus ? s.focus : ""}`}>
                {ref.length > 11 ? `${ref.slice(0, 10)}…` : ref}
              </text>
              <rect x={label + i * cell + 1} y={label - 7} width={cell - 2} height={5} fill={ramp(node.risk_score)} />
            </g>
          );
        })}
        <rect x={label} y={label} width={n * cell} height={n * cell} fill="#0e131a" />
        {cells.map(({ e, r, c }) => (
          <rect
            key={`${r}-${c}`}
            className={s.cell}
            x={label + c * cell + 0.5}
            y={label + r * cell + 0.5}
            width={cell - 1}
            height={cell - 1}
            fill={shade(0.15 + 0.85 * scale(Math.max(Number(e.total_amount), 0.01)))}
          >
            <title>{`${e.source_account_id} → ${e.destination_account_id}: ${e.tx_count} transactions, ${amount(e.total_amount)}`}</title>
          </rect>
        ))}
      </svg>
      </div>
    </div>
  );
}
