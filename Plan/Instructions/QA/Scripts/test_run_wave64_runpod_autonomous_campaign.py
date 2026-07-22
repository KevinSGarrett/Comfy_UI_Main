from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_campaign.py"
SPEC = importlib.util.spec_from_file_location("campaign", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
H = "a" * 64


def contract(count: int = 4) -> dict:
    jobs = []
    dag = []
    for index in range(count):
        node = f"n{index:02d}"
        jobs.append({"node_id": node, "role_id": "W64-AQA-ROLE-IMPLEMENTER", "phase": "CPU", "contract_path": f"contracts/{node}.json"})
        dag.append({"node_id": node, "depends_on": [] if index < 2 else [f"n{index - 2:02d}"]})
    return {"campaign_id": H, "policy": {"max_attempts": 2, "repair_attempts": 1}, "jobs": jobs, "dag": dag, "model_bindings": [{"role_id": "W64-AQA-ROLE-IMPLEMENTER", "family_id": "F1", "checkpoint_sha256": "1" * 64, "qualification_state": "QUALIFIED"}]}


def passing(job: dict, attempt: int, repair: bool) -> MODULE.JobOutcome:
    return MODULE.JobOutcome("PASS", MODULE.canonical_bytes({"node": job["node_id"], "attempt": attempt, "repair": repair}))


def test_deterministic_replay_and_evidence_completeness(tmp_path: Path) -> None:
    first = MODULE.CampaignExecutor(contract(), tmp_path / "a", MODULE.MemoryLeaseAdapter()).run(passing)
    second = MODULE.CampaignExecutor(contract(), tmp_path / "b", MODULE.MemoryLeaseAdapter()).run(passing)
    assert first["disposition"] == "COMPLETE"
    assert first["metrics"]["evidence_completeness_rate"] == 1.0
    schema = json.loads((ROOT / "Plan/08_SCHEMAS/runpod_autonomous_campaign_result.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(first)
    assert [(j["node_id"], j["terminal_state"], j["evidence_sha256"]) for j in first["jobs"]] == [(j["node_id"], j["terminal_state"], j["evidence_sha256"]) for j in second["jobs"]]
    assert "Anomalies: none" in MODULE.render_summary(first)


def test_incompatible_branch_continues_and_retry_exhausts(tmp_path: Path) -> None:
    def runner(job: dict, attempt: int, repair: bool) -> MODULE.JobOutcome:
        if job["node_id"] == "n00":
            return MODULE.JobOutcome("FAIL", b"poison", "POISONED", repairable=True)
        return MODULE.JobOutcome("PASS", job["node_id"].encode())
    result = MODULE.CampaignExecutor(contract(), tmp_path, MODULE.MemoryLeaseAdapter()).run(runner)
    states = {job["node_id"]: job["terminal_state"] for job in result["jobs"]}
    assert states == {"n00": "FAIL", "n01": "PASS", "n02": "BLOCKED", "n03": "PASS"}
    assert result["disposition"] == "PARTIAL_BLOCKED"


def test_repair_and_automatic_rollback(tmp_path: Path) -> None:
    def runner(job: dict, attempt: int, repair: bool) -> MODULE.JobOutcome:
        if job["node_id"] == "n00":
            return MODULE.JobOutcome("PASS", b"repaired") if repair else MODULE.JobOutcome("FAIL", b"bad", "REPAIR", True)
        if job["node_id"] == "n01":
            return MODULE.JobOutcome("FAIL", b"oom", "OOM")
        return MODULE.JobOutcome("PASS", b"ok")
    result = MODULE.CampaignExecutor(contract(), tmp_path, MODULE.MemoryLeaseAdapter()).run(runner)
    states = {job["node_id"]: job["terminal_state"] for job in result["jobs"]}
    assert states["n00"] == "PASS"
    assert states["n01"] == "ROLLED_BACK"


def test_crash_cursor_and_journal_tamper_fork_detection(tmp_path: Path) -> None:
    executor = MODULE.CampaignExecutor(contract(2), tmp_path, MODULE.MemoryLeaseAdapter())
    executor.run(passing)
    cursor = executor.restart_cursor()
    assert cursor["in_flight_nodes_assumed_complete"] is False
    assert cursor["completed_nodes"] == ["n00", "n01"]
    tampered = copy.deepcopy(executor.events)
    tampered[1]["state"] = "BLOCKED"
    with pytest.raises(ValueError, match="hash"):
        MODULE.CampaignExecutor.verify_journal(tampered)
    forked = copy.deepcopy(executor.events)
    forked[1]["previous_hash"] = "f" * 64
    with pytest.raises(ValueError, match="fork"):
        MODULE.CampaignExecutor.verify_journal(forked)


def test_lease_loss_and_unqualified_role_abstain(tmp_path: Path) -> None:
    value = contract(2)
    value["jobs"][0]["phase"] = "GPU"
    result = MODULE.CampaignExecutor(value, tmp_path / "lease", MODULE.MemoryLeaseAdapter(lose_after_acquire=True)).run(passing)
    assert {job["node_id"]: job["terminal_state"] for job in result["jobs"]}["n00"] == "BLOCKED"
    value = contract(1)
    value["model_bindings"][0]["qualification_state"] = "UNQUALIFIED"
    result = MODULE.CampaignExecutor(value, tmp_path / "role", MODULE.MemoryLeaseAdapter()).run(passing)
    assert result["jobs"][0]["terminal_state"] == "ABSTAINED"


@pytest.mark.parametrize("reason", ["OOM", "TIMEOUT", "ROLLBACK_REQUIRED"])
def test_failure_injection_rolls_back(reason: str, tmp_path: Path) -> None:
    def fail(job: dict, attempt: int, repair: bool) -> MODULE.JobOutcome:
        return MODULE.JobOutcome("FAIL", reason.encode(), reason)
    result = MODULE.CampaignExecutor(contract(1), tmp_path / reason, MODULE.MemoryLeaseAdapter()).run(fail)
    assert result["jobs"][0]["terminal_state"] == "ROLLED_BACK"
