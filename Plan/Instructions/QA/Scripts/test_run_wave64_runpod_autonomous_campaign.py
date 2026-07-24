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


def test_crash_restart_replays_without_assuming_in_flight_success(tmp_path: Path) -> None:
    executor = MODULE.CampaignExecutor(
        contract(2), tmp_path / "execution", MODULE.MemoryLeaseAdapter()
    )

    def crash(job: dict, attempt: int, repair: bool) -> MODULE.JobOutcome:
        raise RuntimeError("injected process crash")

    with pytest.raises(RuntimeError, match="injected process crash"):
        executor.run(crash)
    assert executor.events[-1]["event_type"] == "JOB_DISPATCH"
    restored = MODULE.CampaignExecutor.restore(
        contract(2),
        tmp_path / "execution",
        MODULE.MemoryLeaseAdapter(),
        executor.events,
        executor.results,
    )
    assert restored.events[-1]["event_type"] == "RESTART_REPLAY"
    result = restored.run(passing)
    assert result["disposition"] == "COMPLETE"
    assert {job["node_id"] for job in result["jobs"]} == {"n00", "n01"}
    assert restored.restart_cursor()["in_flight_nodes_assumed_complete"] is False


def test_lease_loss_and_unqualified_role_abstain(tmp_path: Path) -> None:
    value = contract(2)
    value["jobs"][0]["phase"] = "GPU"
    result = MODULE.CampaignExecutor(value, tmp_path / "lease", MODULE.MemoryLeaseAdapter(lose_after_acquire=True)).run(passing)
    assert {job["node_id"]: job["terminal_state"] for job in result["jobs"]}["n00"] == "DEFERRED"
    assert result["disposition"] == "PARTIAL_DEFERRED"
    assert result["deferred_work_queue"]["jobs"] == [{"node_id": "n00", "phase": "GPU", "job_sha256": MODULE.digest(value["jobs"][0]), "reason": "GPU_ADMISSION_DEFERRED"}]
    queue_path = tmp_path / "lease" / result["deferred_work_queue"]["relative_path"]
    assert queue_path.is_file()
    assert MODULE.digest(queue_path.read_bytes()) == result["deferred_work_queue"]["content_sha256"]
    value = contract(1)
    value["model_bindings"][0]["qualification_state"] = "UNQUALIFIED"
    result = MODULE.CampaignExecutor(value, tmp_path / "role", MODULE.MemoryLeaseAdapter()).run(passing)
    assert result["jobs"][0]["terminal_state"] == "ABSTAINED"


def test_deferred_gpu_job_preserves_cpu_progress_and_resumes_after_fresh_admission(
    tmp_path: Path,
) -> None:
    value = contract(2)
    value["jobs"][0]["phase"] = "GPU"
    first_executor = MODULE.CampaignExecutor(
        value, tmp_path / "execution", MODULE.MemoryLeaseAdapter(grant=False)
    )
    first = first_executor.run(passing)
    assert {job["node_id"]: job["terminal_state"] for job in first["jobs"]} == {
        "n00": "DEFERRED",
        "n01": "PASS",
    }
    assert first["metrics"]["deferred_job_count"] == 1
    assert first_executor.events[-1]["event_type"] == "CAMPAIGN_DEFERRED"
    MODULE.CampaignExecutor.verify_result_identity(first)

    restored = MODULE.CampaignExecutor.restore(
        value,
        tmp_path / "execution",
        MODULE.MemoryLeaseAdapter(),
        first_executor.events,
        first_executor.results,
    )
    assert set(restored.results) == {"n01"}
    resumed = restored.run(passing)
    assert resumed["disposition"] == "COMPLETE"
    assert resumed["deferred_work_queue"] is None
    assert resumed["metrics"]["deferred_job_count"] == 0
    assert {job["node_id"]: job["terminal_state"] for job in resumed["jobs"]} == {
        "n00": "PASS",
        "n01": "PASS",
    }


