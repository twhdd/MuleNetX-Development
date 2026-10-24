"""Request-scoped dependencies: runtime, DB session, services, principal and permission checks."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from mulenetx.audit.service import AuditService
from mulenetx.auth.passwords import Passwords
from mulenetx.auth.permissions import is_allowed
from mulenetx.auth.service import AuthService, Principal
from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.core.logging import user_id_var
from mulenetx.core.runtime import Runtime
from mulenetx.ingestion.service import IngestionService
from mulenetx.interventions.service import InterventionService

if TYPE_CHECKING:
    from mulenetx.copilot.service import CopilotService
from mulenetx.investigation.service import InvestigationService
from mulenetx.jobs.service import JobService


@dataclass
class Services:
    """Application services built once per app (services are stateless; sessions are per request)."""

    runtime: Runtime
    _cache: dict[str, Any] = field(default_factory=dict)

    def _get(self, key: str, build: Callable[[], Any]) -> Any:
        if key not in self._cache:
            self._cache[key] = build()
        return self._cache[key]

    @property
    def audit(self) -> AuditService:
        result: AuditService = self._get("audit", lambda: AuditService(self.runtime.session_factory))
        return result

    @property
    def auth(self) -> AuthService:
        result: AuthService = self._get(
            "auth", lambda: AuthService(self.runtime.settings, self.audit, Passwords(self.runtime.settings))
        )
        return result

    @property
    def jobs(self) -> JobService:
        result: JobService = self._get("jobs", lambda: JobService(self.runtime.settings, self.audit))
        return result

    @property
    def ingestion(self) -> IngestionService:
        result: IngestionService = self._get(
            "ingestion", lambda: IngestionService(self.runtime.settings, self.audit, self.jobs)
        )
        return result

    @property
    def investigation(self) -> InvestigationService:
        result: InvestigationService = self._get("investigation", lambda: InvestigationService(self.audit))
        return result

    @property
    def copilot(self) -> CopilotService:
        from mulenetx.copilot.service import CopilotService

        result: CopilotService = self._get("copilot", lambda: CopilotService(self.runtime, self.audit))
        return result

    @property
    def interventions(self) -> InterventionService:
        result: InterventionService = self._get(
            "interventions", lambda: InterventionService(self.runtime.settings, self.audit)
        )
        return result


def get_runtime(request: Request) -> Runtime:
    rt: Runtime = request.app.state.runtime
    return rt


def get_services(request: Request) -> Services:
    svc = getattr(request.app.state, "services", None)
    if svc is None:
        svc = Services(get_runtime(request))
        request.app.state.services = svc
    result: Services = svc
    return result


def get_db(request: Request) -> Iterator[Session]:
    session = get_runtime(request).session_factory()
    try:
        yield session
    finally:
        if session.in_transaction():
            session.rollback()
        session.close()


def _bearer(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


def current_principal(
    request: Request, db: Session = Depends(get_db), services: Services = Depends(get_services)
) -> Principal:
    token = _bearer(request)
    principal = None if token is None else services.auth.authenticate(db, token)
    if principal is None:
        raise AppError(ec.UNAUTHENTICATED)
    request.scope.setdefault("state", {})["user_id"] = str(principal.user_id)
    user_id_var.set(str(principal.user_id))
    return principal


def deny(
    services: Services, principal: Principal, permission: str, request: Request, resource_id: str | None = None
) -> AppError:
    """Audit an authorization denial (independent transaction) and return the 403 error to raise."""
    services.audit.record_now(
        "authz.denied",
        "endpoint",
        "DENIED",
        user_id=principal.user_id,
        resource_id=resource_id,
        metadata={"permission": permission, "method": request.method, "path": request.url.path, "role": principal.role},
    )
    return AppError(ec.FORBIDDEN)


def require(permission: str) -> Callable[..., Principal]:
    def dependency(
        request: Request,
        principal: Principal = Depends(current_principal),
        services: Services = Depends(get_services),
    ) -> Principal:
        if not is_allowed(principal.role, permission):
            raise deny(services, principal, permission, request)
        return principal

    dependency.__name__ = f"require_{permission.replace('.', '_')}"
    dependency.permission = permission  # type: ignore[attr-defined]  # read by the OpenAPI annotation
    return dependency
