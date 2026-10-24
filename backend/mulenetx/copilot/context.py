"""Authorized context retrieval and assembly (SRS §21.2, §21.4).

Every section is loaded through the same repositories and permission checks as the matching API endpoint, so
the copilot can never see more than the caller could. Every item carries a stable `ref` and lineage; free text is
truncated to `copilot_max_text_field`; the whole context is bounded by `copilot_max_context_tokens` (estimated
as ceil(len(json)/4)) with deterministic truncation by section priority, then item order."""

from __future__ import annotations

import json
import math
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from mulenetx.auth.permissions import is_allowed
from mulenetx.auth.service import Principal
from mulenetx.core import error_codes as ec
from mulenetx.core.config import Settings
from mulenetx.core.errors import AppError
from mulenetx.core.runtime import Runtime

# lowest priority last: truncation removes items from the end of this order first
PRIORITY = (
    "account",
    "risk_assessment",
    "ring",
    "findings",
    "shap",
    "temporal",
    "motifs",
    "graph",
    "community",
    "money_flow",
    "transactions",
)
LIST_SECTIONS = {"transactions", "shap", "temporal", "motifs", "money_flow", "findings"}
FREE_TEXT_KEYS = {
    "description",
    "title",
    "source_account_ref",
    "source_transaction_ref",
    "name",
    "statement",
    "interpretation",
}


@dataclass
class Context:
    context_id: str
    sections: dict[str, Any]
    refs: set[str] = field(default_factory=set)
    limitations: list[str] = field(default_factory=list)
    referenced: dict[str, str] = field(default_factory=dict)

    def payload(self) -> dict[str, Any]:
        return {"context_id": self.context_id, **self.sections}


def estimate_tokens(obj: Any) -> int:
    return math.ceil(len(json.dumps(obj, ensure_ascii=False, sort_keys=True)) / 4)


def _clip(value: Any, limit: int, notes: list[str], where: str) -> Any:
    if isinstance(value, dict):
        return {
            k: (_clip_text(v, limit, notes, f"{where}.{k}") if k in FREE_TEXT_KEYS else _clip(v, limit, notes, where))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_clip(v, limit, notes, where) for v in value]
    return value


def _clip_text(value: Any, limit: int, notes: list[str], where: str) -> Any:
    if isinstance(value, str) and len(value) > limit:
        notes.append(f"{where} truncated to {limit} characters")
        return value[:limit]
    return value


def _require(principal: Principal, permission: str) -> None:
    if not is_allowed(principal.role, permission):
        raise AppError(ec.FORBIDDEN, details={"permission": permission})


