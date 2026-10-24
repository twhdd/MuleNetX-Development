/** D3 neighbourhood graph: ramp-filled nodes on hop rings, edge width by aggregated amount. */
import { max, scaleSqrt, select, zoom, zoomIdentity, type ZoomBehavior } from "d3";
import { Maximize2, Minus, Plus } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { NeighborhoodEdge, NeighborhoodNode } from "../api/types";
import { compactAmount, int, score } from "../lib/format";
import { bounds, layout, RING_GAP, type Bounds, type LayoutLink, type LayoutNode } from "../lib/layout";
import { ramp } from "../lib/ramp";
import s from "./GraphCanvas.module.css";

interface Props {
  nodes: NeighborhoodNode[];
  edges: NeighborhoodEdge[];
  focusId: string;
  selectedId?: string | null;
  onSelect?: (id: string) => void;
  onOpen?: (id: string) => void;
  /** Accounts to emphasise (e.g. a path); others are dimmed. */
  highlight?: Set<string> | null;
  labelAll?: boolean;
}

function fit(svg: SVGSVGElement, box: Bounds) {
  const { width: w, height: h } = svg.getBoundingClientRect();
  const k = Math.min(1.6, Math.min(w / Math.max(box.width, 1), h / Math.max(box.height, 1)));
  return zoomIdentity.translate(w / 2 - (box.x + box.width / 2) * k, h / 2 - (box.y + box.height / 2) * k).scale(k);
}

interface Placed extends LayoutNode {
  data: NeighborhoodNode;
  degree: number;
}

