"""AT-E2E-01 (SRS §27.7): the golden path from a clean environment with an empty model registry.

Dataset upload → ingestion → validation → profiling → graph → analytics and motifs → features → training
(no compatible model) → scoring → ring analysis → READY → SHAP → case, subjects, finding → RANK intervention
scenario → evaluation run → copilot (mock Ollama; the live model is exercised by tests/integration).

The five parametrized runs each start from truncated databases and an empty graph; every deterministic
output (content, not random run IDs) is digested and must match across runs.
"""

import hashlib
import json
from typing import Any

import pytest

from tests.copilotutil import install
from tests.e2e.fixture import write_fixture
from tests.ingestutil import run_worker, upload

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

OUTPUTS: dict[int, dict[str, str]] = {}
API = "/api/v1"


def get(client: Any, actor: Any, path: str, **params: Any) -> Any:
    resp = client.get(f"{API}{path}", headers=actor.headers, params=params or None)
    assert resp.status_code == 200, f"{path}: {resp.status_code} {resp.text[:300]}"
    return resp.json()


def post(client: Any, actor: Any, path: str, status: int, body: Any) -> Any:
    resp = client.post(f"{API}{path}", headers=actor.headers, json=body)
    assert resp.status_code == status, f"{path}: {resp.status_code} {resp.text[:300]}"
    return resp.json()


def all_accounts(client: Any, actor: Any) -> list[dict[str, Any]]:
    out, page = [], 1
    while True:
        body = get(client, actor, "/accounts", page=page, page_size=100)
        out += body["items"]
        if page * body["page_size"] >= body["total"]:
            return out
        page += 1


