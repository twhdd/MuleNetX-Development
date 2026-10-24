/**
 * Where a copilot source reference leads (SRS §21.5). Refs are the context item IDs the backend assembled;
 * account IDs contain ':' so the account-bearing kinds are parsed from both ends.
 */
import type { CopilotScope } from "../api/copilot";

const acct = (id: string) => `/accounts/${encodeURIComponent(id)}`;

export interface RefTarget {
  kind: string;
  label: string;
  href: string | null;
}

export function refTarget(ref: string, scope: CopilotScope): RefTarget {
  const at = ref.indexOf(":");
  const kind = at < 0 ? ref : ref.slice(0, at);
  const rest = at < 0 ? "" : ref.slice(at + 1);
  const subject = scope.account_id;
  const inSubject = (tab: string) => (subject ? `${acct(subject)}?tab=${tab}` : null);
  switch (kind) {
    case "account":
      return { kind, label: rest, href: acct(rest) };
    case "assessment":
      return { kind, label: "risk assessment", href: inSubject("risk") };
    case "shap":
      return { kind, label: `SHAP ${rest.slice(rest.lastIndexOf(":") + 1)}`, href: inSubject("risk") };
    case "feature": {
      const cut = rest.lastIndexOf(":");
      return { kind, label: rest.slice(cut + 1), href: `${acct(rest.slice(0, cut))}?tab=features` };
    }
    case "transaction":
      return { kind, label: rest, href: inSubject("transactions") };
    case "metrics": {
      const account = rest.slice(rest.indexOf(":") + 1);
      return { kind, label: "graph metrics", href: `/graph?account=${encodeURIComponent(account)}` };
    }
    case "community":
      return { kind, label: rest.slice(0, 8), href: `/communities/${encodeURIComponent(rest)}` };
    case "motif":
      return {
        kind,
        label: rest.slice(0, 8),
        href: scope.ring_id ? `/rings/${encodeURIComponent(scope.ring_id)}?tab=motifs` : inSubject("motifs"),
      };
    case "edge": {
      const [from = "", to = ""] = rest.slice(rest.indexOf(":") + 1).split(">");
      return { kind, label: `${from} → ${to}`, href: `/paths?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}` };
    }
    case "ring":
      return { kind, label: rest.slice(0, 8), href: `/rings/${encodeURIComponent(rest)}` };
    case "case":
      return { kind, label: rest.slice(0, 8), href: `/cases/${encodeURIComponent(rest)}` };
    case "finding":
      return { kind, label: rest.slice(0, 8), href: scope.case_id ? `/cases/${encodeURIComponent(scope.case_id)}` : null };
    default:
      return { kind, label: rest || ref, href: null };
  }
}