def test_gpu_deferment_cascades_only_to_dependent_work(tmp_path: Path) -> None:
    value = contract(3)
    value["jobs"][0]["phase"] = "GPU"
    result = MODULE.CampaignExecutor(
        value, tmp_path, MODULE.MemoryLeaseAdapter(grant=False)
    ).run(passing)
    assert {job["node_id"]: job["terminal_state"] for job in result["jobs"]} == {
        "n00": "DEFERRED",
        "n01": "PASS",
        "n02": "DEFERRED",
    }
    assert result["deferred_work_queue"]["jobs"] == [
        {
            "node_id": "n00",
            "phase": "GPU",
            "job_sha256": MODULE.digest(value["jobs"][0]),
            "reason": "GPU_ADMISSION_DEFERRED",
        },
        {
            "node_id": "n02",
            "phase": "CPU",
            "job_sha256": MODULE.digest(value["jobs"][2]),
            "reason": "UPSTREAM_GPU_ADMISSION_DEFERRED",
        },
    ]


def test_static_shadow_continues_qualified_cpu_sibling_and_blocks_dependents(
    tmp_path: Path,
) -> None:
    value = {
        "campaign_id": H,
        "qualification_mode": "STATIC_SHADOW",
        "admission_disposition": "BLOCKED_UNQUALIFIED",
        "policy": {"max_attempts": 2, "repair_attempts": 1},
        "jobs": [
            {
                "node_id": "unqualified",
                "role_id": "W64-AQA-ROLE-IMPLEMENTER",
                "phase": "CPU",
                "contract_path": "contracts/unqualified.json",
            },
            {
                "node_id": "qualified-sibling",
                "role_id": "W64-AQA-ROLE-REVIEWER",
                "phase": "CPU",
                "contract_path": "contracts/qualified-sibling.json",
            },
            {
                "node_id": "dependent",
                "role_id": "W64-AQA-ROLE-REVIEWER",
                "phase": "CPU",
                "contract_path": "contracts/dependent.json",
            },
        ],
        "dag": [
            {"node_id": "unqualified", "depends_on": []},
            {"node_id": "qualified-sibling", "depends_on": []},
            {"node_id": "dependent", "depends_on": ["unqualified"]},
        ],
        "model_bindings": [
            {
                "role_id": "W64-AQA-ROLE-IMPLEMENTER",
                "family_id": "F1",
                "qualification_state": "UNQUALIFIED",
            },
            {
                "role_id": "W64-AQA-ROLE-REVIEWER",
                "family_id": "F2",
                "checkpoint_sha256": "2" * 64,
                "qualification_state": "QUALIFIED",
            },
        ],
    }
    executor = MODULE.CampaignExecutor(
        value, tmp_path, MODULE.MemoryLeaseAdapter()
    )
    result = executor.run(passing)
    states = {job["node_id"]: job["terminal_state"] for job in result["jobs"]}
    assert states == {
        "dependent": "BLOCKED",
        "qualified-sibling": "PASS",
        "unqualified": "ABSTAINED",
    }
    assert result["disposition"] == "PARTIAL_BLOCKED"
    assert all(
        event["event_type"] != "GPU_LEASE_WAIT" for event in executor.events
    )


def test_static_shadow_blocked_admission_never_acquires_gpu_lease(
    tmp_path: Path,
) -> None:
    value = contract(1)
    value["qualification_mode"] = "STATIC_SHADOW"
    value["admission_disposition"] = "BLOCKED_UNQUALIFIED"
    value["jobs"][0]["phase"] = "GPU"
    lease = MODULE.MemoryLeaseAdapter()
    executor = MODULE.CampaignExecutor(value, tmp_path, lease)
    result = executor.run(passing)
    assert result["jobs"][0]["terminal_state"] == "BLOCKED"
    assert result["jobs"][0]["reason"] == "GPU_ADMISSION_BLOCKED_UNQUALIFIED"
    assert result["jobs"][0]["attempts"] == 0
    assert lease.releases == []
    assert all(event["event_type"] != "GPU_LEASE_WAIT" for event in executor.events)