@pytest.mark.parametrize("run", range(5))
def test_AT_E2E_01_golden_path(app, client, users, tmp_path, run) -> None:
    admin, inv, analyst = users("ADMIN"), users("INVESTIGATOR"), users("ANALYST")
    out: dict[str, Any] = {}

    # clean environment: empty model registry
    assert get(client, admin, "/models")["total"] == 0
    assert get(client, admin, "/context")["is_active"] is False

    # dataset → … → READY in one pipeline run started by the upload
    csv_path = tmp_path / "golden.csv"
    write_fixture(csv_path)
    accepted = upload(client, admin, csv_path, name="golden path")
    assert accepted.status_code == 202, accepted.text
    accepted = accepted.json()
    run_worker(app, timeout=900)
    ingestion = get(client, admin, f"/ingestion/{accepted['ingestion_run_id']}")
    assert ingestion["status"] == "SUCCEEDED"
    pipeline = get(client, admin, f"/pipeline-runs/{accepted['pipeline_run_id']}")
    assert pipeline["current_state"] == "READY", pipeline
    out["ingestion"] = {k: ingestion[k] for k in ("records_seen", "records_accepted", "records_rejected")}
    profile = get(client, admin, f"/datasets/{accepted['dataset_id']}/profile")
    assert profile["dataset_id"] == accepted["dataset_id"]

    # training ran because the registry was empty; the context is the new model
    models = get(client, admin, "/models")["items"]
    assert len(models) == 1
    ctx = get(client, admin, "/context")
    assert ctx["model_version"] == models[0]["model_version"] and ctx["dataset_id"] == accepted["dataset_id"]
    out["model"] = {
        k: models[0][k] for k in ("feature_version", "class_distribution", "evaluation_metrics", "operating_threshold")
    }

    # scoring and graph outputs
    accounts = all_accounts(client, analyst)
    assert accounts and all(a["risk_tier"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL") for a in accounts)
    out["scores"] = sorted((a["account_id"], a["risk_score"], a["risk_tier"]) for a in accounts)
    top = max(accounts, key=lambda a: (a["risk_score"], a["account_id"]))["account_id"]
    risk = get(client, analyst, f"/accounts/{top}/risk")
    out["top_risk"] = {
        k: risk[k] for k in ("final_score", "risk_tier", "ml_score", "graph_signal_score", "propagated_risk")
    }
    get(client, analyst, f"/accounts/{top}/features")
    get(client, analyst, f"/accounts/{top}/motifs")
    nb = get(client, analyst, "/graph/neighborhood", account_id=top, depth=2)
    out["neighbourhood"] = sorted(n["account_id"] for n in nb["nodes"])

    # SHAP on demand
    shap = get(client, analyst, f"/accounts/{top}/shap", assessment_id=risk["assessment_id"])
    assert shap["explains"] == "ML_COMPONENT_ONLY" and shap["contributions"]
    out["shap"] = [(c["feature_id"], round(c["shap"], 6)) for c in shap["contributions"]]

    # investigation: case, subject, finding
    case = post(client, inv, "/cases", 201, {"title": "Golden path review", "priority": "HIGH"})
    post(client, inv, f"/cases/{case['case_id']}/subjects", 201, {"subject_type": "ACCOUNT", "subject_id": top})
    finding = {
        "type": "OBSERVATION",
        "description": "Inflow is forwarded within the hour.",
        "source": "e2e",
        "evidence": [{"type": "risk_assessment", "id": risk["assessment_id"]}],
    }
    post(client, inv, f"/cases/{case['case_id']}/findings", 201, finding)
    assert get(client, inv, f"/cases/{case['case_id']}/findings")["total"] == 1

    # rings and a RANK intervention scenario on the first potential fraud ring candidate
    rings = get(client, inv, "/rings", page_size=100)["items"]
    out["rings"] = sorted((r["candidate_class"], r["member_count"], r["candidate_score"]) for r in rings)
    potential = [r for r in rings if r["candidate_class"] == "POTENTIAL_FRAUD_RING_CANDIDATE"]
    assert potential, "the injected cluster must surface as a potential fraud ring candidate"
    ring = potential[0]
    members = sorted(m["account_id"] for m in get(client, inv, f"/rings/{ring['ring_id']}/accounts")["items"])
    out["ring_members"] = members
    sim = post(client, inv, f"/rings/{ring['ring_id']}/interventions/simulate", 202, {"mode": "RANK"})
    run_worker(app, timeout=600)
    scenario = get(client, inv, f"/interventions/{sim['scenario_id']}")
    assert scenario["status"] == "COMPLETED", scenario
    cands = get(client, inv, f"/interventions/{sim['scenario_id']}/candidates", page_size=10)
    assert cands["hypothetical"] is True and cands["items"]
    out["intervention"] = [(c["rank_position"], c["target_ids"], c["intervention_score"]) for c in cands["items"]]

    # evaluation run over the model's test split
    ev = post(client, admin, "/evaluation/runs", 202, {})
    run_worker(app, timeout=600)
    summary = get(client, admin, f"/evaluation/runs/{ev['evaluation_run_id']}")
    assert summary["status"] == "COMPLETED", summary
    assert set(summary["levels"]) == {"TRANSACTION", "ACCOUNT", "RING", "NETWORK"}
    out["evaluation"] = {
        level: sorted((m["metric"], m["value"], m["state"]) for m in metrics)
        for level, metrics in summary["levels"].items()
    }

    # copilot over the same account
    mock = install(app)
    answer = post(client, analyst, "/copilot/query", 200, {"question": "Why is this account risky?", "account_id": top})
    assert answer["label"] == "AI INTERPRETATION" and answer["facts"] and len(mock.calls) == 1
    # refs to run-scoped rows carry random UUIDs (assessment:{uuid}); compare those by kind only
    stable = ("account", "feature", "transaction")
    refs = sorted(r if r.split(":", 1)[0] in stable else r.split(":", 1)[0] for r in answer["source_references"])
    out["copilot"] = {"intent": answer["intent"], "refs": refs}

    digests = {
        k: hashlib.sha256(json.dumps(v, sort_keys=True, default=str).encode()).hexdigest() for k, v in out.items()
    }
    OUTPUTS[run] = digests
    first = min(OUTPUTS)
    differing = sorted(k for k in digests if digests[k] != OUTPUTS[first][k])
    assert not differing, f"run {run} differs from run {first} in {differing}"
