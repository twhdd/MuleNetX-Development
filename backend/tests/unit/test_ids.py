"""Deterministic identifiers (SRS §6.2.3): one frozen value per function plus content-string checks."""

import uuid

from mulenetx.core import ids

S = "11111111-1111-1111-1111-111111111111"
R = "22222222-2222-2222-2222-222222222222"
NS = uuid.UUID("6f1c2a3e-5b7d-4e0a-9c1f-2d8b4a6e0f13")


def test_namespace_is_fixed() -> None:
    assert ids.NAMESPACE == NS


def test_community_id_frozen_and_sorted() -> None:
    value = ids.community_id(S, "nx-v1", ["d:C2", "d:C1"])
    assert value == "f91c1390-5a47-5377-9751-7cec45347097"
    assert value == str(uuid.uuid5(NS, f"community|{S}|nx-v1|d:C1,d:C2"))
    assert ids.community_id(S, "nx-v1", ["d:C1", "d:C2"]) == value


def test_candidate_id_frozen() -> None:
    assert str(ids.candidate_id(S, R, "c0mm")) == "bcedf780-b031-5d97-9b3d-56d8c635b749"
    assert ids.candidate_id(S, R, "c0mm") == uuid.uuid5(NS, f"candidate|{S}|{R}|c0mm")


def test_motif_id_frozen_and_sorted() -> None:
    value = ids.motif_id(S, "nx-v1", "FAN_IN", 3600, ["d:0000000002", "d:0000000001"])
    assert str(value) == "e0051fbd-3a9a-5446-9487-9fb1c0d2434f"
    assert value == uuid.uuid5(NS, f"motif|{S}|nx-v1|FAN_IN|3600|d:0000000001,d:0000000002")


def test_path_id_keeps_order() -> None:
    value = ids.path_id(S, ["d:C2", "d:C1"])
    assert str(value) == "a05a72f1-e2e0-5e7a-8f38-65afa95071d3"
    assert value != ids.path_id(S, ["d:C1", "d:C2"])


def test_intervention_candidate_id_frozen() -> None:
    ring = "33333333-3333-3333-3333-333333333333"
    value = ids.intervention_candidate_id(S, R, ring, "EDGE_REMOVAL", ["d:C1>d:C2"], "ab" * 32)
    assert str(value) == "a350d202-090c-533e-8cac-743fb692741c"


def test_reference_ring_id_frozen() -> None:
    value = ids.reference_ring_id("refring-v1", ["d:C3", "d:C1"])
    assert str(value) == "a32eadb9-882a-5d56-95ef-4a79a416f054"
    assert value == uuid.uuid5(NS, "refring|refring-v1|d:C1,d:C3")
