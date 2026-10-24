import { ChevronLeft, ChevronRight } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { int, score as fmtScore } from "../lib/format";
import { RAMP_STOPS, ramp, tierColor } from "../lib/ramp";
import s from "./bits.module.css";
import ui from "./ui.module.css";

export function TierChip({ tier }: { tier: string | null | undefined }) {
  return (
    <span className={s.tier} style={{ color: tierColor(tier) }} data-tier={tier ?? "NONE"}>
      <span className={s.tierDot} aria-hidden />
      {tier ?? "UNSCORED"}
    </span>
  );
}

/** A 0–1 score as a ramp-filled bar; `cap` marks the maximum attainable score (§12.6 coverage). */
export function ScoreBar({ value, cap, label }: { value: number | null | undefined; cap?: number; label?: string }) {
  const v = value ?? 0;
  return (
    <div className={s.scoreBar} aria-label={label ? `${label} ${fmtScore(value)}` : undefined}>
      <div className={s.track}>
        {value !== null && value !== undefined && <div className={s.fill} style={{ width: `${v * 100}%`, background: ramp(v) }} />}
        {cap !== undefined && cap < 1 && <div className={s.cap} style={{ left: `${cap * 100}%` }} title="Maximum attainable with the available signals" />}
      </div>
      <span className="num">{fmtScore(value)}</span>
    </div>
  );
}

export function AccountLink({ id, children }: { id: string; children?: ReactNode }) {
  return (
    <Link className={s.entityLink} to={`/accounts/${encodeURIComponent(id)}`}>
      {children ?? id}
    </Link>
  );
}

export function Paginator({ page, pageSize, total, capped, onPage }: { page: number; pageSize: number; total: number; capped?: boolean; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);
  return (
    <nav className={s.pager} aria-label="Pagination">
      <span className={s.count}>
        {int(from)}–{int(to)} of {int(total)}
        {capped ? "+" : ""}
      </span>
      <div className={s.pagerButtons}>
        <button type="button" className={`${ui.button} ${ui.small}`} disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label="Previous page">
          <ChevronLeft size={14} aria-hidden />
        </button>
        <button type="button" className={`${ui.button} ${ui.small}`} disabled={page >= pages && !capped} onClick={() => onPage(page + 1)} aria-label="Next page">
          <ChevronRight size={14} aria-hidden />
        </button>
      </div>
    </nav>
  );
}

export function PageHeader({ title, lede, actions }: { title: ReactNode; lede?: ReactNode; actions?: ReactNode }) {
  return (
    <header className={s.header}>
      <div>
        <h1>{title}</h1>
        {lede && <p>{lede}</p>}
      </div>
      {actions && <div className={s.headerActions}>{actions}</div>}
    </header>
  );
}

export function RampLegend({ low = "0", high = "1" }: { low?: string; high?: string }) {
  const gradient = `linear-gradient(90deg, ${RAMP_STOPS.map((r) => `${r.color} ${r.stop * 100}%`).join(", ")})`;
  return (
    <span className={s.legend}>
      <span>{low}</span>
      <span className={s.legendBar} style={{ background: gradient }} aria-hidden />
      <span>{high}</span>
    </span>
  );
}
