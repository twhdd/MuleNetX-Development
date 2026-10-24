"""Audit events (SRS §24.3). Append-only; metadata is sanitized (no secrets, no copilot text)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from mulenetx.core.logging import request_id_var
from mulenetx.core.timeutil import utcnow
from mulenetx.db.models.audit import AuditEvent

logger = logging.getLogger("mulenetx.audit")

_FORBIDDEN_METADATA_KEYS = frozenset({"password", "token", "access_token", "token_hash", "question", "answer"})


def _sanitize(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if metadata is None:
        return None
    return {k: v for k, v in metadata.items() if k.lower() not in _FORBIDDEN_METADATA_KEYS}


class AuditService:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    @staticmethod
    def build(
        action: str,
        resource_type: str,
        outcome: str,
        *,
        user_id: uuid.UUID | None = None,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> AuditEvent:
        return AuditEvent(
            event_id=uuid.uuid4(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            timestamp=utcnow(),
            request_id=request_id if request_id is not None else request_id_var.get(),
            metadata_=_sanitize(metadata),
        )

    def record_in(self, session: Session, action: str, resource_type: str, outcome: str, **kw: Any) -> None:
        """Record inside the caller's transaction (committed together with the audited change)."""
        session.add(self.build(action, resource_type, outcome, **kw))

    def record_now(self, action: str, resource_type: str, outcome: str, **kw: Any) -> None:
        """Record in an independent transaction (used for DENIED/FAILED events of failing requests)."""
        try:
            with self._factory() as session:
                session.add(self.build(action, resource_type, outcome, **kw))
                session.commit()
        except Exception:
            logger.exception("failed to write audit event %s", action)
            raise
