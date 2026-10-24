import { UserPlus } from "lucide-react";
import { useState, type FormEvent } from "react";
import { userService } from "../../api/admin";
import type { Role, User } from "../../api/types";
import { PageHeader, Paginator } from "../../components/bits";
import { StateView } from "../../components/StateView";
import ui from "../../components/ui.module.css";
import { dateTime, relative } from "../../lib/format";
import { useApi } from "../../lib/useApi";
import { useSession } from "../../state/session";
import p from "../page.module.css";

const ROLES: Role[] = ["ANALYST", "INVESTIGATOR", "ADMIN"];

function Row({ u, onChanged }: { u: User; onChanged: () => void }) {
  const me = useSession((st) => st.user);
  const [error, setError] = useState<string | null>(null);
  const update = async (body: { role?: Role; is_active?: boolean }) => {
    setError(null);
    try {
      await userService.update(u.user_id, body);
      onChanged();
    } catch (err) {
      setError((err as Error).message);
    }
  };
  const self = me?.user_id === u.user_id;
  return (
    <tr>
      <td>
        <span className="entity">{u.username}</span> {self && <span className={p.muted}>(you)</span>}
        {error && <div className={ui.error}>{error}</div>}
      </td>
      <td>
        <select className={`${ui.select} ${ui.small}`} aria-label={`Role of ${u.username}`} value={u.role} disabled={self} onChange={(e) => void update({ role: e.target.value as Role })}>
          {ROLES.map((r) => (
            <option key={r}>{r}</option>
          ))}
        </select>
      </td>
      <td>{u.is_active ? "Active" : <span className={p.muted}>Inactive</span>}</td>
      <td className="num">{relative(u.last_login_at)}</td>
      <td className="num">{dateTime(u.created_at)}</td>
      <td className={ui.right}>
        {!self && (
          <button type="button" className={`${ui.button} ${ui.small} ${u.is_active ? ui.danger : ""}`} onClick={() => void update({ is_active: !u.is_active })}>
            {u.is_active ? "Deactivate" : "Activate"}
          </button>
        )}
      </td>
    </tr>
  );
}

export function Users() {
  const [page, setPage] = useState(1);
  const [tick, setTick] = useState(0);
  const result = useApi((sig) => userService.list(page, sig), [page, tick]);
  const [form, setForm] = useState({ username: "", role: "ANALYST" as Role, password: "" });
  const [error, setError] = useState<string | null>(null);
  const create = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await userService.create(form);
      setForm({ username: "", role: "ANALYST", password: "" });
      setTick((t) => t + 1);
    } catch (err) {
      setError((err as Error).message);
    }
  };
  return (
    <div className={p.page}>
      <PageHeader title="Users" lede="Accounts and roles. Role and activation changes are audited; deactivation ends the user's sessions." />
      <div className={p.body}>
        <form className={ui.toolbar} onSubmit={create} aria-label="Create user">
          <label className={ui.field}>
            <span className={ui.label}>Username</span>
            <input className={ui.input} value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} autoComplete="off" />
          </label>
          <label className={ui.field}>
            <span className={ui.label}>Role</span>
            <select className={ui.select} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}>
              {ROLES.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </label>
          <label className={ui.field}>
            <span className={ui.label}>Initial password</span>
            <input className={ui.input} type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} autoComplete="new-password" />
          </label>
          <button type="submit" className={`${ui.button} ${ui.primary}`} disabled={!form.username || !form.password}>
            <UserPlus size={15} aria-hidden />
            Create user
          </button>
          {error && <span className={ui.error} role="alert">{error}</span>}
        </form>
        <div className={ui.panel}>
          <StateView result={result} rows={6}>
            {(data) => (
              <>
                <div className={p.tableWrap}>
                  <div className={ui.tableScroll}><table className={ui.table}>
                    <thead>
                      <tr>
                        <th>User</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Last sign-in</th>
                        <th>Created</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {data.items.map((u) => (
                        <Row key={u.user_id} u={u} onChanged={() => setTick((t) => t + 1)} />
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