class Retriever:
    """Loads sections for one request; a section the caller may not read is omitted and reported."""

    def __init__(self, rt: Runtime, db: Session, principal: Principal) -> None:
        self.rt = rt
        self.db = db
        self.principal = principal
        self.limitations: list[str] = []

    def _section(self, permission: str, name: str, load: Callable[[], Any]) -> Any:
        if not is_allowed(self.principal.role, permission):
            self.limitations.append(f"{name} omitted: your role lacks {permission}")
            return None
        try:
            return load()
        except AppError as exc:
            self.limitations.append(f"{name} unavailable: {exc.code}")
            return None

    # ── account-centred sections ─────────────────────────────────────────
    def account(self, account_id: str) -> dict[str, Any] | None:
        from mulenetx.db.repositories import accounts

        def load() -> dict[str, Any]:
            a = accounts.get(self.db, account_id)
            return {
                "ref": f"account:{a['account_id']}",
                "lineage": a["lineage"],
                **{
                    k: a[k]
                    for k in (
                        "account_id",
                        "source_account_ref",
                        "account_type",
                        "risk_score",
                        "risk_tier",
                        "community_id",
                        "is_stale",
                    )
                },
            }

        result: dict[str, Any] | None = self._section("account.read", "account", load)
        return result

    def risk_assessment(self, account_id: str) -> dict[str, Any] | None:
        from mulenetx.db.repositories import risk

        def load() -> dict[str, Any]:
            r = risk.risk(self.db, account_id, None)
            keep = (
                "final_score",
                "risk_tier",
                "ml_score",
                "graph_signal_score",
                "behavioral_signal_score",
                "rule_signal_score",
                "propagated_risk",
                "signal_coverage",
                "fired_rules",
                "interpretation",
            )
            return {"ref": f"assessment:{r['assessment_id']}", "lineage": r["lineage"], **{k: r[k] for k in keep}}

        result: dict[str, Any] | None = self._section("risk.read", "risk_assessment", load)
        return result

    def shap(self, account_id: str) -> list[dict[str, Any]] | None:
        from mulenetx.explain.shap_service import explain

        def load() -> list[dict[str, Any]]:
            s = explain(self.db, account_id, None, 8)
            return [
                {
                    "ref": f"shap:{s['assessment_id']}:{c['feature_id']}",
                    "lineage": s["lineage"],
                    "feature_id": c["feature_id"],
                    "name": c["name"],
                    "shap": c["shap"],
                    "value": c["value"],
                    "explains": "ML component only",
                }
                for c in s["contributions"]
            ]

        result: list[dict[str, Any]] | None = self._section("shap.read", "shap", load)
        return result

    def temporal(self, account_id: str) -> list[dict[str, Any]] | None:
        from mulenetx.db.repositories import risk

        def load() -> list[dict[str, Any]]:
            t = risk.temporal(self.db, account_id, None)
            return [
                {
                    "ref": f"feature:{account_id}:{f['feature_id']}",
                    "lineage": t["lineage"],
                    "feature_id": f["feature_id"],
                    "name": f["name"],
                    "value": f["value"],
                    "state": f["state"],
                }
                for f in t["features"]
            ]

        result: list[dict[str, Any]] | None = self._section("temporal.read", "temporal", load)
        return result

    def transactions(self, account_id: str) -> list[dict[str, Any]] | None:
        from mulenetx.db.repositories import transactions

        def load() -> list[dict[str, Any]]:
            page = transactions.page_for_account(
                self.db,
                account_id,
                start=None,
                end=None,
                tx_type=None,
                direction="any",
                page_size=20,
                cursor=None,
                max_days=self.rt.settings.max_transaction_range_days,
            )
            return [
                {
                    "ref": f"transaction:{t['transaction_id']}",
                    "lineage": {"dataset_id": t["dataset_id"]},
                    **{
                        k: t[k]
                        for k in (
                            "transaction_id",
                            "source_account_id",
                            "destination_account_id",
                            "amount",
                            "timestamp",
                            "transaction_type",
                            "direction",
                        )
                    },
                }
                for t in page["items"]
            ]

        result: list[dict[str, Any]] | None = self._section("transaction.read", "transactions", load)
        return result

    def graph(self, account_id: str) -> dict[str, Any] | None:
        from mulenetx.db.repositories import communities

        def load() -> dict[str, Any]:
            m = communities.metrics(self.db, account_id, None)
            return {
                "ref": f"metrics:{m['analytics_run_id']}:{account_id}",
                "lineage": m["lineage"],
                **{
                    k: m[k]
                    for k in (
                        "degree",
                        "in_degree",
                        "out_degree",
                        "pagerank_norm",
                        "betweenness_raw",
                        "component_size",
                        "community_size",
                    )
                },
            }

        result: dict[str, Any] | None = self._section("graph.analytics.read", "graph", load)
        return result

    def community(self, account_id: str) -> dict[str, Any] | None:
        from mulenetx.core.pagination import PageRequest
        from mulenetx.db.repositories import communities

        def load() -> dict[str, Any]:
            c = communities.account_community(self.db, account_id, None, PageRequest(1, 10), 10_000)
            return {
                "ref": f"community:{c['community_id']}",
                "lineage": c["lineage"],
                "community_id": c["community_id"],
                "member_count": c["member_count"],
                "interpretation": c["interpretation"],
                "members": [
                    {"account_id": x["account_id"], "risk_tier": x["risk_tier"]} for x in c["members"]["items"]
                ],
            }

        result: dict[str, Any] | None = self._section("community.read", "community", load)
        return result

    def motifs(self, accounts: list[str], analytics_run_id: uuid.UUID | None = None) -> list[dict[str, Any]] | None:
        from mulenetx.core.pagination import PageRequest
        from mulenetx.db.repositories import motifs

        def load() -> list[dict[str, Any]]:
            page = motifs.list_for_accounts(
                self.db, accounts, analytics_run_id, None, None, None, PageRequest(1, 15), 10_000
            )
            return [
                {
                    "ref": f"motif:{m['motif_id']}",
                    "lineage": page["lineage"],
                    **{
                        k: m[k]
                        for k in (
                            "motif_type",
                            "anchor_account_id",
                            "start_time",
                            "end_time",
                            "participating_account_ids",
                            "motif_confidence",
                            "order_ambiguous",
                        )
                    },
                }
                for m in page["items"]
            ]

        result: list[dict[str, Any]] | None = self._section("motif.read", "motifs", load)
        return result

    def money_flow(self, account_id: str) -> list[dict[str, Any]] | None:
        from mulenetx.graph.neighborhood import neighborhood

        def load() -> list[dict[str, Any]]:
            nb = neighborhood(self.rt, self.db, account_id, 1, 50, 100, None)
            return [
                {
                    "ref": f"edge:{nb['graph_snapshot_id']}:{e['source_account_id']}>{e['destination_account_id']}",
                    "lineage": nb["lineage"],
                    **e,
                }
                for e in nb["edges"]
            ]

        result: list[dict[str, Any]] | None = self._section("graph.read", "money_flow", load)
        return result

    # ── ring and case ────────────────────────────────────────────────────
    def ring(self, ring_id: uuid.UUID) -> tuple[dict[str, Any] | None, list[str], uuid.UUID | None]:
        from mulenetx.db.repositories import rings
        from mulenetx.db.repositories.context import active_lineage

        c = rings.get_candidate(self.db, ring_id)
        view = rings.ring_view(self.db, c, active_lineage(self.db))
        members = rings.member_ids(self.db, c)
        section: dict[str, Any] = {
            "ref": f"ring:{ring_id}",
            "lineage": view["lineage"],
            **{
                k: view[k]
                for k in (
                    "candidate_class",
                    "candidate_status",
                    "candidate_score",
                    "signal_summary",
                    "member_count",
                    "transaction_count",
                    "start_time",
                    "end_time",
                    "ring_risk_score",
                    "ring_risk_tier",
                    "interpretation",
                )
            },
            "members": members[:25],
        }
        if c.candidate_class == "POTENTIAL_FRAUD_RING_CANDIDATE":
            risk = rings.risk(self.db, c)
            section["ring_risk_components"] = {x["component"]: x["value"] for x in risk["components"]}
        return section, members, c.analytics_run_id

    def case(self, case_id: uuid.UUID) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
        from mulenetx.core.pagination import PageRequest
        from mulenetx.investigation.service import InvestigationService, case_view, finding_view, subject_view

        service = InvestigationService(None)  # type: ignore[arg-type]  # reads only
        c = service.get(self.db, case_id)
        view = case_view(c)
        subjects = [subject_view(s) for s in service.subjects(self.db, case_id, PageRequest(1, 100))[0]]
        findings = [finding_view(f) for f in service.findings(self.db, case_id, PageRequest(1, 50))[0]]
        case_section = {
            "ref": f"case:{case_id}",
            "lineage": {},
            **{k: view[k] for k in ("title", "status", "priority")},
            "subjects": [
                {"subject_type": s["subject_type"], "subject_id": s["subject_id"]} for s in subjects if s["active"]
            ],
        }
        finding_items = [
            {
                "ref": f"finding:{f['finding_id']}",
                "lineage": {},
                "type": f["type"],
                "description": f["description"],
                "evidence": f["evidence"],
                "label": f["label"],
            }
            for f in findings
        ]
        accounts = [s["subject_id"] for s in subjects if s["active"] and s["subject_type"] == "ACCOUNT"]
        return case_section, finding_items, accounts