def test_static_shadow_cpu_pass_cannot_promote_globally_blocked_campaign(
    tmp_path: Path,
) -> None:
    value = contract(1)
    value["qualification_mode"] = "STATIC_SHADOW"
    value["admission_disposition"] = "BLOCKED_UNQUALIFIED"
    result = MODULE.CampaignExecutor(
        value, tmp_path, MODULE.MemoryLeaseAdapter()
    ).run(passing)
    assert result["jobs"][0]["terminal_state"] == "PASS"
    assert result["disposition"] == "PARTIAL_BLOCKED"
    assert result["authority"]["self_promoted"] is False


def test_non_shadow_blocked_admission_still_abstains_every_job(
    tmp_path: Path,
) -> None:
    value = contract(2)
    value["qualification_mode"] = "RUNTIME_QUALIFICATION"
    value["admission_disposition"] = "BLOCKED_UNQUALIFIED"
    calls: list[str] = []

    def runner(job: dict, attempt: int, repair: bool) -> MODULE.JobOutcome:
        calls.append(job["node_id"])
        return passing(job, attempt, repair)

    result = MODULE.CampaignExecutor(
        value, tmp_path, MODULE.MemoryLeaseAdapter()
    ).run(runner)
    assert calls == []
    assert {job["terminal_state"] for job in result["jobs"]} == {"ABSTAINED"}
    assert {
        job["reason"] for job in result["jobs"]
    } == {"BLOCKED_UNQUALIFIED"}


def test_static_shadow_blocked_partition_replays_deterministically(
    tmp_path: Path,
) -> None:
    value = contract(2)
    value["qualification_mode"] = "STATIC_SHADOW"
    value["admission_disposition"] = "BLOCKED_UNQUALIFIED"
    value["model_bindings"][0]["qualification_state"] = "UNQUALIFIED"
    value["model_bindings"][0].pop("checkpoint_sha256")
    first = MODULE.CampaignExecutor(
        value, tmp_path / "first", MODULE.MemoryLeaseAdapter()
    ).run(passing)
    second = MODULE.CampaignExecutor(
        value, tmp_path / "second", MODULE.MemoryLeaseAdapter()
    ).run(passing)
    assert [
        (job["node_id"], job["terminal_state"], job["evidence_sha256"])
        for job in first["jobs"]
    ] == [
        (job["node_id"], job["terminal_state"], job["evidence_sha256"])
        for job in second["jobs"]
    ]


def test_coordinator_adapter_fails_closed_and_never_overrides_foreign_lease() -> None:
    releases: list[tuple[str, str]] = []
    adapter = MODULE.CoordinatorLeaseAdapter(
        lambda campaign_id, node_id: {"state": "GRANTED", "lease_id": "lease-1", "foreign_override_allowed": False},
        lambda lease_id: {"state": "VALID", "campaign_id": H},
        lambda lease_id, outcome: releases.append((lease_id, outcome)),
        lambda receipt: True,
    )
    assert adapter.acquire(H, "n00") == "lease-1"
    assert adapter.validate("lease-1") is True
    adapter.release("lease-1", "PASS")
    assert releases == [("lease-1", "PASS")]
    denied = MODULE.CoordinatorLeaseAdapter(
        lambda campaign_id, node_id: {"state": "GRANTED", "lease_id": "foreign", "foreign_override_allowed": True},
        lambda lease_id: {},
        lambda lease_id, outcome: None,
        lambda receipt: True,
    )
    assert denied.acquire(H, "n00") is None


def test_coordinator_adapter_cancels_queued_request_before_returning() -> None:
    canceled: list[str] = []
    adapter = MODULE.CoordinatorLeaseAdapter(
        lambda campaign_id, node_id: {"state": "QUEUED", "lease_id": "queued-1"},
        lambda lease_id: {},
        lambda lease_id, outcome: None,
        lambda receipt: canceled.append(receipt["lease_id"]) is None or True,
    )
    assert adapter.acquire(H, "n00") is None
    assert canceled == ["queued-1"]


