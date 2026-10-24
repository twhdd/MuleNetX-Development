"""AT-RING-02: a qualifying community yields a ring with deterministic identity, members, constituent transactions,
temporal span and source community, identical across reruns of the same context (SRS §9A.2, §9A.5)."""

import pytest
from sqlalchemy import func, select

from mulenetx.api.deps import get_services
from mulenetx.core import ids
from mulenetx.core.timeutil import utcnow
from mulenetx.db.models.rings import RingCandidate, RingFeatureSet, RingMembership, RingRiskAssessment
from mulenetx.rings.service import RingIntelligenceService, intelligence
from tests.apiutil import _Req
from tests.flowutil import RUN, SNAPSHOT
from tests.ingestutil import seed_synth_and_activate
from tests.ringutil import inputs, load

EXP = load()["expected_ring"]


def test_AT_RING_02_membership_and_span() -> None:
    ctx = inputs()
    ring = intelligence(ctx, ctx.communities["c-ring"])
    m = ring.membership
    assert m.members == EXP["members"] and m.ring_size == EXP["ring_size"]
    assert [t.transaction_id for _u, _v, t in m.constituent] == EXP["constituent"]
    assert int(m.start_time.timestamp()) == EXP["start"] and int(m.end_time.timestamp()) == EXP["end"]
    assert m.temporal_span_seconds == EXP["temporal_span_seconds"]
    again = intelligence(inputs(), inputs().communities["c-ring"])
    assert again.features.values == ring.features.values and again.risk == ring.risk
    assert ids.candidate_id(SNAPSHOT, RUN, "c-ring") == ids.candidate_id(SNAPSHOT, RUN, "c-ring")


@pytest.mark.integration
def test_AT_RING_02_stage_persists_idempotently(app, client, users) -> None:
    admin = users("ADMIN")
    _ds, run = seed_synth_and_activate(app, client, admin, key="rg")
    rt = get_services(_Req(app)).runtime
    service = RingIntelligenceService(rt)
    with rt.session_factory() as db:
        before = (
            db.execute(select(RingCandidate).where(RingCandidate.scoring_run_id == run["scoring_run_id"]))
            .scalars()
            .all()
        )
        counts = [
            db.execute(select(func.count()).select_from(t)).scalar_one()
            for t in (RingMembership, RingFeatureSet, RingRiskAssessment)
        ]
    assert before, "the synthetic dataset yields at least one candidate"
    for c in before:
        assert c.candidate_id == ids.candidate_id(c.graph_snapshot_id, c.scoring_run_id, c.community_id)
        assert c.candidate_status == "CANDIDATE" and c.candidate_score >= 0.5
    # re-running the analysis for the same context derives and re-inserts the same rows: nothing new appears
    import uuid

    analysis = service.analyze(
        uuid.UUID(_ds.dataset_id.hex),
        uuid.UUID(run["graph_snapshot_id"]),
        uuid.UUID(run["analytics_run_id"]),
        uuid.UUID(run["scoring_run_id"]),
    )
    with rt.session_factory() as db:
        service.persist(db, analysis, utcnow())
        db.commit()
        after = (
            db.execute(select(RingCandidate).where(RingCandidate.scoring_run_id == run["scoring_run_id"]))
            .scalars()
            .all()
        )
        assert sorted(c.candidate_id for c in after) == sorted(c.candidate_id for c in before)
        assert [
            db.execute(select(func.count()).select_from(t)).scalar_one()
            for t in (RingMembership, RingFeatureSet, RingRiskAssessment)
        ] == counts