def collect_refs(obj: Any, out: set[str]) -> None:
    if isinstance(obj, dict):
        ref = obj.get("ref")
        if isinstance(ref, str):
            out.add(ref)
        for v in obj.values():
            collect_refs(v, out)
    elif isinstance(obj, list):
        for v in obj:
            collect_refs(v, out)


def bound(sections: dict[str, Any], settings: Settings, notes: list[str], context_id: str) -> dict[str, Any]:
    """Clip free text, then drop items from the lowest-priority sections until the token estimate fits."""
    clipped = {k: _clip(v, settings.copilot_max_text_field, notes, k) for k, v in sections.items()}
    budget = settings.copilot_max_context_tokens
    for name in reversed(PRIORITY):
        while estimate_tokens({"context_id": context_id, **clipped}) > budget:
            value = clipped.get(name)
            if isinstance(value, list) and value:
                value.pop()
                notes.append(f"{name}: lowest-priority items dropped to fit the context budget")
            elif value:
                clipped[name] = {} if isinstance(value, dict) else []
                notes.append(f"{name}: dropped to fit the context budget")
            else:
                break
    return clipped


def assemble(
    rt: Runtime,
    db: Session,
    principal: Principal,
    intent: str,
    wanted: list[str],
    account_id: str | None,
    case_id: str | None,
    ring_id: str | None,
) -> Context:
    """Load and bound the context. Malformed or unauthorized references are rejected before any model call."""
    r = Retriever(rt, db, principal)
    referenced: dict[str, str] = {}
    sections: dict[str, Any] = {}
    focus_accounts: list[str] = []
    ring_run: uuid.UUID | None = None
    if account_id is not None:
        _require(principal, "account.read")
        from mulenetx.db.repositories import accounts

        accounts.require(db, account_id)  # 404 before any model call
        referenced["account"] = account_id
        focus_accounts = [account_id]
    if ring_id is not None:
        _require(principal, "ring.read")
        try:
            rid = uuid.UUID(ring_id)
        except ValueError as exc:
            raise AppError(ec.VALIDATION_ERROR, details={"field": "ring_id"}) from exc
        sections["ring"], members, ring_run = r.ring(rid)
        referenced["ring"] = ring_id
        focus_accounts = focus_accounts or members
    if case_id is not None:
        _require(principal, "case.read")
        try:
            cid = uuid.UUID(case_id)
        except ValueError as exc:
            raise AppError(ec.VALIDATION_ERROR, details={"field": "case_id"}) from exc
        case_section, findings, case_accounts = r.case(cid)
        sections["case"] = case_section
        sections["findings"] = findings
        referenced["case"] = case_id
        focus_accounts = focus_accounts or case_accounts[:1]
    subject = focus_accounts[0] if focus_accounts else None
    if subject is not None:
        loaders: dict[str, Callable[[], Any]] = {
            "account": lambda: r.account(subject),
            "risk_assessment": lambda: r.risk_assessment(subject),
            "shap": lambda: r.shap(subject),
            "temporal": lambda: r.temporal(subject),
            "transactions": lambda: r.transactions(subject),
            "graph": lambda: r.graph(subject),
            "community": lambda: r.community(subject),
            "money_flow": lambda: r.money_flow(subject),
            "motifs": lambda: r.motifs(focus_accounts[:25] if ring_id else [subject], ring_run),
        }
        for name in wanted:
            if name in loaders and name not in sections:
                value = loaders[name]()
                if value is not None:
                    sections[name] = value
    if "findings" in wanted and "findings" not in sections:
        sections["findings"] = []
    context_id = str(uuid.uuid4())
    notes = list(r.limitations)
    bounded = bound(sections, rt.settings, notes, context_id)
    ctx = Context(context_id, bounded, limitations=notes, referenced=referenced)
    collect_refs(bounded, ctx.refs)
    return ctx
