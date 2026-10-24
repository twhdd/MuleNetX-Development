import {
  Boxes,
  Database,
  FolderKanban,
  Gauge,
  GitFork,
  LogOut,
  Network,
  Route,
  ScrollText,
  Search,
  Users,
  Workflow,
  Waypoints,
  Target,
  Cpu,
  Menu,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import type { LucideIcon } from "lucide-react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { authService } from "../api/auth";
import { CONTEXT_POLL_MS, useActiveContext } from "../state/context";
import { useSession } from "../state/session";
import { EvidenceLabel } from "./EvidenceLabel";
import { relative, shortId } from "../lib/format";
import { can } from "../lib/permissions";
import s from "./Layout.module.css";
import ui from "./ui.module.css";

interface NavDef {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
}

const WORK: NavDef[] = [
  { to: "/", label: "Triage", icon: Gauge, end: true },
  { to: "/accounts", label: "Accounts", icon: Search },
  { to: "/graph", label: "Graph explorer", icon: Network },
  { to: "/paths", label: "Money flow", icon: Route },
  { to: "/communities", label: "Communities", icon: Boxes },
  { to: "/rings", label: "Rings", icon: Waypoints },
  { to: "/evaluation", label: "Evaluation", icon: Target },
  { to: "/cases", label: "Cases", icon: FolderKanban },
];

function adminNav(role: string | undefined): NavDef[] {
  const items: NavDef[] = [
    { to: "/admin/ingestion", label: "Ingestion", icon: Database },
    { to: "/admin/pipelines", label: "Pipelines", icon: Workflow },
    { to: "/admin/models", label: "Models", icon: Cpu },
  ];
  if (can.manageUsers(role as never)) items.push({ to: "/admin/users", label: "Users", icon: Users });
  if (can.readAudit(role as never)) items.push({ to: "/admin/audit", label: "Audit log", icon: ScrollText });
  return items;
}

function NavItem({ item }: { item: NavDef }) {
  const [tip, setTip] = useState<{ x: number; y: number } | null>(null);
  const Icon = item.icon;
  const show = (el: HTMLElement) => {
    const r = el.getBoundingClientRect();
    setTip(window.innerWidth <= 640 ? null : { x: r.right + 8, y: r.top + r.height / 2 - 12 });
  };
  return (
    <>
      <NavLink
        to={item.to}
        end={item.end}
        className={s.navItem}
        aria-label={item.label}
        onMouseEnter={(e) => show(e.currentTarget)}
        onMouseLeave={() => setTip(null)}
        onFocus={(e) => show(e.currentTarget)}
        onBlur={() => setTip(null)}
      >
        <Icon size={19} aria-hidden />
      </NavLink>
      {tip && (
        <span className={s.tip} style={{ left: tip.x, top: tip.y }} role="tooltip">
          {item.label}
        </span>
      )}
    </>
  );
}

function ContextBanner() {
  const { context, error, loadedAt, refresh } = useActiveContext();
  useEffect(() => {
    void refresh();
    const t = window.setInterval(() => void refresh(), CONTEXT_POLL_MS);
    return () => window.clearInterval(t);
  }, [refresh]);
  if (error && !context) return <div className={s.ctx}><span className={s.idle}>Context unavailable: {error}</span></div>;
  if (!context) return <div className={s.ctx}>Loading context…</div>;
  if (!context.is_active)
    return (
      <div className={s.ctx} data-state="EMPTY">
        <span className={s.idle}>No active dataset. An administrator must ingest data and run the pipeline to READY.</span>
      </div>
    );
  return (
    <div className={s.ctx} aria-label="Active analytical context" title={loadedAt ? `Checked ${relative(new Date(loadedAt).toISOString())}` : undefined}>
      {context.is_synthetic_injection && <EvidenceLabel kind="SYNTHETIC DATA" />}
      <span className={`${s.ctxItem} ${s.ctxOptional}`}>
        <span>Dataset</span>
        <span className="num">{shortId(context.dataset_id)}</span>
      </span>
      <span className={s.ctxItem}>
        <span>Snapshot</span>
        <span className="num">{shortId(context.graph_snapshot_id)}</span>
      </span>
      <span className={`${s.ctxItem} ${s.ctxOptional}`}>
        <span>Model</span>
        <span className="num">{context.model_version ?? "none (ML unavailable)"}</span>
      </span>
      <span className={s.ctxItem}>
        <span>Activated</span>
        <span className="num">{relative(context.updated_at)}</span>
      </span>
    </div>
  );
}

const PRIMARY_MOBILE = ["/", "/accounts", "/graph", "/cases"];

function MobileNav({ items }: { items: NavDef[] }) {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  useEffect(() => setOpen(false), [location.pathname]);
  useEffect(() => {
    if (!open) return;
    const close = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [open]);
  const primary = items.filter((i) => PRIMARY_MOBILE.includes(i.to));
  return (
    <>
      <nav className={s.mobileBar} aria-label="Primary">
        {primary.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink key={item.to} to={item.to} end={item.end} className={s.mobileItem}>
              <Icon size={19} aria-hidden />
              <span>{item.label === "Graph explorer" ? "Graph" : item.label}</span>
            </NavLink>
          );
        })}
        <button type="button" className={s.mobileItem} aria-expanded={open} aria-controls="more-sheet" onClick={() => setOpen((o) => !o)}>
          {open ? <X size={19} aria-hidden /> : <Menu size={19} aria-hidden />}
          <span>More</span>
        </button>
      </nav>
      {open && (
        <div className={s.sheet} id="more-sheet" role="dialog" aria-label="All destinations">
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink key={item.to} to={item.to} end={item.end} className={s.sheetItem}>
                <Icon size={18} aria-hidden />
                {item.label}
              </NavLink>
            );
          })}
        </div>
      )}
    </>
  );
}

export function Layout() {
  const user = useSession((st) => st.user);
  const signOut = useSession((st) => st.signOut);
  const resetContext = useActiveContext((st) => st.reset);
  const navigate = useNavigate();
  const logout = async () => {
    try {
      await authService.logout();
    } catch {
      /* the session is dropped locally either way */
    }
    signOut();
    resetContext();
    navigate("/login");
  };
  return (
    <div className={s.shell}>
      <nav className={s.rail} aria-label="Primary">
        <div className={s.mark} aria-hidden>
          <GitFork size={22} />
        </div>
        <div className={s.group}>
          {WORK.map((item) => (
            <NavItem key={item.to} item={item} />
          ))}
        </div>
        <div className={s.group}>
          {adminNav(user?.role).map((item) => (
            <NavItem key={item.to} item={item} />
          ))}
        </div>
        <div className={s.spacer} />
      </nav>
      <MobileNav items={[...WORK, ...adminNav(user?.role)]} />
      <header className={s.banner}>
        <span className={s.brand}>MuleNetX</span>
        <ContextBanner />
        <div className={s.user}>
          <span>{user?.username}</span>
          <span className={s.role}>{user?.role}</span>
          <button type="button" className={`${ui.button} ${ui.ghost} ${ui.small}`} onClick={logout}>
            <LogOut size={14} aria-hidden />
            Sign out
          </button>
        </div>
      </header>
      <main className={s.main} id="main">
        <Outlet />
      </main>
    </div>
  );
}
