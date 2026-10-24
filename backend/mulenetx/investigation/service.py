"""InvestigationService (SRS §17, §19.10, §22.2): cases, subjects and findings with server-side rules."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mulenetx.audit.service import AuditService
from mulenetx.auth.permissions import CASE_FIELD_RULES, PARTICIPANT_ONLY, transition_rule_key
from mulenetx.auth.service import Principal
from mulenetx.core import error_codes as ec
from mulenetx.core import ids
from mulenetx.core.errors import AppError
from mulenetx.core.pagination import PageRequest
from mulenetx.core.timeutil import isoformat_utc, utcnow
from mulenetx.db.models.account_analytics import RiskAssessment, ShapExplanation
from mulenetx.db.models.auth import User
from mulenetx.db.models.canonical import Account, Transaction
from mulenetx.db.models.communities import Community
from mulenetx.db.models.interventions import InterventionScenario
from mulenetx.db.models.investigation import Case, CaseSubject, Finding
from mulenetx.db.models.lineage import GraphSnapshot
from mulenetx.db.models.motifs import TemporalMotif
from mulenetx.db.models.rings import RingCandidate
from mulenetx.investigation.cases import PRIORITIES, is_valid_transition

MAX_DESCRIPTION = 20_000
SUBJECT_TYPES = ("ACCOUNT", "TRANSACTION", "RING", "SCENARIO")
EVIDENCE_TYPES = (
    "transaction",
    "account",
    "risk_assessment",
    "graph_snapshot",
    "shap_explanation",
    "motif",
    "community",
    "ring",
    "path",
    "scenario",
)

Denier = Callable[[str, str | None], AppError]


def _iso(v: Any) -> str | None:
    return None if v is None else isoformat_utc(v)


def case_view(c: Case) -> dict[str, Any]:
    return {
        "case_id": str(c.case_id),
        "title": c.title,
        "status": c.status,
        "priority": c.priority,
        "assigned_to": None if c.assigned_to is None else str(c.assigned_to),
        "created_by": str(c.created_by),
        "created_at": _iso(c.created_at),
        "updated_at": _iso(c.updated_at),
        "closed_at": _iso(c.closed_at),
        "version": c.version,
    }


def subject_view(s: CaseSubject) -> dict[str, Any]:
    return {
        "case_id": str(s.case_id),
        "subject_type": s.subject_type,
        "subject_id": s.subject_id,
        "added_by": str(s.added_by),
        "added_at": _iso(s.added_at),
        "removed_by": None if s.removed_by is None else str(s.removed_by),
        "removed_at": _iso(s.removed_at),
        "active": s.removed_at is None,
    }


def finding_view(f: Finding) -> dict[str, Any]:
    return {
        "finding_id": str(f.finding_id),
        "case_id": str(f.case_id),
        "type": f.type,
        "description": f.description,
        "evidence": f.evidence,
        "source": f.source,
        "created_by": str(f.created_by),
        "created_at": _iso(f.created_at),
        "label": "INVESTIGATOR FINDING",
    }


def is_participant(c: Case, principal: Principal) -> bool:
    return principal.user_id in (c.created_by, c.assigned_to)


class InvestigationService:
    def __init__(self, audit: AuditService) -> None:
        self.audit = audit

    # ── cases ──────────────────────────────────────────────────────────────

    def _active_user(self, db: Session, user_id: uuid.UUID) -> User:
        user = db.get(User, user_id)
        if user is None or not user.is_active:
            raise AppError(ec.VALIDATION_ERROR, "The assignee must be an active user.", {"field": "assigned_to"})
        return user

    def create(
        self, db: Session, actor: Principal, title: str, priority: str, assigned_to: uuid.UUID | None, deny: Denier
    ) -> Case:
        title = title.strip()
        if not title or len(title) > 250:
            raise AppError(ec.VALIDATION_ERROR, details={"field": "title"})
        if priority not in PRIORITIES:
            raise AppError(ec.VALIDATION_ERROR, details={"field": "priority"})
        if assigned_to is not None:
            if CASE_FIELD_RULES["assigned_to"][actor.role] == "deny":  # type: ignore[index]
                raise deny("case.assign", None)
            self._active_user(db, assigned_to)
        now = utcnow()
        case = Case(
            case_id=uuid.uuid4(),
            title=title,
            status="OPEN",
            priority=priority,
            assigned_to=assigned_to,
            created_by=actor.user_id,
            created_at=now,
            updated_at=now,
            version=1,
        )
        db.add(case)
        db.flush()
        self.audit.record_in(
            db,
            "case.create",
            "case",
            "SUCCESS",
            user_id=actor.user_id,
            resource_id=str(case.case_id),
            metadata={"priority": priority},
        )
        db.commit()
        return case

    def get(self, db: Session, case_id: uuid.UUID, lock: bool = False) -> Case:
        case = db.get(Case, case_id, with_for_update=lock)
        if case is None:
            raise AppError(ec.NOT_FOUND, details={"resource": "case"})
        return case

    def list_cases(
        self, db: Session, page: PageRequest, status: str | None, assigned_to: uuid.UUID | None
    ) -> tuple[list[Case], int]:
        q = select(Case)
        if status is not None:
            q = q.where(Case.status == status)
        if assigned_to is not None:
            q = q.where(Case.assigned_to == assigned_to)
        total = int(db.execute(select(func.count()).select_from(q.subquery())).scalar_one())
        rows = db.execute(q.order_by(Case.updated_at.desc(), Case.case_id).offset(page.offset).limit(page.page_size))
        return list(rows.scalars()), total

    def _allowed(self, rule_key: str, actor: Principal, case: Case) -> bool:
        scope = CASE_FIELD_RULES[rule_key][actor.role]  # type: ignore[index]
        return scope == "any" or (scope == "participant" and is_participant(case, actor))

    def patch(
        self, db: Session, actor: Principal, case_id: uuid.UUID, version: int, changes: dict[str, Any], deny: Denier
    ) -> Case:
        case = self.get(db, case_id, lock=True)
        if case.version != version:
            raise AppError(ec.CASE_VERSION_CONFLICT, details={"current_version": case.version})
        if case.status == "CLOSED":
            raise AppError(ec.CONFLICT, "A closed case cannot be changed.")
        audit: list[tuple[str, dict[str, Any]]] = []
        target = changes.get("status")
        if target is not None and target != case.status:
            if not is_valid_transition(case.status, target):
                raise AppError(ec.INVALID_CASE_TRANSITION, details={"from": case.status, "to": target})
            if not self._allowed(transition_rule_key(case.status, target), actor, case):
                raise deny(
                    "case.resolve" if target in ("RESOLVED", "FALSE_POSITIVE", "CLOSED") else "case.update",
                    str(case_id),
                )
        for field in ("title", "priority", "assigned_to"):
            if field in changes and changes[field] != getattr(case, field):
                if not self._allowed(field, actor, case):
                    raise deny("case.assign" if field == "assigned_to" else "case.update", str(case_id))
        if "title" in changes and changes["title"] != case.title:
            title = str(changes["title"]).strip()
            if not title or len(title) > 250:
                raise AppError(ec.VALIDATION_ERROR, details={"field": "title"})
            audit.append(("case.update", {"field": "title"}))
            case.title = title
        if "priority" in changes and changes["priority"] != case.priority:
            if changes["priority"] not in PRIORITIES:
                raise AppError(ec.VALIDATION_ERROR, details={"field": "priority"})
            audit.append(("case.update", {"field": "priority", "to": changes["priority"]}))
            case.priority = changes["priority"]
        if "assigned_to" in changes and changes["assigned_to"] != case.assigned_to:
            if changes["assigned_to"] is not None:
                self._active_user(db, changes["assigned_to"])
            audit.append(
                (
                    "case.assign",
                    {"assigned_to": None if changes["assigned_to"] is None else str(changes["assigned_to"])},
                )
            )
            case.assigned_to = changes["assigned_to"]
        now = utcnow()
        if target is not None and target != case.status:
            audit.append(("case.transition", {"from": case.status, "to": target}))
            case.status = target
            if target == "CLOSED":
                case.closed_at = now
        if audit:
            case.version += 1
            case.updated_at = now
            for action, meta in audit:
                self.audit.record_in(
                    db, action, "case", "SUCCESS", user_id=actor.user_id, resource_id=str(case_id), metadata=meta
                )
        db.commit()
        return case

    # ── subjects ───────────────────────────────────────────────────────────

    def _participant_gate(self, actor: Principal, case: Case, permission: str, deny: Denier) -> None:
        if actor.role in PARTICIPANT_ONLY.get(permission, frozenset()) and not is_participant(case, actor):
            raise deny(permission, str(case.case_id))

    @staticmethod
    def subject_exists(db: Session, subject_type: str, subject_id: str) -> bool:
        if subject_type == "ACCOUNT":
            return db.get(Account, subject_id) is not None
        if subject_type == "TRANSACTION":
            return db.get(Transaction, subject_id) is not None
        try:
            uid = uuid.UUID(subject_id)
        except ValueError:
            return False
        if subject_type == "RING":
            return db.get(RingCandidate, uid) is not None
        if subject_type == "SCENARIO":
            return db.get(InterventionScenario, uid) is not None
        return False

    def add_subject(
        self, db: Session, actor: Principal, case_id: uuid.UUID, subject_type: str, subject_id: str, deny: Denier
    ) -> CaseSubject:
        case = self.get(db, case_id, lock=True)
        self._participant_gate(actor, case, "case_subject.manage", deny)
        if subject_type not in SUBJECT_TYPES:
            raise AppError(ec.VALIDATION_ERROR, details={"field": "subject_type"})
        if case.status == "CLOSED":
            raise AppError(ec.CONFLICT, "Subjects cannot be changed on a closed case.")
        if not self.subject_exists(db, subject_type, subject_id):
            raise AppError(ec.NOT_FOUND, details={"resource": "subject"})
        active = db.execute(
            select(CaseSubject).where(
                CaseSubject.case_id == case_id,
                CaseSubject.subject_type == subject_type,
                CaseSubject.subject_id == subject_id,
                CaseSubject.removed_at.is_(None),
            )
        ).first()
        if active is not None:
            raise AppError(ec.CONFLICT, "The subject is already linked to this case.")
        subject = CaseSubject(
            case_id=case_id, subject_type=subject_type, subject_id=subject_id, added_by=actor.user_id, added_at=utcnow()
        )
        db.add(subject)
        self.audit.record_in(
            db,
            "case_subject.add",
            "case",
            "SUCCESS",
            user_id=actor.user_id,
            resource_id=str(case_id),
            metadata={"subject_type": subject_type, "subject_id": subject_id},
        )
        db.commit()
        return subject

    def remove_subject(
        self, db: Session, actor: Principal, case_id: uuid.UUID, subject_type: str, subject_id: str, deny: Denier
    ) -> None:
        case = self.get(db, case_id, lock=True)
        self._participant_gate(actor, case, "case_subject.manage", deny)
        if case.status == "CLOSED":
            raise AppError(ec.CONFLICT, "Subjects cannot be changed on a closed case.")
        subject = db.execute(
            select(CaseSubject).where(
                CaseSubject.case_id == case_id,
                CaseSubject.subject_type == subject_type,
                CaseSubject.subject_id == subject_id,
                CaseSubject.removed_at.is_(None),
            )
        ).scalar_one_or_none()
        if subject is None:
            raise AppError(ec.NOT_FOUND, details={"resource": "subject"})
        subject.removed_by = actor.user_id
        subject.removed_at = utcnow()
        self.audit.record_in(
            db,
            "case_subject.remove",
            "case",
            "SUCCESS",
            user_id=actor.user_id,
            resource_id=str(case_id),
            metadata={"subject_type": subject_type, "subject_id": subject_id},
        )
        db.commit()

    @staticmethod
    def subjects(db: Session, case_id: uuid.UUID, page: PageRequest) -> tuple[list[CaseSubject], int]:
        q = select(CaseSubject).where(CaseSubject.case_id == case_id)
        total = int(db.execute(select(func.count()).select_from(q.subquery())).scalar_one())
        rows = db.execute(
            q.order_by(CaseSubject.added_at, CaseSubject.subject_type, CaseSubject.subject_id)
            .offset(page.offset)
            .limit(page.page_size)
        ).scalars()
        return list(rows), total

    # ── findings ───────────────────────────────────────────────────────────

    @staticmethod
    def evidence_exists(db: Session, ref: dict[str, Any]) -> bool:
        kind, rid = ref.get("type"), ref.get("id")
        if kind not in EVIDENCE_TYPES or not isinstance(rid, str) or not rid:
            return False
        if kind == "transaction":
            return db.get(Transaction, rid) is not None
        if kind == "account":
            return db.get(Account, rid) is not None
        if kind == "community":
            return db.execute(select(Community.community_id).where(Community.community_id == rid)).first() is not None
        try:
            uid = uuid.UUID(rid)
        except ValueError:
            return False
        if kind == "path":
            snapshot, accounts = ref.get("graph_snapshot_id"), ref.get("accounts")
            if not isinstance(snapshot, str) or not isinstance(accounts, list) or len(accounts) < 2:
                return False
            return (
                ids.path_id(snapshot, [str(a) for a in accounts]) == uid
                and db.get(GraphSnapshot, uuid.UUID(snapshot)) is not None
            )
        model = {
            "risk_assessment": RiskAssessment,
            "graph_snapshot": GraphSnapshot,
            "shap_explanation": ShapExplanation,
            "motif": TemporalMotif,
            "ring": RingCandidate,
            "scenario": InterventionScenario,
        }[kind]
        return db.get(model, uid) is not None

    def add_finding(
        self,
        db: Session,
        actor: Principal,
        case_id: uuid.UUID,
        ftype: str,
        description: str,
        evidence: list[dict[str, Any]],
        source: str,
        deny: Denier,
    ) -> Finding:
        case = self.get(db, case_id, lock=True)
        self._participant_gate(actor, case, "finding.create", deny)
        if case.status == "CLOSED":
            raise AppError(ec.CONFLICT, "Findings cannot be added to a closed case.")
        if not ftype.strip() or len(ftype) > 50:
            raise AppError(ec.VALIDATION_ERROR, details={"field": "type"})
        if not source.strip() or len(source) > 100:
            raise AppError(ec.VALIDATION_ERROR, details={"field": "source"})
        if not description.strip():
            raise AppError(ec.VALIDATION_ERROR, details={"field": "description"})
        if len(description) > MAX_DESCRIPTION:
            raise AppError(ec.LIMIT_EXCEEDED, details={"field": "description", "limit": MAX_DESCRIPTION})
        for i, ref in enumerate(evidence):
            if not self.evidence_exists(db, ref):
                raise AppError(ec.VALIDATION_ERROR, "An evidence reference does not exist.", {"field": f"evidence.{i}"})
        finding = Finding(
            finding_id=uuid.uuid4(),
            case_id=case_id,
            type=ftype.strip(),
            description=description,
            evidence=evidence,
            source=source.strip(),
            created_by=actor.user_id,
            created_at=utcnow(),
        )
        db.add(finding)
        self.audit.record_in(
            db,
            "finding.create",
            "case",
            "SUCCESS",
            user_id=actor.user_id,
            resource_id=str(case_id),
            metadata={"finding_id": str(finding.finding_id), "evidence_count": len(evidence)},
        )
        db.commit()
        return finding

    @staticmethod
    def findings(db: Session, case_id: uuid.UUID, page: PageRequest) -> tuple[list[Finding], int]:
        q = select(Finding).where(Finding.case_id == case_id)
        total = int(db.execute(select(func.count()).select_from(q.subquery())).scalar_one())
        rows = db.execute(
            q.order_by(Finding.created_at, Finding.finding_id).offset(page.offset).limit(page.page_size)
        ).scalars()
        return list(rows), total