def test_coordinator_adapter_fails_closed_when_queue_cancel_fails() -> None:
    adapter = MODULE.CoordinatorLeaseAdapter(
        lambda campaign_id, node_id: {"state": "QUEUED", "lease_id": "queued-1"},
        lambda lease_id: {},
        lambda lease_id, outcome: None,
        lambda receipt: False,
    )
    with pytest.raises(RuntimeError, match="queued coordinator request was not canceled"):
        adapter.acquire(H, "n00")


def test_direct_runpod_adapter_requires_clean_exact_probe_and_single_claim() -> None:
    snapshot = {
        "pod_id": "a6000-direct",
        "queue_idle": True,
        "foreign_process_conflict": False,
        "free_mib": 24000,
    }
    adapter = MODULE.DirectRunPodLeaseAdapter(
        lambda: snapshot,
        expected_pod_id="a6000-direct",
        minimum_free_mib=22000,
    )
    lease_id = adapter.acquire(H, "n00")
    assert lease_id is not None
    assert adapter.acquire(H, "n01") is None
    assert adapter.validate(lease_id) is True
    snapshot["free_mib"] = 100
    assert adapter.validate(lease_id) is False
    adapter.release(lease_id, "PASS")
    assert adapter.releases == [(lease_id, "PASS")]
    snapshot["free_mib"] = 24000
    replacement = adapter.acquire(H, "n00")
    assert replacement is not None and replacement != lease_id


@pytest.mark.parametrize(
    "field,value",
    [
        ("pod_id", "different-pod"),
        ("queue_idle", False),
        ("foreign_process_conflict", True),
        ("free_mib", 21999),
    ],
)
def test_direct_runpod_adapter_fails_closed_on_any_probe_mismatch(field: str, value: object) -> None:
    snapshot: dict[str, object] = {
        "pod_id": "a6000-direct",
        "queue_idle": True,
        "foreign_process_conflict": False,
        "free_mib": 22000,
    }
    snapshot[field] = value
    adapter = MODULE.DirectRunPodLeaseAdapter(
        lambda: snapshot,
        expected_pod_id="a6000-direct",
        minimum_free_mib=22000,
    )
    assert adapter.acquire(H, "n00") is None


def test_direct_runpod_adapter_fails_closed_on_malformed_or_failed_probe() -> None:
    def probe_error() -> dict[str, object]:
        raise RuntimeError("probe transport failed")

    for probe in (lambda: {}, lambda: None, probe_error):
        adapter = MODULE.DirectRunPodLeaseAdapter(
            probe,
            expected_pod_id="a6000-direct",
            minimum_free_mib=0,
        )
        assert adapter.acquire(H, "n00") is None
    bool_free_mib = MODULE.DirectRunPodLeaseAdapter(
        lambda: {
            "pod_id": "a6000-direct",
            "queue_idle": True,
            "foreign_process_conflict": False,
            "free_mib": True,
        },
        expected_pod_id="a6000-direct",
        minimum_free_mib=0,
    )
    assert bool_free_mib.acquire(H, "n00") is None


def test_campaign_executor_uses_direct_runpod_adapter_for_gpu_job(tmp_path: Path) -> None:
    value = contract(1)
    value["jobs"][0]["phase"] = "GPU"
    snapshot = {
        "pod_id": "a6000-direct",
        "queue_idle": True,
        "foreign_process_conflict": False,
        "free_mib": 24000,
    }
    adapter = MODULE.DirectRunPodLeaseAdapter(
        lambda: snapshot,
        expected_pod_id="a6000-direct",
        minimum_free_mib=22000,
    )
    result = MODULE.CampaignExecutor(value, tmp_path, adapter).run(passing)
    assert result["disposition"] == "COMPLETE"
    assert result["jobs"][0]["terminal_state"] == "PASS"
    assert result["metrics"]["coordinator_churn"] == 1
    assert len(adapter.releases) == 1


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
