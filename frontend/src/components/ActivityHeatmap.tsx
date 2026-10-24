/**
 * Day × hour activity of one account (UTC), counted from its canonical transactions in the API's
 * resolved window. A display aggregation of facts: counts and sums only, no scoring.
 */
import { interpolateRgb } from "d3";
import { useMemo } from "react";
import type { Transaction } from "../api/types";
import { amount, int } from "../lib/format";
import s from "./ActivityHeatmap.module.css";

const shade = interpolateRgb("#18202b", "#e6ebf0");

interface Bucket {
  count: number;
  inCount: number;
  outCount: number;
  total: number;
}

export function ActivityHeatmap({ transactions, start, end, capped }: { transactions: Transaction[]; start: string; end: string; capped: boolean }) {
  const { days, grid, maxCount } = useMemo(() => {
    const first = new Date(start);
    const last = new Date(end);
    const dayKeys: string[] = [];
    for (let d = Date.UTC(first.getUTCFullYear(), first.getUTCMonth(), first.getUTCDate()); d <= last.getTime(); d += 86_400_000) {
      dayKeys.push(new Date(d).toISOString().slice(0, 10));
    }
    const cells = new Map<string, Bucket>();
    let maxC = 0;
    for (const t of transactions) {
      const key = `${t.timestamp.slice(0, 10)}|${Number(t.timestamp.slice(11, 13))}`;
      const b = cells.get(key) ?? { count: 0, inCount: 0, outCount: 0, total: 0 };
      b.count += 1;
      if (t.direction === "in") b.inCount += 1;
      else b.outCount += 1;
      b.total += Number(t.amount);
      cells.set(key, b);
      maxC = Math.max(maxC, b.count);
    }
    const active = dayKeys.filter((d) => [...Array(24).keys()].some((h) => cells.has(`${d}|${h}`)));
    // long windows: show only days with activity plus their neighbours, so the grid stays readable
    const shown = dayKeys.length > 14 ? dayKeys.filter((d, i) => active.includes(d) || active.includes(dayKeys[i - 1] ?? "") || active.includes(dayKeys[i + 1] ?? "")) : dayKeys;
    return { days: shown, grid: cells, maxCount: maxC };
  }, [transactions, start, end]);

  const color = (c: number) => (c === 0 ? undefined : shade(0.25 + 0.75 * (c / Math.max(maxCount, 1))));

  return (
    <div className={s.wrap}>
      <div className={s.grid} role="grid" aria-label="Transactions per hour, by day (UTC)">
        <span />
        {Array.from({ length: 24 }, (_, h) => (
          <span key={h} className={s.hour}>
            {h % 3 === 0 ? String(h).padStart(2, "0") : ""}
          </span>
        ))}
        {days.map((d) => (
          <div key={d} style={{ display: "contents" }} role="row">
            <span className={s.day}>{d.slice(5)}</span>
            {Array.from({ length: 24 }, (_, h) => {
              const b = grid.get(`${d}|${h}`);
              const label = b ? `${d} ${String(h).padStart(2, "0")}:00 — ${b.count} transactions (${b.inCount} in, ${b.outCount} out), ${amount(String(b.total))}` : `${d} ${String(h).padStart(2, "0")}:00 — none`;
              return <span key={h} className={s.cell} role="gridcell" style={{ background: color(b?.count ?? 0) }} title={label} aria-label={label} />;
            })}
          </div>
        ))}
      </div>
      <div className={s.foot}>
        <span>
          {int(transactions.length)} transactions{capped ? " (first page set only; narrow the window to see all)" : ""} · {days.length} days shown
        </span>
        <span className={s.scale}>
          fewer
          {[0.25, 0.5, 0.75, 1].map((v) => (
            <span key={v} style={{ background: shade(v) }} />
          ))}
          more
        </span>
      </div>
    </div>
  );
}
