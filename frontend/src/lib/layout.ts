/**
 * Deterministic graph layout (PLAN T27 default): nodes start on BFS hop rings ordered by `account_id`,
 * then a fixed number of force iterations settles them. The same input always yields the same picture.
 */
import { forceCollide, forceLink, forceManyBody, forceRadial, forceSimulation, type SimulationLinkDatum, type SimulationNodeDatum } from "d3";

export interface LayoutNode extends SimulationNodeDatum {
  id: string;
  hop: number;
  r: number;
}

export interface LayoutLink extends SimulationLinkDatum<LayoutNode> {
  source: string | LayoutNode;
  target: string | LayoutNode;
  amount: string;
}

export const RING_GAP = 150;

export function initialPositions<T extends { id: string; hop: number }>(nodes: T[]): Map<string, { x: number; y: number }> {
  const byHop = new Map<number, T[]>();
  for (const n of nodes) byHop.set(n.hop, [...(byHop.get(n.hop) ?? []), n]);
  const out = new Map<string, { x: number; y: number }>();
  for (const [hop, ring] of byHop) {
    const sorted = [...ring].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
    sorted.forEach((n, i) => {
      if (hop === 0 && sorted.length === 1) {
        out.set(n.id, { x: 0, y: 0 });
        return;
      }
      const angle = (2 * Math.PI * i) / sorted.length - Math.PI / 2 + hop * 0.35;
      out.set(n.id, { x: Math.cos(angle) * hop * RING_GAP, y: Math.sin(angle) * hop * RING_GAP });
    });
  }
  return out;
}

export function layout(nodes: LayoutNode[], links: LayoutLink[], iterations = 320): void {
  const start = initialPositions(nodes);
  for (const n of nodes) {
    const p = start.get(n.id)!;
    n.x = p.x;
    n.y = p.y;
    if (n.hop === 0) {
      n.fx = 0;
      n.fy = 0;
    }
  }
  const sim = forceSimulation(nodes)
    .force("link", forceLink<LayoutNode, LayoutLink>(links).id((d) => d.id).distance(60).strength(0.03))
    .force("charge", forceManyBody<LayoutNode>().strength(-90).distanceMax(260))
    .force("collide", forceCollide<LayoutNode>().radius((d) => d.r + 5).iterations(3))
    .force("radial", forceRadial<LayoutNode>((d) => d.hop * RING_GAP).strength(1))
    .stop();
  for (let i = 0; i < iterations; i++) sim.tick();
}

export interface Bounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

export function bounds(nodes: LayoutNode[], pad = 40): Bounds {
  if (nodes.length === 0) return { x: -100, y: -100, width: 200, height: 200 };
  let x0 = Infinity;
  let y0 = Infinity;
  let x1 = -Infinity;
  let y1 = -Infinity;
  for (const n of nodes) {
    x0 = Math.min(x0, (n.x ?? 0) - n.r);
    y0 = Math.min(y0, (n.y ?? 0) - n.r);
    x1 = Math.max(x1, (n.x ?? 0) + n.r);
    y1 = Math.max(y1, (n.y ?? 0) + n.r);
  }
  return { x: x0 - pad, y: y0 - pad, width: x1 - x0 + 2 * pad, height: y1 - y0 + 2 * pad };
}
