"""AT-RING-01: fixed community signals give the exact deterministic candidate score and class (SRS §9.2–§9.3);
communities below three members are not scored; scores below 0.50 are not persisted."""

from mulenetx.rings.candidates import score_communities
from tests.ringutil import inputs, load

EXP = load()["expected_candidate"]


def test_AT_RING_01_candidate_score() -> None:
    scored = score_communities(inputs())
    assert set(scored) == {"c-ring", "c-quiet"}  # c-pair has 2 members: not scored
    c = scored["c-ring"]
    for signal in ("H", "D", "C", "community_temporal_density", "M"):
        assert c.signals[signal]["value"] == EXP[signal], signal
        assert c.signals[signal]["available"] is True
    assert format(c.score, "f") == EXP["score"]
    assert c.candidate_class == EXP["class"]
    assert c.signals["member_count"] == 5 and c.signals["M_paths_truncated"] is False


def test_AT_RING_01_quiet_community_and_determinism() -> None:
    scored = score_communities(inputs())
    quiet = scored["c-quiet"]
    assert quiet.signals["H"]["value"] == "0.0000000"
    assert quiet.score < 0.5 and quiet.candidate_class == "NOT_SUSPICIOUS"
    assert score_communities(inputs()) == scored  # identical on rerun
