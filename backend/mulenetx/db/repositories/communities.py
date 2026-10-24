"""Graph metrics and community read models (SRS §19.2, §8, §19.12)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.core.lineage import Lineage, lineage_envelope
from mulenetx.core.pagination import PageRequest, offset_page
from mulenetx.db.models.account_analytics import AccountGraphMetrics
from mulenetx.db.models.canonical import Account
from mulenetx.db.models.communities import Community, CommunityMembership
from mulenetx.db.models.lineage import AnalyticsRun
from mulenetx.db.repositories.context import active, active_lineage


def resolve_analytics_run(db: Session, analytics_run_id: uuid.UUID | None) -> AnalyticsRun:
    run_id = analytics_run_id if analytics_run_id is not None else active(db).analytics_run_id
    if run_id is None:
        raise AppError(ec.NOT_FOUND, "No active analytics run.", {"resource": "analytics_run"})
    run = db.get(AnalyticsRun, run_id)
    if run is None or run.status != "SUCCEEDED":
        raise AppError(ec.NOT_FOUND, details={"resource": "analytics_run"})
    return run


def _lineage(run: AnalyticsRun) -> Lineage:
    return Lineage(graph_snapshot_id=str(run.graph_snapshot_id), analytics_run_id=str(run.analytics_run_id))


def metrics(db: Session, account_id: str, analytics_run_id: uuid.UUID | None) -> dict[str, Any]:
    run = resolve_analytics_run(db, analytics_run_id)
    m = db.get(AccountGraphMetrics, (run.analytics_run_id, account_id))
    if m is None:
        raise AppError(ec.NOT_FOUND, details={"resource": "graph_metrics"})
    return {
        "account_id": account_id,
        "analytics_run_id": str(run.analytics_run_id),
        "analytics_version": run.analytics_version,
        "engine": run.engine,
        "degree": m.degree,
        "in_degree": m.in_degree,
        "out_degree": m.out_degree,
        "pagerank_raw": m.pagerank_raw,
        "pagerank_norm": float(m.pagerank_norm),
        "betweenness_raw": m.betweenness_raw,
        "component_id": m.component_id,
        "component_size": m.component_size,
        "community_id": m.community_id,
        "community_size": m.community_size,
        "algorithm_configuration": run.algorithm_configuration,
        **lineage_envelope(_lineage(run), active_lineage(db), run.completed_at),
    }


def _member(a: Account) -> dict[str, Any]:
    score = a.risk_score
    return {
        "account_id": a.account_id,
        "source_account_ref": a.source_account_ref,
        "account_type": a.account_type,
        "risk_tier": a.risk_tier,
        "risk_score": None if score is None else float(score),
    }


def community_view(c: Community) -> dict[str, Any]:
    return {
        "community_id": c.community_id,
        "analytics_run_id": str(c.analytics_run_id),
        "graph_snapshot_id": str(c.graph_snapshot_id),
        "algorithm": c.algorithm,
        "algorithm_version": c.algorithm_version,
        "member_count": c.member_count,
        "computed_at": c.computed_at.isoformat(),
        "analytical_summary": c.analytical_summary,
    }


def list_communities(db: Session, analytics_run_id: uuid.UUID | None, page: PageRequest, cap: int) -> dict[str, Any]:
    run = resolve_analytics_run(db, analytics_run_id)
    base = select(Community).where(Community.analytics_run_id == run.analytics_run_id)
    total = int(db.execute(select(func.count()).select_from(base.subquery())).scalar_one())
    rows = db.execute(
        base.order_by(Community.member_count.desc(), Community.community_id).offset(page.offset).limit(page.page_size)
    ).scalars()
    body = offset_page([community_view(c) for c in rows], page, total, cap)
    return {**body, **lineage_envelope(_lineage(run), active_lineage(db), run.completed_at)}


def community_detail(
    db: Session, community_id: str, analytics_run_id: uuid.UUID | None, page: PageRequest, cap: int
) -> dict[str, Any]:
    run = resolve_analytics_run(db, analytics_run_id)
    c = db.get(Community, (community_id, run.analytics_run_id))
    if c is None:
        raise AppError(ec.NOT_FOUND, details={"resource": "community"})
    members = select(CommunityMembership.account_id).where(
        CommunityMembership.analytics_run_id == run.analytics_run_id, CommunityMembership.community_id == community_id
    )
    total = int(db.execute(select(func.count()).select_from(members.subquery())).scalar_one())
    ids = [
        r[0]
        for r in db.execute(members.order_by(CommunityMembership.account_id).offset(page.offset).limit(page.page_size))
    ]
    accounts = {a.account_id: a for a in db.execute(select(Account).where(Account.account_id.in_(ids))).scalars()}
    items = [_member(accounts[a]) for a in ids if a in accounts]
    return {
        **community_view(c),
        "members": offset_page(items, page, total, cap),
        "interpretation": "Community membership is a graph-structural grouping, not evidence of a fraud ring.",
        **lineage_envelope(_lineage(run), active_lineage(db), c.computed_at),
    }


def account_community(
    db: Session, account_id: str, analytics_run_id: uuid.UUID | None, page: PageRequest, cap: int
) -> dict[str, Any]:
    run = resolve_analytics_run(db, analytics_run_id)
    cid = db.execute(
        select(CommunityMembership.community_id).where(
            CommunityMembership.analytics_run_id == run.analytics_run_id, CommunityMembership.account_id == account_id
        )
    ).scalar_one_or_none()
    if cid is None:
        raise AppError(ec.NOT_FOUND, details={"resource": "community"})
    return {"account_id": account_id, **community_detail(db, cid, run.analytics_run_id, page, cap)}
