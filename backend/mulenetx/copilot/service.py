"""CopilotService (SRS §21): intent → authorized context → prompt → local Ollama → validation → response.
Audit records metadata only (intent, referenced resource IDs, context_id, outcome, latency), never the question
or the answer (§24.3)."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from mulenetx.audit.service import AuditService
from mulenetx.auth.service import Principal
from mulenetx.copilot import context as context_module
from mulenetx.copilot import intents, prompt, validation
from mulenetx.copilot.limiter import Limiter
from mulenetx.copilot.ollama_client import OllamaClient
from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.core.runtime import Runtime
from mulenetx.core.timeutil import isoformat_utc, utcnow


class CopilotService:
    def __init__(self, runtime: Runtime, audit: AuditService, client: OllamaClient | None = None) -> None:
        s = runtime.settings
        self.rt = runtime
        self.audit = audit
        # window = context budget + output budget + 2,048 for the system rules and a 4,000-character question
        num_ctx = s.copilot_max_context_tokens + s.copilot_max_output_tokens + 2048
        self.client = client or OllamaClient(s.ollama_url, s.ollama_model, s.copilot_timeout_seconds, num_ctx=num_ctx)
        self.limiter = Limiter(s.copilot_max_concurrency, s.copilot_queue_wait_seconds, s.copilot_rate_per_minute)

    def query(
        self,
        db: Session,
        principal: Principal,
        question: str,
        account_id: str | None,
        case_id: str | None,
        ring_id: str | None,
        request_id: str | None,
        context_options: dict[str, bool] | None = None,
    ) -> dict[str, Any]:
        started = time.monotonic()
        meta: dict[str, Any] = {"account_id": account_id, "case_id": case_id, "ring_id": ring_id}
        outcome, intent, context_id = "FAILED", None, None
        try:
            self.limiter.check_rate(principal.user_id)
            c = intents.classify(question, account_id, case_id, ring_id)
            intent = c.intent
            if c.intent == intents.UNSUPPORTED:
                outcome = "SUCCESS"
                return self._unsupported(request_id, c.reason)
            wanted = [x for x in intents.sections(c.intent) if (context_options or {}).get(x, True)]
            ctx = context_module.assemble(self.rt, db, principal, c.intent, wanted, account_id, case_id, ring_id)
            context_id = ctx.context_id
            payload = ctx.payload()
            with self.limiter.slot():
                gen = self.client.generate(
                    prompt.messages(question, c.intent, payload),
                    prompt.SCHEMA,
                    self.rt.settings.copilot_max_output_tokens,
                )
            verdict, answer = validation.validate(
                gen.content,
                ctx.refs,
                json.dumps(payload, ensure_ascii=False),
                self.rt.settings.copilot_max_output_tokens,
                gen.output_tokens,
                self.rt.settings.copilot_deny_list_version,
            )
            if not verdict.ok or answer is None:
                meta["validation_rule"] = verdict.rule
                raise AppError(ec.AI_RESPONSE_INVALID, details={"rule": verdict.rule, "reason": verdict.detail})
            outcome = "SUCCESS"
            return {
                "request_id": request_id or str(uuid.uuid4()),
                "intent": c.intent,
                "facts": answer["facts"],
                "observed_signals": answer["observed_signals"],
                "possible_interpretation": answer["possible_interpretation"],
                "limitations": [*answer["limitations"], *ctx.limitations],
                "source_references": answer["source_references"],
                "model": {"provider": "ollama", "model": gen.model, "model_digest": gen.model_digest},
                "context_id": ctx.context_id,
                "generated_at": isoformat_utc(utcnow()),
                "ai_generated": True,
                "label": "AI INTERPRETATION",
            }
        except AppError as exc:
            outcome = "DENIED" if exc.code in (ec.FORBIDDEN,) else "FAILED"
            meta["error_code"] = exc.code
            raise
        finally:
            self.audit.record_now(
                "copilot.query",
                "copilot",
                outcome,
                user_id=principal.user_id,
                resource_id=context_id,
                request_id=request_id,
                metadata={
                    **meta,
                    "intent": intent,
                    "context_id": context_id,
                    "latency_ms": round((time.monotonic() - started) * 1000, 1),
                },
            )

    @staticmethod
    def _unsupported(request_id: str | None, reason: str | None) -> dict[str, Any]:
        return {
            "request_id": request_id or str(uuid.uuid4()),
            "intent": intents.UNSUPPORTED,
            "facts": [],
            "observed_signals": [],
            "possible_interpretation": [],
            "limitations": [
                "The copilot answers questions about a referenced account, case or ring "
                "(summary, risk, graph, timing, money flow).",
                *([reason] if reason else []),
            ],
            "source_references": [],
            "model": None,
            "context_id": None,
            "generated_at": isoformat_utc(utcnow()),
            "ai_generated": False,
            "label": "AI INTERPRETATION",
        }
