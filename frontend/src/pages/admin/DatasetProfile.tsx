import { useParams } from "react-router-dom";
import { pipelineService } from "../../api/pipeline";
import { PageHeader } from "../../components/bits";
import { EvidenceLabel } from "../../components/EvidenceLabel";
import { StateView } from "../../components/StateView";
import ui from "../../components/ui.module.css";
import { dateTime, int } from "../../lib/format";
import { useApi } from "../../lib/useApi";
import p from "../page.module.css";
import s from "./admin.module.css";

type Json = Record<string, unknown>;

function scalar(v: unknown): string {
  if (typeof v === "number") return Number.isInteger(v) ? int(v) : v.toFixed(4);
  if (typeof v === "boolean") return v ? "yes" : "no";
  return String(v ?? "—");
}

function Group({ title, data }: { title: string; data: Json }) {
  return (
    <section className={ui.panel}>
      <div className={ui.panelHead}>
        <h2 className={ui.panelTitle}>{title}</h2>
      </div>
      <div className={ui.panelBody}>
        <dl className={ui.kv}>
          {Object.entries(data).map(([k, v]) => (
            <div key={k} style={{ display: "contents" }}>
              <dt>{k.replaceAll("_", " ")}</dt>
              <dd className="num">{typeof v === "object" && v !== null ? JSON.stringify(v) : scalar(v)}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}

export function DatasetProfile() {
  const { id = "" } = useParams();
  const result = useApi((sig) => pipelineService.profile(id, sig), [id]);
  return (
    <div className={p.page}>
      <PageHeader title="Dataset profile" lede={<>Dataset <span className="num">{id}</span></>} actions={<EvidenceLabel kind="FACT" />} />
      <div className={p.body}>
        <StateView result={result} rows={8} empty="The profile is written by the PROFILING stage; it does not exist yet.">
          {(profile) => {
            const m = profile.metrics as Json;
            const scalars = Object.fromEntries(Object.entries(m).filter(([, v]) => typeof v !== "object" || v === null));
            const groups = Object.entries(m).filter(([, v]) => typeof v === "object" && v !== null) as [string, Json][];
            return (
              <>
                <p className={`${p.muted} ${p.small}`}>
                  Profile {profile.profile_version} · {dateTime(profile.created_at)} UTC
                </p>
                <div className={s.metrics}>
                  {Object.entries(scalars).map(([k, v]) => (
                    <div key={k} className={s.metric}>
                      <span>{k.replaceAll("_", " ")}</span>
                      <span className="num">{scalar(v)}</span>
                    </div>
                  ))}
                </div>
                <div className={p.grid2}>
                  {groups.map(([k, v]) => (
                    <Group key={k} title={k.replaceAll("_", " ")} data={v} />
                  ))}
                </div>
              </>
            );
          }}
        </StateView>
      </div>
    </div>
  );
}