export function GraphCanvas({ nodes, edges, focusId, selectedId, onSelect, onOpen, highlight, labelAll }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const gRef = useRef<SVGGElement>(null);
  const zoomRef = useRef<ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const [hover, setHover] = useState<{ node: Placed; x: number; y: number } | null>(null);

  const { placed, links, maxHop, width, box } = useMemo(() => {
    const degree = new Map<string, number>();
    for (const e of edges) {
      degree.set(e.source_account_id, (degree.get(e.source_account_id) ?? 0) + 1);
      degree.set(e.destination_account_id, (degree.get(e.destination_account_id) ?? 0) + 1);
    }
    const maxDeg = max([...degree.values()]) ?? 1;
    const radius = scaleSqrt().domain([0, maxDeg]).range([5, 17]);
    const placedNodes: Placed[] = nodes.map((n) => ({
      id: n.account_id,
      hop: n.hop,
      r: n.account_id === focusId ? 15 : radius(degree.get(n.account_id) ?? 0),
      data: n,
      degree: degree.get(n.account_id) ?? 0,
    }));
    const ids = new Set(placedNodes.map((n) => n.id));
    const layoutLinks: LayoutLink[] = edges
      .filter((e) => ids.has(e.source_account_id) && ids.has(e.destination_account_id))
      .map((e) => ({ source: e.source_account_id, target: e.destination_account_id, amount: e.total_amount }));
    layout(placedNodes, layoutLinks);
    const amounts = edges.map((e) => Number(e.total_amount));
    const w = scaleSqrt().domain([0, max(amounts) ?? 1]).range([0.8, 6]);
    const hops = max(placedNodes, (n) => n.hop) ?? 0;
    const nodeBox = bounds(placedNodes, 24);
    // frame the outer ring with the focus account at the centre; labels need horizontal room
    const reach = Math.max(hops * RING_GAP + 30, Math.abs(nodeBox.x), Math.abs(nodeBox.y), nodeBox.x + nodeBox.width, nodeBox.y + nodeBox.height);
    const box: Bounds = { x: -reach - 70, y: -reach - 20, width: 2 * reach + 140, height: 2 * reach + 40 };
    return { placed: placedNodes, links: layoutLinks, maxHop: hops, width: (a: string) => w(Number(a)), box };
  }, [nodes, edges, focusId]);

  const byId = useMemo(() => new Map(placed.map((n) => [n.id, n])), [placed]);

  useEffect(() => {
    const svg = svgRef.current;
    const g = gRef.current;
    if (!svg || !g) return;
    const behaviour = zoom<SVGSVGElement, unknown>()
      .extent(() => {
        const r = svg.getBoundingClientRect();
        return [
          [0, 0],
          [r.width || 1, r.height || 1],
        ];
      })
      .scaleExtent([0.2, 5])
      .on("zoom", (event) => {
        select(g).attr("transform", event.transform.toString());
        // labels keep their on-screen size whatever the fit or zoom
        svg.style.setProperty("--k", String(event.transform.k));
      });
    zoomRef.current = behaviour;
    const sel = select(svg);
    sel.call(behaviour);
    sel.call(behaviour.transform, fit(svg, box));
    return () => {
      sel.on(".zoom", null);
    };
  }, [placed, box]);

  const zoomBy = (factor: number) => {
    if (svgRef.current && zoomRef.current) select(svgRef.current).call(zoomRef.current.scaleBy, factor);
  };
  const reset = () => {
    if (svgRef.current && zoomRef.current) select(svgRef.current).call(zoomRef.current.transform, fit(svgRef.current, box));
  };

  const active = hover?.node.id ?? selectedId ?? null;
  const topRisk = useMemo(
    () => new Set([...placed].sort((a, b) => (b.data.risk_score ?? -1) - (a.data.risk_score ?? -1)).slice(0, 6).map((n) => n.id)),
    [placed],
  );

  return (
    <div className={s.wrap}>
      <svg ref={svgRef} className={s.svg} onPointerDown={(e) => e.target === svgRef.current && setHover(null)} role="img" aria-label={`Neighbourhood graph of ${focusId}: ${nodes.length} accounts, ${edges.length} aggregated transfers`}>
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" markerUnits="userSpaceOnUse" orient="auto-start-reverse">
            <path d="M0 0 10 5 0 10z" fill="#5a6878" />
          </marker>
        </defs>
        <g ref={gRef}>
          {Array.from({ length: maxHop }, (_, i) => (
            <g key={i}>
              <circle className={s.ring} r={(i + 1) * RING_GAP} />
            </g>
          ))}
          {links.map((l) => {
            const a = l.source as LayoutNode;
            const b = l.target as LayoutNode;
            const dx = b.x! - a.x!;
            const dy = b.y! - a.y!;
            const len = Math.hypot(dx, dy) || 1;
            const rb = byId.get(b.id)?.r ?? 6;
            const hot = active !== null && (a.id === active || b.id === active);
            const onFocus = a.id === focusId || b.id === focusId;
            const dim = (highlight && !(highlight.has(a.id) && highlight.has(b.id))) || (active !== null && !hot);
            // the focus account's money: tinted by the counterparty's risk on the shared ramp
            const counterparty = byId.get(a.id === (active ?? focusId) ? b.id : a.id);
            const tinted = hot || (active === null && onFocus);
            return (
              <line
                key={`${a.id}>${b.id}`}
                className={`${s.edge} ${hot ? s.edgeHot : ""} ${onFocus && !hot ? s.edgeFocus : ""} ${dim ? s.edgeDim : ""}`}
                style={{ animationDelay: `${Math.max(a.hop, b.hop) * 110 + 60}ms`, ...(tinted ? { stroke: ramp(counterparty?.data.risk_score) } : {}) }}
                x1={a.x}
                y1={a.y}
                x2={b.x! - (dx / len) * (rb + 3)}
                y2={b.y! - (dy / len) * (rb + 3)}
                strokeWidth={width(l.amount)}
                markerEnd="url(#arrow)"
              />
            );
          })}
          {placed.map((n) => {
            const dim = highlight ? !highlight.has(n.id) : false;
            return (
              <g
                key={n.id}
                className={`${s.node} ${dim ? s.dim : ""}`}
                style={{ animationDelay: `${n.hop * 110}ms` }}
                transform={`translate(${n.x},${n.y})`}
                tabIndex={0}
                role="button"
                aria-label={`${n.id}, risk ${score(n.data.risk_score)}, ${n.data.risk_tier ?? "unscored"}, hop ${n.hop}`}
                aria-pressed={n.id === selectedId}
                onClick={() => onSelect?.(n.id)}
                onDoubleClick={() => onOpen?.(n.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") onOpen?.(n.id);
                  if (e.key === " ") {
                    e.preventDefault();
                    onSelect?.(n.id);
                  }
                }}
                onPointerEnter={(e) => {
                  if (e.pointerType !== "mouse") return;
                  const box = svgRef.current!.getBoundingClientRect();
                  setHover({ node: n, x: e.clientX - box.left, y: e.clientY - box.top });
                }}
                onPointerLeave={() => setHover(null)}
              >
                {n.id === focusId && <circle className={s.focusRing} r={n.r + 5} />}
                {n.id === selectedId && <circle className={s.selectRing} r={n.r + 4} />}
                <circle r={n.r} fill={ramp(n.data.risk_score)} />

              </g>
            );
          })}
          <g aria-hidden>
            {placed
              .filter((n) => labelAll || n.id === focusId || n.id === active || topRisk.has(n.id))
              .map((n) => {
                // labels on the right half read outward to the right, on the left half to the left
                const left = (n.x ?? 0) < 0;
                return (
                  <text key={n.id} className={s.label} x={(n.x ?? 0) + (left ? -(n.r + 5) : n.r + 5)} y={(n.y ?? 0) + 4} textAnchor={left ? "end" : "start"}>
                    {n.data.source_account_ref ?? n.id}
                  </text>
                );
              })}
          </g>
        </g>
      </svg>
      {hover && (
        <div className={s.tooltip} style={{ left: Math.min(hover.x + 14, (svgRef.current?.clientWidth ?? 600) - 220), top: hover.y + 14 }}>
          <strong>{hover.node.id}</strong>
          <dl>
            <dt>Risk</dt>
            <dd>
              {score(hover.node.data.risk_score)} {hover.node.data.risk_tier ?? ""}
            </dd>
            <dt>Type</dt>
            <dd>{hover.node.data.account_type ?? "—"}</dd>
            <dt>Hop</dt>
            <dd>{hover.node.hop}</dd>
            <dt>Links here</dt>
            <dd>{int(hover.node.degree)}</dd>
            <dt>Community</dt>
            <dd>{hover.node.data.community_id?.slice(0, 8) ?? "—"}</dd>
          </dl>
        </div>
      )}
      <div className={s.hud}>
        <span>{maxHop > 0 ? `dashed rings: hop ${maxHop > 1 ? `1–${maxHop}` : "1"} from focus` : "focus only"}</span>
        <span>{int(nodes.length)} accounts</span>
        <span>{int(edges.length)} transfers (aggregated)</span>
        <span>max {compactAmount(max(edges, (e) => Number(e.total_amount)) ?? 0)}</span>
      </div>
      <div className={s.controls}>
        <button type="button" onClick={() => zoomBy(1.3)} aria-label="Zoom in">
          <Plus size={15} aria-hidden />
        </button>
        <button type="button" onClick={reset} aria-label="Fit graph">
          <Maximize2 size={14} aria-hidden />
        </button>
        <button type="button" onClick={() => zoomBy(1 / 1.3)} aria-label="Zoom out">
          <Minus size={15} aria-hidden />
        </button>
      </div>
    </div>
  );
}
