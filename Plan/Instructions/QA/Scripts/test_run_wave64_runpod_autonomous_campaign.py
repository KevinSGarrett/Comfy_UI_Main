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
    MODULE.CampaignExecutor.verify_result_identity(first)
    assert first["cleanup"] == {"measured": False, "complete": None, "residual_paths": [], "measurement_sha256": None}
    assert first["metrics"]["known_bad_false_accepts"] is None
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
    illegal = copy.deepcopy(executor.events)
    illegal[1]["event_type"] = "JOB_DISPATCH"
    illegal[1]["event_hash"] = MODULE.ZERO_HASH
    illegal[1]["event_hash"] = MODULE.digest(illegal[1])
    if len(illegal) > 2:
        illegal[2]["previous_hash"] = illegal[1]["event_hash"]
        illegal[2]["event_hash"] = MODULE.ZERO_HASH
        illegal[2]["event_hash"] = MODULE.digest(illegal[2])
    with pytest.raises(ValueError, match="illegal journal state transition"):
        MODULE.CampaignExecutor.verify_journal(illegal)


def test_lease_loss_and_unqualified_role_abstain(tmp_path: Path) -> None:
    value = contract(2)
    value["jobs"][0]["phase"] = "GPU"
    result = MODULE.CampaignExecutor(value, tmp_path / "lease", MODULE.MemoryLeaseAdapter(lose_after_acquire=True)).run(passing)
    assert {job["node_id"]: job["terminal_state"] for job in result["jobs"]}["n00"] == "BLOCKED"
    value = contract(1)
    value["model_bindings"][0]["qualification_state"] = "UNQUALIFIED"
    result = MODULE.CampaignExecutor(value, tmp_path / "role", MODULE.MemoryLeaseAdapter()).run(passing)
    assert result["jobs"][0]["terminal_state"] == "ABSTAINED"


def test_coordinator_adapter_fails_closed_and_never_overrides_foreign_lease() -> None:
    releases: list[tuple[str, str]] = []
    adapter = MODULE.CoordinatorLeaseAdapter(
        lambda campaign_id, node_id: {"state": "GRANTED", "lease_id": "lease-1", "foreign_override_allowed": False},
        lambda lease_id: {"state": "VALID", "campaign_id": H},
        lambda lease_id, outcome: releases.append((lease_id, outcome)),
    )
    assert adapter.acquire(H, "n00") == "lease-1"
    assert adapter.validate("lease-1") is True
    adapter.release("lease-1", "PASS")
    assert releases == [("lease-1", "PASS")]
    denied = MODULE.CoordinatorLeaseAdapter(
        lambda campaign_id, node_id: {"state": "GRANTED", "lease_id": "foreign", "foreign_override_allowed": True},
        lambda lease_id: {},
        lambda lease_id, outcome: None,
    )
    assert denied.acquire(H, "n00") is None


def test_result_identity_and_merkle_tamper_detection(tmp_path: Path) -> None:
    result = MODULE.CampaignExecutor(contract(1), tmp_path, MODULE.MemoryLeaseAdapter()).run(passing)
    tampered = copy.deepcopy(result)
    tampered["metrics"]["model_reloads"] += 1
    with pytest.raises(ValueError, match="result_id"):
        MODULE.CampaignExecutor.verify_result_identity(tampered)


def test_campaign_lease_schema_rejects_foreign_override() -> None:
    schema = json.loads((ROOT / "Plan/08_SCHEMAS/runpod_autonomous_campaign_lease.schema.json").read_text(encoding="utf-8"))
    lease = {"schema_version": "wave64.aqa.campaign_lease.v1", "campaign_id": H, "lease_id": "lease-123", "coordinator_receipt_sha256": H, "owner": "comfyui_main", "phase": "GPU", "capacity_gib": 4, "state": "GRANTED", "expires_at": "2026-07-22T23:59:00Z", "foreign_override_allowed": False}
    jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(lease)
    lease["foreign_override_allowed"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(schema).validate(lease)


def test_model_residency_batches_ready_jobs(tmp_path: Path) -> None:
    value = contract(4)
    value["model_bindings"] = [
        {"role_id": "R-A", "checkpoint_sha256": "1" * 64, "qualification_state": "QUALIFIED"},
        {"role_id": "R-B", "checkpoint_sha256": "2" * 64, "qualification_state": "QUALIFIED"},
    ]
    value["jobs"][0]["role_id"] = "R-A"
    value["jobs"][1]["role_id"] = "R-B"
    value["jobs"][2]["role_id"] = "R-A"
    value["jobs"][3]["role_id"] = "R-B"
    result = MODULE.CampaignExecutor(value, tmp_path, MODULE.MemoryLeaseAdapter()).run(passing)
    assert result["metrics"]["model_reloads"] == 2
    tampered = copy.deepcopy(result)
    tampered["evidence"][0]["sha256"] = "f" * 64
    tampered["result_id"] = MODULE.RESULT_ID_PLACEHOLDER
    tampered["result_id"] = MODULE.digest(tampered)
    with pytest.raises(ValueError, match="Merkle root"):
        MODULE.CampaignExecutor.verify_result_identity(tampered)


@pytest.mark.parametrize("reason", ["OOM", "TIMEOUT", "ROLLBACK_REQUIRED"])
def test_failure_injection_rolls_back(reason: str, tmp_path: Path) -> None:
    def fail(job: dict, attempt: int, repair: bool) -> MODULE.JobOutcome:
        return MODULE.JobOutcome("FAIL", reason.encode(), reason)
    result = MODULE.CampaignExecutor(contract(1), tmp_path / reason, MODULE.MemoryLeaseAdapter()).run(fail)
    assert result["jobs"][0]["terminal_state"] == "ROLLED_BACK"
