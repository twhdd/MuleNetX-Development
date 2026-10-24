/**
 * The signal matrix: one row per account, one ramp cell per score component plus the final score.
 * Every cell is an API field; unavailable components are hatched, never imputed.
 */
import type { KeyboardEvent } from "react";
import type { Account, Assessment } from "../api/types";
import { inkOn, ramp, tierColor } from "../lib/ramp";
import { availability, COMPONENTS, componentValue } from "../lib/signals";
import s from "./SignalMatrix.module.css";

export interface MatrixRow {
  account: Account;
  assessment: Assessment | null;
  error: boolean;
}

interface Props {
  rows: MatrixRow[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onOpen: (id: string) => void;
}

function Cell({ value, title, final }: { value: number | null | undefined; title: string; final?: boolean }) {
  if (value === undefined) return <td className={`${s.cell} ${s.pending} ${final ? s.final : ""}`} aria-label={`${title}: loading`} />;
  if (value === null)
    return (
      <td className={`${s.cell} ${s.na} ${final ? s.final : ""}`} title={`${title}: unavailable`}>
        n/a
      </td>
    );
  return (
    <td className={`${s.cell} ${final ? s.final : ""}`} style={{ background: ramp(value), color: inkOn(value) }} title={`${title}: ${value.toFixed(7)}`}>
      {value.toFixed(2).replace(/^0/, "")}
    </td>
  );
}

export function SignalMatrix({ rows, selectedId, onSelect, onOpen }: Props) {
  const move = (e: KeyboardEvent<HTMLTableRowElement>, index: number) => {
    const delta = e.key === "ArrowDown" ? 1 : e.key === "ArrowUp" ? -1 : 0;
    if (delta) {
      e.preventDefault();
      const target = rows[index + delta];
      if (target) {
        onSelect(target.account.account_id);
        const next = e.currentTarget.parentElement?.children[index + delta] as HTMLElement | undefined;
        next?.focus();
      }
    } else if (e.key === "Enter") {
      onOpen(rows[index]!.account.account_id);
    } else if (e.key === " ") {
      e.preventDefault();
      onSelect(rows[index]!.account.account_id);
    }
  };
  return (
    <table className={s.matrix} aria-label="Signal matrix: score components of the highest-risk accounts">
      <thead>
        <tr>
          <th scope="col">Account</th>
          {COMPONENTS.map((c) => (
            <th key={c.key} scope="col" title={c.label}>
              {c.short}
            </th>
          ))}
          <th aria-hidden className={s.gap} />
          <th scope="col" title="Final composed score">
            Final
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => {
          const a = row.assessment;
          const id = row.account.account_id;
          return (
            <tr
              key={id}
              className={s.row}
              tabIndex={0}
              aria-selected={id === selectedId}
              onClick={() => onSelect(id)}
              onDoubleClick={() => onOpen(id)}
              onKeyDown={(e) => move(e, i)}
            >
              <th scope="row" className={s.who}>
                <div className={s.whoInner}>
                  <span className={s.ref}>{row.account.source_account_ref}</span>
                  <span className={s.tierline} style={{ color: tierColor(row.account.risk_tier) }}>
                    {row.account.risk_tier ?? "UNSCORED"}
                  </span>
                </div>
              </th>
              {COMPONENTS.map((c) => (
                <Cell
                  key={c.key}
                  title={`${c.label}${a && !availability(a, c.key).available ? ` (${availability(a, c.key).reason})` : ""}`}
                  value={a ? componentValue(a, c) : row.error ? null : undefined}
                />
              ))}
              <td aria-hidden className={s.gap} />
              <Cell final title="Final score" value={a ? a.final_score : row.error ? (row.account.risk_score ?? null) : undefined} />
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
