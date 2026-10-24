/**
 * Copilot (SRS §20.5, §21.5): facts, observed signals, possible interpretation and limitations shown apart,
 * every reference clickable, the whole answer labelled AI INTERPRETATION. When the local model is down or busy
 * the panel says so and nothing else on the page depends on it (§21.7).
 */
import { AlertTriangle, CircleSlash, Hourglass, PlugZap, ShieldAlert, Sparkles } from "lucide-react";
import { type FormEvent, type ReactNode, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/client";
import { type CopilotScope, copilotService } from "../api/copilot";
import type { CopilotItem, CopilotResponse } from "../api/types";
import { refTarget } from "../lib/copilotRefs";
import { dateTime, humanize, shortId } from "../lib/format";
import { EvidenceLabel } from "./EvidenceLabel";
import { Running } from "./StateView";
import s from "./CopilotPanel.module.css";
import ui from "./ui.module.css";

const MAX_QUESTION = 4000;

const SUGGESTIONS: Record<"account" | "case" | "ring", string[]> = {
  account: ["Why is this account scored this way?", "Where did money flow?", "When was this account active?", "How is it connected in the graph?"],
  case: ["Summarise this case", "What do the findings say?"],
  ring: ["Summarise this ring candidate", "Who is in this group?"],
};

const RULES: Record<number, string> = {
  1: "it was not valid JSON in the required shape",
  2: "it cited a reference that was not in the evidence it was given",
  3: "it stated a fact or signal without citing evidence",
  4: "it used wording the copilot is not allowed to use",
  5: "it exceeded the output length limit",
};

function Refs({ refs, scope }: { refs: string[]; scope: CopilotScope }) {
  if (refs.length === 0) return null;
  return (
    <span className={s.refs}>
      {refs.map((ref) => {
        const t = refTarget(ref, scope);
        const body = (
          <>
            <span className={s.refKind}>{t.kind}</span>
            {t.label}
          </>
        );
        return t.href ? (
          <Link key={ref} to={t.href} className={s.ref} title={ref}>
            {body}
          </Link>
        ) : (
          <span key={ref} className={s.ref} title={ref}>
            {body}
          </span>
        );
      })}
    </span>
  );
}

function Section({ title, items, scope, hypothesis }: { title: string; items: CopilotItem[]; scope: CopilotScope; hypothesis?: boolean }) {
  return (
    <div className={s.section}>
      <h3 className={s.sectionTitle}>{title}</h3>
      {items.length === 0 ? (
        <p className={s.none}>None stated.</p>
      ) : (
        <ul className={`${s.items} ${hypothesis ? s.hypothesis : ""}`}>
          {items.map((item, i) => (
            <li key={i}>
              <span>{item.text}</span>
              <Refs refs={item.refs} scope={scope} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Answer({ answer, scope }: { answer: CopilotResponse; scope: CopilotScope }) {
  const unsupported = answer.intent === "UNSUPPORTED";
  return (
    <div className={s.answer} data-intent={answer.intent}>
      <div className={s.answerMeta}>
        <span>{unsupported ? "Not a question the copilot answers" : humanize(answer.intent)}</span>
        {answer.model && (
          <span className="num" title={answer.model.model_digest ?? undefined}>
            {answer.model.model}
          </span>
        )}
        <span className="num">{dateTime(answer.generated_at)}</span>
      </div>
      {!unsupported && (
        <>
          <Section title="Facts" items={answer.facts} scope={scope} />
          <Section title="Observed signals" items={answer.observed_signals} scope={scope} />
          <Section title="Possible interpretation" items={answer.possible_interpretation} scope={scope} hypothesis />
        </>
      )}
      <div className={s.section}>
        <h3 className={s.sectionTitle}>Limitations</h3>
        <ul className={`${s.items} ${s.limits}`}>
          {answer.limitations.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      </div>
      {answer.source_references.length > 0 && (
        <div className={s.section}>
          <h3 className={s.sectionTitle}>Sources</h3>
          <Refs refs={answer.source_references} scope={scope} />
        </div>
      )}
      {answer.context_id && <p className={s.trace}>context {shortId(answer.context_id)} · request {shortId(answer.request_id)}</p>}
    </div>
  );
}

function Problem({ error }: { error: Error }) {
  const e = error instanceof ApiError ? error : null;
  let icon: ReactNode = <AlertTriangle size={16} aria-hidden />;
  let title = "The copilot could not answer";
  let body: ReactNode = error.message;
  if (e?.code === "COPILOT_UNAVAILABLE") {
    icon = <PlugZap size={16} aria-hidden />;
    title = "Copilot unavailable";
    body = "The local model service is not reachable. Everything else in this workspace works without it; try again later.";
  } else if (e?.code === "COPILOT_BUSY") {
    icon = <Hourglass size={16} aria-hidden />;
    title = "Copilot busy";
    body = "Another answer is being generated. Ask again in a few seconds.";
  } else if (e?.code === "RATE_LIMITED") {
    icon = <Hourglass size={16} aria-hidden />;
    title = "Too many questions";
    body = "You have reached the per-minute limit. Ask again in a minute.";
  } else if (e?.code === "AI_RESPONSE_INVALID") {
    icon = <ShieldAlert size={16} aria-hidden />;
    title = "Answer discarded";
    const rule = Number(e.details.rule);
    body = `The model's answer failed validation because ${RULES[rule] ?? "it broke a safety rule"}, so it is not shown. Rephrase or ask again.`;
  } else if (e?.status === 403) {
    icon = <CircleSlash size={16} aria-hidden />;
    title = "Not permitted for your role";
  }
  return (
    <div className={s.problem} role="alert" data-code={e?.code ?? "ERROR"}>
      <h3>
        {icon}
        {title}
      </h3>
      <p>{body}</p>
      {e?.requestId && <span className={s.trace}>request {e.requestId}</span>}
    </div>
  );
}

export function CopilotPanel({ scope, kind }: { scope: CopilotScope; kind: "account" | "case" | "ring" }) {
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState<CopilotResponse | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const ask = async (q: string) => {
    const text = q.trim();
    if (!text || busy) return;
    setQuestion(text);
    setBusy(true);
    setError(null);
    try {
      setAnswer(await copilotService.query(text, scope));
    } catch (err) {
      setAnswer(null);
      setError(err as Error);
    } finally {
      setBusy(false);
    }
  };
  const submit = (e: FormEvent) => {
    e.preventDefault();
    void ask(question);
  };

  return (
    <section className={ui.panel} aria-label="Copilot">
      <div className={ui.panelHead}>
        <h2 className={ui.panelTitle}>
          <Sparkles size={14} aria-hidden className={s.titleIcon} />
          Copilot
        </h2>
        <EvidenceLabel kind="AI INTERPRETATION" />
      </div>
      <form className={s.form} onSubmit={submit}>
        <label className={ui.field}>
          <span className={ui.label}>Ask about this {kind}</span>
          <textarea
            className={`${ui.textarea} ${s.question}`}
            value={question}
            maxLength={MAX_QUESTION}
            rows={2}
            placeholder="Ask about the evidence on this page"
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void ask(question);
            }}
          />
        </label>
        <div className={s.formRow}>
          <div className={s.suggestions} role="group" aria-label="Suggested questions">
            {SUGGESTIONS[kind].map((q) => (
              <button key={q} type="button" className={`${ui.button} ${ui.small} ${ui.ghost}`} disabled={busy} onClick={() => void ask(q)}>
                {q}
              </button>
            ))}
          </div>
          <button type="submit" className={`${ui.button} ${ui.primary}`} disabled={busy || !question.trim()}>
            Ask
          </button>
        </div>
        <p className={s.note}>
          Answers draw only on evidence your role can already see and cite it. They are interpretations to check, not findings.
        </p>
      </form>
      <div className={s.output} aria-live="polite">
        {busy && (
          <div className={s.pending}>
            <Running label="Generating an answer from the cited evidence…" />
          </div>
        )}
        {!busy && error && <Problem error={error} />}
        {!busy && answer && <Answer answer={answer} scope={scope} />}
      </div>
    </section>
  );
}
