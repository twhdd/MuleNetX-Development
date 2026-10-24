"""Run the 16 demonstration scenarios of SRS §29 against a running MuleNetX stack, printing each step.

    make demo                                   # clean throwaway stack + this script (see Makefile)
    cd backend && uv run python ../scripts/demo.py --project mulenetx-demo [--csv paysim.csv]

Credentials come from the repository's `.env` (the bootstrap admin). Without `--csv` the script uploads the
synthetic labelled fixture (backend/tests/e2e/fixture.py), so the demo needs no external download. Scenarios
9, 10, 11 and 16 stop and start Compose services of `--project` to inject failures, and restore them.

Every scenario checks what §29 says should be observable and prints PASS or FAIL; the exit code is the number
of failed scenarios. Nothing here is mocked: scenario 8 needs a local Ollama model that answers within the
copilot timeout (OQ-85).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


class Fail(Exception):
    pass


def check(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


class Demo:
    def __init__(self, base: str, project: str, csv_path: Path | None) -> None:
        self.base = base.rstrip("/")
        self.project = project
        self.csv_path = csv_path
        self.http = httpx.Client(base_url=self.base, timeout=60)
        self.state: dict[str, Any] = {}
        self.wait_up()
        env = env_file()
        self.admin = self.login(
            env.get("MULENETX_BOOTSTRAP_ADMIN_USERNAME", "admin"), env["MULENETX_BOOTSTRAP_ADMIN_PASSWORD"]
        )

    # ── plumbing ──────────────────────────────────────────────────────────
    def wait_up(self, timeout: float = 300) -> None:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            try:
                if self.http.get("/ready").status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(2)
        raise SystemExit(f"{self.base}/ready did not answer 200 within {timeout:.0f}s")

    @staticmethod
    def step(text: str) -> None:
        print(f"    · {text}")

    def login(self, username: str, password: str) -> dict[str, str]:
        resp = self.http.post("/api/v1/auth/login", json={"username": username, "password": password})
        check(resp.status_code == 200, f"login as {username}: {resp.status_code}")
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    def call(self, method: str, path: str, expect: int = 200, who: dict[str, str] | None = None, **kw: Any) -> Any:
        resp = self.http.request(method, f"/api/v1{path}", headers=who or self.admin, **kw)
        check(
            resp.status_code == expect, f"{method} {path}: expected {expect}, got {resp.status_code} {resp.text[:200]}"
        )
        return resp.json() if resp.content else None

    def compose(self, *args: str) -> None:
        cmd = [
            "docker",
            "compose",
            "-p",
            self.project,
            "-f",
            str(ROOT / "docker-compose.yml"),
            "--project-directory",
            str(ROOT),
            *args,
        ]
        self.step("$ " + " ".join(cmd[cmd.index("-p") : cmd.index("-f")] + list(args)))
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=False)  # noqa: S603 - fixed docker argv
        check(done.returncode == 0, f"docker compose {' '.join(args)}: {done.stderr[-300:]}")

    def wait_run(self, run_id: str, timeout: float = 900) -> dict[str, Any]:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            run: dict[str, Any] = self.call("GET", f"/pipeline-runs/{run_id}")
            if run["current_state"] in ("READY", "FAILED"):
                return run
            time.sleep(3)
        raise Fail(f"pipeline run {run_id} did not finish in {timeout:.0f}s")

    def wait_job(self, path: str, timeout: float = 600) -> dict[str, Any]:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            body: dict[str, Any] = self.call("GET", path)
            if body["status"] in ("COMPLETED", "FAILED"):
                return body
            time.sleep(3)
        raise Fail(f"{path} did not finish in {timeout:.0f}s")

    def wait_ready(self, timeout: float = 300) -> dict[str, Any]:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            try:
                resp = self.http.get("/ready")
                if resp.status_code == 200 and resp.json().get("checks", {}).get("neo4j", {}).get("status") in (
                    "ok",
                    "OK",
                    "up",
                    "UP",
                    None,
                ):
                    return dict(resp.json())
            except httpx.HTTPError:
                pass
            time.sleep(3)
        raise Fail("backend not ready")

    # ── scenarios ─────────────────────────────────────────────────────────
    def s01_ingestion(self) -> None:
        check(self.call("GET", "/models")["total"] == 0, "the model registry is not empty: start from a clean stack")
        path = self.csv_path
        if path is None:
            from tests.e2e.fixture import write_fixture

            path = Path(tempfile.mkdtemp()) / "mulenetx-demo.csv"
            self.step(f"writing the synthetic fixture: {write_fixture(path)} transactions")
        with path.open("rb") as f:
            accepted = self.call(
                "POST",
                "/ingestion",
                202,
                files={"file": (path.name, f, "text/csv")},
                data={
                    "name": "demo",
                    "source": "paysim",
                    "dataset_version": f"v{int(time.time())}",
                    "schema_version": "paysim-1",
                    "adapter": "paysim-v1",
                },
            )
        self.state.update(accepted)
        self.step(f"accepted as {accepted['dataset_key']}; pipeline run {accepted['pipeline_run_id']}")
        end = time.monotonic() + 600
        while True:
            run = self.call("GET", f"/pipeline-runs/{accepted['pipeline_run_id']}")
            if run["current_state"] not in ("CREATED", "INGESTING", "INGESTED", "PROFILING") or time.monotonic() > end:
                break
            time.sleep(2)
        ing = self.call("GET", f"/ingestion/{accepted['ingestion_run_id']}")
        check(ing["status"] == "SUCCEEDED", f"ingestion {ing['status']}")
        self.step(
            f"seen {ing['records_seen']}, accepted {ing['records_accepted']}, rejected "
            f"{ing['records_rejected']}, duplicates {ing['records_duplicate']}; rejection codes "
            f"{ing['rejection_summary'].get('counts', {})}"
        )
        profile = self.call("GET", f"/datasets/{accepted['dataset_id']}/profile")
        self.step(f"profile {profile['profile_version']}: {', '.join(sorted(profile['metrics'])[:6])} …")

    def s02_pipeline(self) -> None:
        run = self.wait_run(self.state["pipeline_run_id"])
        check(run["current_state"] == "READY", f"pipeline ended {run['current_state']}: {run['safe_failure_message']}")
        models = self.call("GET", "/models")["items"]
        check(len(models) == 1, "training did not register a model")
        ctx = self.call("GET", "/context")
        check(ctx["is_active"] and ctx["model_version"] == models[0]["model_version"], "context not updated")
        self.state["run"] = run
        self.step(
            f"READY; trained {models[0]['model_version']}; active context {ctx['dataset_id'][:8]} / "
            f"snapshot {ctx['graph_snapshot_id'][:8]}"
        )

    def s03_graph(self) -> None:
        metrics = self.state["run"].get("metrics") or {}
        graph = {k: v for k, v in metrics.items() if "node" in k or "edge" in k or "digest" in k or "graph" in k}
        check(bool(self.state["run"]["graph_snapshot_id"]), "no graph snapshot")
        self.step(f"snapshot {self.state['run']['graph_snapshot_id']}: {graph or metrics}")

    def s04_account(self) -> None:
        accounts = self.call("GET", "/accounts", params={"sort": "risk_score", "order": "desc", "page_size": 5})
        top = accounts["items"][0]["account_id"]
        self.state["top"] = top
        found = self.call("GET", "/accounts", params={"q": top.split(":")[-1]})
        check(any(a["account_id"] == top for a in found["items"]), "search did not find the account")
        txs = self.call("GET", f"/accounts/{top}/transactions", params={"page_size": 5})
        risk = self.call("GET", f"/accounts/{top}/risk")
        self.state["risk"] = risk
        prop = self.call("GET", f"/accounts/{top}/risk/propagation")
        shap = self.call("GET", f"/accounts/{top}/shap", params={"assessment_id": risk["assessment_id"]})
        nb = self.call("GET", "/graph/neighborhood", params={"account_id": top, "depth": 2})
        check(shap["explains"] == "ML_COMPONENT_ONLY", "SHAP must explain the ML component only")
        self.step(f"{top}: final {risk['final_score']:.3f} {risk['risk_tier']}, coverage {risk['signal_coverage']}")
        self.step(
            f"components ml {risk['ml_score']}, graph {risk['graph_signal_score']:.3f}, behaviour "
            f"{risk['behavioral_signal_score']:.3f}, rules {risk['rule_signal_score']:.3f}, propagated "
            f"{risk['propagated_risk']:.3f} from {len(prop['contributions'])} sources"
        )
        self.step(
            f"{len(txs['items'])} transactions shown; SHAP top: "
            f"{[c['feature_id'] for c in shap['contributions'][:3]]}; neighbourhood "
            f"{len(nb['nodes'])} nodes, truncated={nb.get('truncated')}"
        )

    def s05_community_ring(self) -> None:
        communities = self.call("GET", "/communities", params={"page_size": 5})
        check(communities["total"] > 0, "no communities")
        community = self.call("GET", f"/communities/{communities['items'][0]['community_id']}")
        rings = self.call("GET", "/rings", params={"class": "POTENTIAL_FRAUD_RING_CANDIDATE"})
        check(rings["total"] > 0, "no potential fraud ring candidate")
        ring = rings["items"][0]
        self.state["ring"] = ring
        self.step(f"community {community['community_id'][:8]}: {community['member_count']} members")
        self.step(f'ring {ring["ring_id"][:8]}: score {ring["candidate_score"]:.3f}; "{ring["interpretation"]}"')
        from mulenetx.copilot.validation import deny_list

        text = ring["interpretation"].lower()
        check(not any(p in text for p in deny_list()), "criminality assertion in the ring interpretation")
        check("not proof" in text, "the interpretation must say membership is not proof")
        updated = self.call(
            "PATCH", f"/rings/{ring['ring_id']}/status", json={"status": "REVIEWED"}, who=self.investigator()
        )
        self.step(f"investigator set status {updated['candidate_status']}")

    def investigator(self) -> dict[str, str]:
        if "inv" not in self.state:
            for role in ("INVESTIGATOR", "ANALYST"):
                name, password = f"demo-{role.lower()}-{int(time.time())}", "demo-password-12345"
                self.call("POST", "/users", 201, json={"username": name, "role": role, "password": password})
                self.state[role] = self.login(name, password)
            self.state["inv"] = self.state["INVESTIGATOR"]
        inv: dict[str, str] = self.state["inv"]
        return inv

    def s06_money_flow(self) -> None:
        members = self.call("GET", f"/rings/{self.state['ring']['ring_id']}/accounts")["items"]
        ids = [m["account_id"] for m in members]
        found = None
        for src in ids:
            for dst in ids:
                if src == dst:
                    continue
                paths = self.call(
                    "GET", "/graph/path", params={"source_account_id": src, "destination_account_id": dst}
                )
                if paths["paths"]:
                    found = (src, dst, paths)
                    break
            if found:
                break
        check(found is not None, "no path between ring members")
        src, dst, paths = found  # type: ignore[misc]
        p0 = paths["paths"][0]
        self.step(
            f"{src} → {dst}: {len(paths['paths'])} path(s); first via {p0['accounts']}; statement: {paths['statement']}"
        )

    def s07_case(self) -> None:
        inv = self.investigator()
        top, risk = self.state["top"], self.state["risk"]
        case = self.call("POST", "/cases", 201, json={"title": f"Review {top}", "priority": "HIGH"}, who=inv)
        url = f"/cases/{case['case_id']}"
        self.call("POST", f"{url}/subjects", 201, json={"subject_type": "ACCOUNT", "subject_id": top}, who=inv)
        self.call(
            "POST",
            f"{url}/subjects",
            201,
            json={"subject_type": "RING", "subject_id": self.state["ring"]["ring_id"]},
            who=inv,
        )
        self.call(
            "POST",
            f"{url}/findings",
            201,
            who=inv,
            json={
                "type": "OBSERVATION",
                "description": "Inflow is forwarded within the hour.",
                "source": "demo",
                "evidence": [{"type": "risk_assessment", "id": risk["assessment_id"]}],
            },
        )
        case = self.call("PATCH", url, json={"version": case["version"], "status": "IN_REVIEW"}, who=inv)
        self.step(f"case {case['case_id'][:8]}: 2 subjects, 1 finding, now {case['status']}")
        analyst = self.state["ANALYST"]
        refused = self.http.patch(
            f"/api/v1{url}", headers=analyst, json={"version": case["version"], "status": "RESOLVED"}
        )
        check(refused.status_code == 403, f"analyst resolve: {refused.status_code}")
        self.step("analyst's RESOLVED transition refused with 403 (audited)")
        self.state["case"] = case

    def s08_copilot(self) -> None:
        self.compose("up", "-d", "ollama")
        time.sleep(5)  # let the Ollama server start listening
        resp = self.http.post(
            "/api/v1/copilot/query",
            headers=self.admin,
            timeout=120,
            json={"question": "Why is this account risky?", "account_id": self.state["top"]},
        )
        body = resp.json()
        if resp.status_code != 200:
            raise Fail(
                f"copilot {resp.status_code} {body['error']['code']} {body['error'].get('details')}: the local "
                "model must be pulled (`docker compose up ollama-pull`) and answer within the copilot timeout"
            )
        self.step(f"{body['label']}: {len(body['facts'])} facts citing {body['source_references'][:3]}")

    def s09_ollama_down(self) -> None:
        self.compose("stop", "ollama")
        resp = self.http.post(
            "/api/v1/copilot/query",
            headers=self.admin,
            json={"question": "Summarise this account", "account_id": self.state["top"]},
        )
        check(
            resp.status_code == 503 and resp.json()["error"]["code"] == "COPILOT_UNAVAILABLE",
            f"copilot with Ollama stopped: {resp.status_code}",
        )
        self.call("GET", f"/accounts/{self.state['top']}/risk")
        self.call("GET", f"/cases/{self.state['case']['case_id']}")
        self.step("503 COPILOT_UNAVAILABLE; account risk and the case still load")

    def s10_neo4j_down(self) -> None:
        self.compose("stop", "neo4j")
        try:
            ready = self.http.get("/ready")
            check(ready.status_code == 200, f"/ready {ready.status_code}")
            self.call("GET", f"/accounts/{self.state['top']}/risk")
            self.call("GET", f"/accounts/{self.state['top']}/transactions")
            nb = self.http.get(
                "/api/v1/graph/neighborhood", headers=self.admin, params={"account_id": self.state["top"]}
            )
            check(
                nb.status_code == 503 and nb.json()["error"]["code"] == "GRAPH_UNAVAILABLE",
                f"neighbourhood with Neo4j stopped: {nb.status_code}",
            )
            self.step(f"/ready 200 {ready.json()}; risk and transactions load; neighbourhood 503 GRAPH_UNAVAILABLE")
        finally:
            self.compose("start", "neo4j")
            self.wait_graph()

    def wait_graph(self) -> None:
        end = time.monotonic() + 300
        while time.monotonic() < end:
            resp = self.http.get(
                "/api/v1/graph/neighborhood", headers=self.admin, params={"account_id": self.state["top"]}
            )
            if resp.status_code == 200:
                return
            time.sleep(3)
        raise Fail("Neo4j did not come back")

    def s11_ml_down(self) -> None:
        model = self.call("GET", "/models")["items"][0]
        ref = model["artifact_reference"]
        before = self.call("GET", f"/accounts/{self.state['top']}/risk")
        self.compose("exec", "-T", "worker", "mv", ref, ref + ".hidden")
        try:
            run = self.call("POST", "/pipeline-runs", 202, json={"dataset_id": self.state["dataset_id"]})
            done = self.wait_run(run["pipeline_run_id"])
            check(done["current_state"] == "READY", f"rescoring ended {done['current_state']}")
        finally:
            self.compose("exec", "-T", "worker", "mv", ref + ".hidden", ref)
        now = self.call("GET", f"/accounts/{self.state['top']}/risk")
        check(
            now["ml_score"] is None and now["signal_availability"]["ml"]["state"] == "UNAVAILABLE",
            "ML should be unavailable",
        )
        self.step(
            f"artifact hidden; new scoring run: ml_score None ({now['signal_availability']['ml']}); "
            f"coverage {now['signal_coverage']}; earlier ML score {before['ml_score']} not substituted"
        )
        self.state["ml_hidden_run"] = done

    def s12_ring_intelligence(self) -> None:
        # rescore with the model restored so the ring analysis below has every signal
        run = self.call("POST", "/pipeline-runs", 202, json={"dataset_id": self.state["dataset_id"]})
        check(self.wait_run(run["pipeline_run_id"])["current_state"] == "READY", "rescoring failed")
        rings = self.call("GET", "/rings", params={"class": "POTENTIAL_FRAUD_RING_CANDIDATE"})["items"]
        ring = rings[0]
        self.state["ring"] = ring
        r = f"/rings/{ring['ring_id']}"
        features = self.call("GET", f"{r}/features")
        risk = self.call("GET", f"{r}/risk")
        evidence = self.call("GET", f"{r}/evidence", params={"section": "paths"})
        txs = self.call("GET", f"{r}/transactions")
        motifs = self.call("GET", f"{r}/motifs")
        self.step(
            f"ring {ring['ring_id'][:8]}: risk {risk.get('ring_risk_score')} {risk.get('ring_risk_tier')}; "
            f"features {[f['name'] for f in features['features']][:9]}; paths truncated={features['paths_truncated']}"
        )
        self.step(
            f"evidence paths {evidence.get('total', '?')}, transactions {txs.get('total', len(txs['items']))},"
            f" motifs {motifs['total']}"
        )

    def s13_motifs(self) -> None:
        motifs = self.call("GET", "/rings/" + self.state["ring"]["ring_id"] + "/motifs")["items"]
        check(bool(motifs), "no motifs in the ring's context")
        m = motifs[0]
        self.step(
            f"{m['motif_type']} anchored at {m['anchor_account_id']}: confidence {m['motif_confidence']:.3f} "
            f"{m['confidence_components']}, order_ambiguous={m['order_ambiguous']}, "
            f"{m['transaction_count']} transactions"
        )

    def s14_intervention(self) -> None:
        inv = self.investigator()
        r = f"/rings/{self.state['ring']['ring_id']}"
        totals = (self.call("GET", "/accounts")["total"], self.call("GET", "/cases")["total"])
        rank = self.call("POST", f"{r}/interventions/simulate", 202, json={"mode": "RANK"}, who=inv)
        done = self.wait_job(f"/interventions/{rank['scenario_id']}")
        check(done["status"] == "COMPLETED", f"RANK {done['status']}: {done['error_summary']}")
        cands = self.call("GET", f"/interventions/{rank['scenario_id']}/candidates", params={"page_size": 3})
        top = cands["items"][0]
        self.step(
            f"RANK (hypothetical={cands['hypothetical']}): top {top['operation_type']} {top['target_ids']} "
            f"score {top['intervention_score']:.3f}, flow disruption {top['flow_disruption_percentage']}%"
        )
        ev = self.call(
            "POST",
            f"{r}/interventions/simulate",
            202,
            who=inv,
            json={"mode": "EVALUATE", "intervention_type": top["operation_type"], "target_ids": top["target_ids"]},
        )
        done = self.wait_job(f"/interventions/{ev['scenario_id']}")
        check(done["status"] == "COMPLETED", f"EVALUATE {done['status']}: {done['error_summary']}")
        check(
            (self.call("GET", "/accounts")["total"], self.call("GET", "/cases")["total"]) == totals,
            "canonical state changed",
        )
        self.step(
            f"EVALUATE of the investigator-chosen set completed; statement: {done['statement']}; "
            "account and case counts unchanged"
        )

    def s15_evaluation(self) -> None:
        ev = self.call("POST", "/evaluation/runs", 202, json={})
        done = self.wait_job(f"/evaluation/runs/{ev['evaluation_run_id']}")
        check(done["status"] == "COMPLETED", f"evaluation {done['status']}: {done['failure']}")
        for level in ("TRANSACTION", "ACCOUNT", "RING", "NETWORK"):
            check(level in done["levels"], f"missing level {level}")
            shown = [
                (m["metric"], m["value"] if m["value"] is None else round(m["value"], 3))
                for m in done["levels"][level][:3]
            ]
            self.step(f"{level}: {shown}")
        self.step(f"limitation: {done['limitation'][:140]}…")

    def s16_worker_recovery(self) -> None:
        run = self.call("POST", "/pipeline-runs", 202, json={"dataset_id": self.state["dataset_id"]})
        end = time.monotonic() + 300
        while time.monotonic() < end:
            state = self.call("GET", f"/pipeline-runs/{run['pipeline_run_id']}")["current_state"]
            if state not in ("CREATED", "READY", "FAILED"):
                break
            time.sleep(0.5)
        self.step(f"run in {state}; killing the worker")
        self.compose("kill", "worker")
        time.sleep(5)
        self.compose("start", "worker")
        done = self.wait_run(run["pipeline_run_id"], timeout=1200)
        check(done["current_state"] == "READY", f"run ended {done['current_state']}")
        self.step("worker restarted; the expired lease was reclaimed and the run resumed to READY")


SCENARIOS: list[tuple[str, str]] = [
    ("1", "s01_ingestion"),
    ("2", "s02_pipeline"),
    ("3", "s03_graph"),
    ("4", "s04_account"),
    ("5", "s05_community_ring"),
    ("6", "s06_money_flow"),
    ("7", "s07_case"),
    ("8", "s08_copilot"),
    ("9", "s09_ollama_down"),
    ("10", "s10_neo4j_down"),
    ("11", "s11_ml_down"),
    ("12", "s12_ring_intelligence"),
    ("13", "s13_motifs"),
    ("14", "s14_intervention"),
    ("15", "s15_evaluation"),
    ("16", "s16_worker_recovery"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--project", default="mulenetx-demo", help="Compose project name of the running stack")
    parser.add_argument("--csv", type=Path, help="a PaySim CSV to use instead of the synthetic fixture")
    args = parser.parse_args()
    demo = Demo(args.base_url, args.project, args.csv)
    results: list[tuple[str, str, str]] = []
    for number, name in SCENARIOS:
        method: Callable[[], None] = getattr(demo, name)
        title = (method.__name__.split("_", 1)[1]).replace("_", " ")
        print(f"\n[{number:>2}] {title}")
        try:
            method()
            results.append((number, title, "PASS"))
        except Fail as exc:
            print(f"    ✗ {exc}")
            results.append((number, title, f"FAIL: {exc}"))
        except Exception as exc:  # report and continue with the next scenario
            traceback.print_exc(limit=2)
            results.append((number, title, f"FAIL: {type(exc).__name__}: {exc}"))
    print("\nSummary")
    for number, title, outcome in results:
        print(f"  {number:>2}. {title:<22} {outcome}")
    return sum(1 for *_, outcome in results if outcome != "PASS")


if __name__ == "__main__":
    sys.exit(main())
