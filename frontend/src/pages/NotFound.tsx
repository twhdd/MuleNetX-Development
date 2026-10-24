import { Link } from "react-router-dom";
import ui from "../components/ui.module.css";
import p from "./page.module.css";

export function NotFound({ reason }: { reason?: string }) {
  return (
    <div className={p.page}>
      <div className={p.body} style={{ paddingTop: "var(--sp-7)", maxWidth: "60ch" }}>
        <h1>{reason ? "Not available" : "Page not found"}</h1>
        <p className={p.muted}>{reason ?? "This address does not match any screen."}</p>
        <Link to="/" className={ui.button} style={{ alignSelf: "flex-start" }}>
          Back to triage
        </Link>
      </div>
    </div>
  );
}
