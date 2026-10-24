/** The risk ramp: one continuous scale shared by heatmap cells, graph nodes and score bars. */
import { interpolateLab, scaleLinear } from "d3";

const STOPS = [0, 0.15, 0.3, 0.45, 0.6, 0.75, 0.88, 1];
const COLORS = ["#123524", "#1f6b45", "#3f9a5c", "#9bb83a", "#e0a52a", "#e3692f", "#d43c2f", "#a3172b"];

const scale = scaleLinear<string>().domain(STOPS).range(COLORS).interpolate(interpolateLab).clamp(true);

export const NO_SIGNAL = "#151b23";

export function ramp(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return NO_SIGNAL;
  return scale(value);
}

/** Legible label colour for text drawn on a ramp fill. */
export function inkOn(value: number | null | undefined): string {
  if (value === null || value === undefined) return "#808d9b";
  return value >= 0.38 && value <= 0.8 ? "#07090c" : "#eef2f5";
}

export const RAMP_STOPS = STOPS.map((stop, i) => ({ stop, color: COLORS[i] as string }));

export const TIER_VAR: Record<string, string> = {
  LOW: "var(--tier-low)",
  MEDIUM: "var(--tier-medium)",
  HIGH: "var(--tier-high)",
  CRITICAL: "var(--tier-critical)",
};

export function tierColor(tier: string | null | undefined): string {
  return (tier && TIER_VAR[tier]) || "var(--tier-none)";
}
