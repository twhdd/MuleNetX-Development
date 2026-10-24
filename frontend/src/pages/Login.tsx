import { LogIn } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { authService } from "../api/auth";
import { ApiError } from "../api/client";
import type { Role } from "../api/types";
import ui from "../components/ui.module.css";
import { ramp } from "../lib/ramp";
import { useSession } from "../state/session";
import s from "./Login.module.css";

/** A fixed illustrative drawing of accounts and transfers; it depicts no data. */
const ART_NODES: [number, number, number][] = [
  [60, 210, 0.12], [150, 120, 0.22], [170, 300, 0.3], [260, 200, 0.55], [330, 90, 0.4], [360, 310, 0.62],
  [440, 190, 0.86], [520, 110, 0.7], [540, 280, 0.93], [620, 200, 0.97], [470, 360, 0.5], [250, 360, 0.18],
];
const ART_EDGES: [number, number][] = [
  [0, 1], [0, 2], [1, 3], [2, 3], [3, 4], [3, 5], [4, 6], [5, 6], [6, 7], [6, 8], [7, 9], [8, 9], [5, 10], [10, 8], [2, 11], [11, 5],
];

function NetworkArt() {
  return (
    <svg className={s.network} viewBox="0 0 680 420" aria-hidden>
      {ART_EDGES.map(([a, b]) => {
        const [x1, y1] = ART_NODES[a]!;
        const [x2, y2] = ART_NODES[b]!;
        return <line key={`${a}-${b}`} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#2b3644" strokeWidth={1.2} />;
      })}
      {ART_NODES.map(([x, y, v], i) => (
        <circle key={i} cx={x} cy={y} r={6 + v * 9} fill={ramp(v)} stroke="#07090c" strokeWidth={2} />
      ))}
    </svg>
  );
}

export function Login() {
  const signIn = useSession((st) => st.signIn);
  const expired = useSession((st) => st.expired);
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await authService.login(username, password);
      signIn(res.access_token, { user_id: res.user.user_id, username: res.user.username, role: res.user.role as Role }, res.expires_in);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from && from !== "/login" ? from : "/", { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) setError("Too many attempts. Wait a moment before trying again.");
      else if (err instanceof ApiError && err.status === 401) setError("Username or password is incorrect, or the account is inactive.");
      else setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={s.page}>
      <section className={s.art}>
        <span className={s.wordmark}>MuleNetX</span>
        <NetworkArt />
        <div>
          <p className={s.statement}>
            Follow the money between accounts, see <em>why</em> each one scores, and build the case on evidence.
          </p>
        </div>
      </section>
      <div className={s.formWrap}>
        <form className={s.form} onSubmit={submit} noValidate>
          <div>
            <h1>Sign in</h1>
            <p className={s.sub}>Investigation workspace</p>
          </div>
          {expired && !error && <div className={s.info} role="status">Your session ended. Sign in again to continue.</div>}
          {error && <div className={s.alert} role="alert">{error}</div>}
          <label className={ui.field}>
            <span className={ui.label}>Username</span>
            <input className={ui.input} autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus />
          </label>
          <label className={ui.field}>
            <span className={ui.label}>Password</span>
            <input className={ui.input} type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          <button type="submit" className={`${ui.button} ${ui.primary}`} disabled={busy || !username || !password}>
            <LogIn size={15} aria-hidden />
            {busy ? "Signing in…" : "Sign in"}
          </button>
          <p className={s.note}>The session is held in this tab's memory only. Reloading the page signs you out.</p>
        </form>
      </div>
    </div>
  );
}
