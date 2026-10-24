/** Diverging SHAP bars. SHAP explains the ML component only (SRS §12.8). */
import type { ShapContribution } from "../api/types";
import s from "./ShapBars.module.css";

export function ShapBars({ contributions, statement }: { contributions: ShapContribution[]; statement?: string }) {
  const maxAbs = Math.max(...contributions.map((c) => Math.abs(c.shap)), 1e-9);
  return (
    <>
      <ul className={s.list}>
        {contributions.map((c) => {
          const w = (Math.abs(c.shap) / maxAbs) * 50;
          return (
            <li key={c.feature_id} className={s.row} title={`${c.feature_id} ${c.name}: value ${c.value ?? "—"} (${c.state})`}>
              <span className={s.name}>
                <b>{c.feature_id}</b> {c.name}
              </span>
              <span className={s.axis} aria-hidden>
                <span className={`${s.bar} ${c.shap >= 0 ? s.up : s.down}`} style={c.shap >= 0 ? { left: "50%", width: `${w}%` } : { right: "50%", width: `${w}%` }} />
              </span>
              <span className={`num ${s.val}`}>
                {c.shap >= 0 ? "+" : "−"}
                {Math.abs(c.shap).toFixed(3)}
              </span>
            </li>
          );
        })}
      </ul>
      {statement && <p className={s.note}>{statement}</p>}
    </>
  );
}
