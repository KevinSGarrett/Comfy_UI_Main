from __future__ import annotations

import copy
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[4]
MISSION_SCRIPT = (
    ROOT
    / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_mission_controller.py"
)
CAMPAIGN_COMPILER = (
    ROOT
    / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_campaign_contract.py"
)
CAMPAIGN_EXECUTOR = (
    ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_campaign.py"
)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MISSION = load(MISSION_SCRIPT, "mission_controller")
COMPILER = load(CAMPAIGN_COMPILER, "campaign_compiler_for_mission")
EXECUTOR = load(CAMPAIGN_EXECUTOR, "campaign_executor_for_mission")
H = "a" * 64


def campaign_draft() -> dict:
    roles = [
        "CONTROLLER",
        "IMPLEMENTER",
        "REVIEWER",
        "INDEPENDENT-JUROR",
        "ARBITER",
        "REPAIR-PLANNER",
        "DETERMINISTIC",
        "EVIDENCE-COMPILER",
    ]
    bindings = []
    for index, role in enumerate(roles, 1):
        role_id = f"W64-AQA-ROLE-{role}"
        binding = {
            "role_id": role_id,
            "family_id": f"W64-AQA-FAMILY-F{index}",
            "residency_group": f"f{index}",
            "capacity_state": "QUALIFIED",
            "checkpoint_sha256": str(index) * 64,
            "environment_sha256": H,
            "qualification_state": "QUALIFIED",
        }
        if role in {"DETERMINISTIC", "EVIDENCE-COMPILER"}:
            binding["binding_kind"] = "CERTIFIED_COMPONENT"
            binding["certificate_id"] = str(index) * 64
        else:
            binding["binding_kind"] = "MODEL_PACKAGE"
            binding["package_id"] = role_id.replace(
                "W64-AQA-ROLE-", "W64-AQA-PKG-"
            )
        bindings.append(binding)
    return {
        "schema_version": "wave64.aqa.campaign.v2",
        "campaign_name": "mission-controller-test",
        "campaign_profile": "DEVELOPMENT_CAMPAIGN",
        "qualification_mode": "STATIC_SHADOW",
        "repository": {
            "remote": "https://example.invalid/repository.git",
            "commit_sha256": "1" * 64,
            "tree_sha256": "2" * 64,
        },
        "policy": {
            "policy_id": "W64-AQA-TOOL-POLICY-002",
            "policy_sha256": "3" * 64,
            "max_attempts": 2,
            "repair_attempts": 1,
            "abstain_on_unqualified_role": True,
        },
        "jobs": [
            {
                "node_id": "n00",
                "contract_path": "contracts/n00.json",
                "contract_sha256": "4" * 64,
                "contract_id": "5" * 64,
                "input_sha256": "6" * 64,
                "runtime_sha256": "7" * 64,
                "prompt_sha256": "8" * 64,
                "environment_sha256": "9" * 64,
                "role_id": "W64-AQA-ROLE-IMPLEMENTER",
                "phase": "CPU",
                "stage": "GENERATE_OR_IMPLEMENT",
                "modality": "CODE",
                "risk_tier": "HIGH",
                "residency_group": "cpu-test",
                "estimated_vram_gib": 0,
                "continue_unrelated_branches": True,
            }
        ],
        "dag": [{"node_id": "n00", "depends_on": []}],
        "model_bindings": bindings,
        "bulk_manifest": None,
        "authority": {
            "runpod_may_execute_isolated_batches": True,
            "runpod_may_propose_deltas": True,
            "runpod_may_push_git": False,
            "runpod_may_promote": False,
            "runpod_may_spend": False,
            "runpod_may_override_foreign_lease": False,
            "final_acceptance_authority": "CODEX",
        },
    }


def mission_draft(campaign: dict, campaign_path: Path) -> dict:
    return {
        "schema_version": "wave64.aqa.mission_envelope.v1",
        "mission_name": "durable-work-cell-test",
        "campaign": {
            "relative_path": campaign_path.name,
            "sha256": MISSION.digest(campaign_path.read_bytes()),
            "campaign_id": campaign["campaign_id"],
        },
        "execution": {
            "allowed_paths": ["Plan/07_IMPLEMENTATION/scripts"],
            "allowed_tools": ["HASH_FILE", "RUN_ALLOWLISTED_VALIDATOR"],
            "allowed_repair_operations": ["PATCH_ALLOWED_PATH"],
            "max_child_operations": 100,
            "max_wall_seconds": 3600,
            "max_gpu_seconds": 0,
            "max_storage_growth_bytes": 1048576,
            "checkpoint_interval_seconds": 60,
            "reporting_interval_seconds": 600,
            "terminal_states": ["COMPLETE", "PARTIAL_BLOCKED", "FAILED"],
            "escalation_conditions": [
                "AUTHORITY_CHANGE",
                "FROZEN_POLICY_MISMATCH",
                "FINAL_SEALED_ACCEPTANCE",
            ],
            "gpu_lease_profile": None,
        },
        "authority": {
            "may_push_git": False,
            "may_grant_product_authority": False,
            "may_weaken_thresholds": False,
            "may_spend_money": False,
            "may_read_credentials": False,
            "may_perform_destructive_actions": False,
            "may_override_foreign_lease": False,
            "may_self_promote": False,
            "final_acceptance_authority": "CODEX",
        },
    }


def fixture(tmp_path: Path) -> tuple[dict, dict, MISSION.MissionQueue]:
    campaign = COMPILER.compile_contract(campaign_draft())
    campaign_path = tmp_path / "campaign.json"
    campaign_path.write_text(
        json.dumps(campaign, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    mission = MISSION.compile_mission(mission_draft(campaign, campaign_path), tmp_path)
    return campaign, mission, MISSION.MissionQueue(tmp_path / "queue")


def test_compile_admit_and_idempotent_replay(tmp_path: Path) -> None:
    _, mission, queue = fixture(tmp_path)
    first = queue.admit(mission, tmp_path, at="2026-07-23T00:00:00Z")
    second = queue.admit(mission, tmp_path, at="2026-07-23T00:00:01Z")
    assert first == second
    assert first["state"] == "QUEUED"
    assert first["event_count"] == 1
    assert queue.verify(mission["mission_id"]) == first


def test_mission_identity_and_path_escape_fail_closed(tmp_path: Path) -> None:
    _, mission, _ = fixture(tmp_path)
    tampered = copy.deepcopy(mission)
    tampered["execution"]["max_child_operations"] += 1
    with pytest.raises(MISSION.MissionError, match="mission_id"):
        MISSION.verify_mission(tampered, tmp_path)
    draft = copy.deepcopy(mission)
    draft.pop("mission_id")
    draft["execution"]["allowed_paths"] = ["../escape"]
    with pytest.raises(MISSION.MissionError, match="schema violation|escapes"):
        MISSION.compile_mission(draft, tmp_path)


def test_claim_heartbeat_checkpoint_and_no_time_based_reclaim(tmp_path: Path) -> None:
    _, mission, queue = fixture(tmp_path)
    mission_id = mission["mission_id"]
    queue.admit(mission, tmp_path, at="2026-07-23T00:00:00Z")
    claimed = queue.claim(mission_id, "worker-a", at="2026-07-23T00:01:00Z")
    replayed = queue.claim(mission_id, "worker-a", at="2026-07-23T00:01:01Z")
    assert replayed == claimed
    with pytest.raises(MISSION.MissionError, match="not claimable"):
        queue.claim(mission_id, "worker-b", at="2026-07-23T00:01:02Z")
    queue.heartbeat(mission_id, "worker-a", at="2026-07-23T00:02:00Z")
    checkpoint = queue.checkpoint(
        mission_id,
        "worker-a",
        {"completed_nodes": [], "in_flight_nodes_assumed_complete": False},
        at="2026-07-23T00:03:00Z",
    )
    assert checkpoint["checkpoint_sha256"]
    retained = queue.recover_stale(
        mission_id,
        stale_before="2026-07-23T00:03:01Z",
        at="2026-07-23T00:05:00Z",
    )
    assert retained["state"] == "RUNNING"
    assert retained["worker_id"] == "worker-a"
    with pytest.raises(MISSION.MissionError, match="not claimable"):
        queue.claim(mission_id, "worker-b", at="2026-07-23T00:06:00Z")
    queue.verify(mission_id)


def test_owner_confirmed_crash_requeues_checkpoint_without_assumed_success(
    tmp_path: Path,
) -> None:
    _, mission, queue = fixture(tmp_path)
    mission_id = mission["mission_id"]
    queue.admit(mission, tmp_path, at="2026-07-23T00:00:00Z")
    queue.claim(mission_id, "worker-a", at="2026-07-23T00:01:00Z")
    queue.checkpoint(
        mission_id,
        "worker-a",
        {"completed_nodes": [], "in_flight_nodes_assumed_complete": False},
        at="2026-07-23T00:02:00Z",
    )
    recovered = queue.recover_confirmed_crash(
        mission_id,
        "worker-a",
        at="2026-07-23T00:03:00Z",
    )
    assert recovered["state"] == "QUEUED"
    assert recovered["worker_id"] is None
    event = queue.journal(mission_id)[-1]
    assert event["event_type"] == "MISSION_RECOVERED"
    assert event["payload"]["recovery_reason"] == "OWNER_CONFIRMED_CRASH"
    assert event["payload"]["in_flight_assumed_complete"] is False
    queue.claim(mission_id, "worker-b", at="2026-07-23T00:04:00Z")
    queue.verify(mission_id)


def test_owner_defers_to_durable_queue_without_assumed_success(tmp_path: Path) -> None:
    _, mission, queue = fixture(tmp_path)
    mission_id = mission["mission_id"]
    queue.admit(mission, tmp_path, at="2026-07-23T00:00:00Z")
    queue.claim(mission_id, "worker-a", at="2026-07-23T00:01:00Z")
    deferred = queue.defer(
        mission_id,
        "worker-a",
        {"next_phase": "GPU", "completed_nodes": []},
        reason="GPU_ADMISSION_DEFERRED",
        at="2026-07-23T00:02:00Z",
    )
    assert deferred["state"] == "QUEUED"
    assert deferred["worker_id"] is None
    assert deferred["checkpoint_sha256"]
    event = queue.journal(mission_id)[-1]
    assert event["event_type"] == "MISSION_DEFERRED"
    assert event["payload"]["reason"] == "GPU_ADMISSION_DEFERRED"
    assert event["payload"]["in_flight_nodes_assumed_complete"] is False
    checkpoint = json.loads(
        (queue.root / event["payload"]["relative_path"]).read_text(encoding="utf-8")
    )
    assert checkpoint["next_phase"] == "GPU"
    assert checkpoint["in_flight_nodes_assumed_complete"] is False
    replacement = queue.claim(mission_id, "worker-b", at="2026-07-23T00:03:00Z")
    assert replacement["state"] == "RUNNING"
    assert replacement["worker_id"] == "worker-b"
    queue.verify(mission_id)


def test_cli_defer_requeues_owned_mission(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, mission, queue = fixture(tmp_path)
    mission_id = mission["mission_id"]
    queue.admit(mission, tmp_path, at="2026-07-23T00:00:00Z")
    queue.claim(mission_id, "worker-a", at="2026-07-23T00:01:00Z")
    checkpoint_path = tmp_path / "deferred-checkpoint.json"
    checkpoint_path.write_text(
        json.dumps({"next_phase": "GPU"}), encoding="utf-8"
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(MISSION_SCRIPT),
            "--queue-root",
            str(queue.root),
            "defer",
            mission_id,
            str(checkpoint_path),
            "--reason",
            "GPU_ADMISSION_DEFERRED",
            "--worker-id",
            "worker-a",
            "--at",
            "2026-07-23T00:02:00Z",
        ],
    )
    assert MISSION.main() == 0
    assert queue.status(mission_id)["state"] == "QUEUED"
    assert queue.journal(mission_id)[-1]["event_type"] == "MISSION_DEFERRED"


def test_confirmed_crash_rejects_wrong_owner_and_missing_checkpoint(
    tmp_path: Path,
) -> None:
    _, mission, queue = fixture(tmp_path)
    mission_id = mission["mission_id"]
    queue.admit(mission, tmp_path, at="2026-07-23T00:00:00Z")
    queue.claim(mission_id, "worker-a", at="2026-07-23T00:01:00Z")
    with pytest.raises(MISSION.MissionError, match="ownership mismatch"):
        queue.recover_confirmed_crash(
            mission_id,
            "worker-b",
            at="2026-07-23T00:02:00Z",
        )
    with pytest.raises(MISSION.MissionError, match="durable checkpoint"):
        queue.recover_confirmed_crash(
            mission_id,
            "worker-a",
            at="2026-07-23T00:03:00Z",
        )
    assert queue.status(mission_id)["state"] == "RUNNING"
    assert not (queue.root / "cas").exists()


def test_journal_is_append_only_and_tamper_is_detected(tmp_path: Path) -> None:
    _, mission, queue = fixture(tmp_path)
    mission_id = mission["mission_id"]
    queue.admit(mission, tmp_path, at="2026-07-23T00:00:00Z")
    with sqlite3.connect(queue.database) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="MISSION_JOURNAL_APPEND_ONLY"):
            connection.execute(
                "UPDATE mission_events SET event_hash=? WHERE mission_id=? AND sequence=0",
                ("f" * 64, mission_id),
            )
        with pytest.raises(sqlite3.IntegrityError, match="MISSION_JOURNAL_APPEND_ONLY"):
            connection.execute(
                "DELETE FROM mission_events WHERE mission_id=? AND sequence=0",
                (mission_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="MISSION_IDENTITY_IMMUTABLE"):
            connection.execute(
                "UPDATE missions SET campaign_json=? WHERE mission_id=?",
                (b"{}", mission_id),
            )
        with pytest.raises(
            sqlite3.IntegrityError, match="MISSION_RECORD_RETENTION_REQUIRED"
        ):
            connection.execute("DELETE FROM missions WHERE mission_id=?", (mission_id,))
        connection.execute("DROP TRIGGER mission_events_no_update")
        connection.execute(
            "UPDATE mission_events SET event_hash=? WHERE mission_id=? AND sequence=0",
            ("f" * 64, mission_id),
        )
    with pytest.raises(MISSION.MissionError, match="hash or sequence"):
        queue.verify(mission_id)


def test_terminal_result_is_identity_checked_and_stored_in_cas(tmp_path: Path) -> None:
    campaign, mission, queue = fixture(tmp_path)
    mission_id = mission["mission_id"]
    queue.admit(mission, tmp_path, at="2026-07-23T00:00:00Z")
    queue.claim(mission_id, "worker-a", at="2026-07-23T00:01:00Z")

    def passing(job: dict, attempt: int, repair: bool) -> EXECUTOR.JobOutcome:
        return EXECUTOR.JobOutcome(
            "PASS",
            EXECUTOR.canonical_bytes(
                {"node": job["node_id"], "attempt": attempt, "repair": repair}
            ),
        )

    result = EXECUTOR.CampaignExecutor(
        campaign, tmp_path / "execution", EXECUTOR.MemoryLeaseAdapter()
    ).run(passing)
    altered = copy.deepcopy(result)
    altered["metrics"]["model_reloads"] += 1
    with pytest.raises(MISSION.MissionError, match="identity invalid"):
        queue.terminalize(
            mission_id,
            "worker-a",
            altered,
            tmp_path / "execution",
            at="2026-07-23T00:01:30Z",
        )
    with pytest.raises(MISSION.MissionError, match="evidence file is missing"):
        queue.terminalize(
            mission_id,
            "worker-a",
            result,
            tmp_path / "missing-evidence",
            at="2026-07-23T00:01:45Z",
        )
    terminal = queue.terminalize(
        mission_id,
        "worker-a",
        result,
        tmp_path / "execution",
        at="2026-07-23T00:02:00Z",
    )
    assert terminal["state"] == "TERMINAL"
    assert terminal["result_id"] == result["result_id"]
    cas_files = [path for path in (queue.root / "cas" / "sha256").rglob("*") if path.is_file()]
    assert any(path.read_bytes() == MISSION.canonical_bytes(result) for path in cas_files)
    queue.verify(mission_id)


def test_unauthorized_checkpoint_does_not_write_cas(tmp_path: Path) -> None:
    _, mission, queue = fixture(tmp_path)
    mission_id = mission["mission_id"]
    queue.admit(mission, tmp_path, at="2026-07-23T00:00:00Z")
    queue.claim(mission_id, "worker-a", at="2026-07-23T00:01:00Z")
    with pytest.raises(MISSION.MissionError, match="ownership mismatch"):
        queue.checkpoint(
            mission_id,
            "worker-b",
            {"attempt": "unauthorized"},
            at="2026-07-23T00:02:00Z",
        )
    assert not (queue.root / "cas").exists()


def test_concurrent_recovery_before_terminal_recheck_does_not_write_cas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign, mission, queue = fixture(tmp_path)
    mission_id = mission["mission_id"]
    queue.admit(mission, tmp_path, at="2026-07-23T00:00:00Z")
    queue.claim(mission_id, "worker-a", at="2026-07-23T00:01:00Z")

    def passing(job: dict, attempt: int, repair: bool) -> EXECUTOR.JobOutcome:
        return EXECUTOR.JobOutcome(
            "PASS",
            EXECUTOR.canonical_bytes(
                {"node": job["node_id"], "attempt": attempt, "repair": repair}
            ),
        )

    result = EXECUTOR.CampaignExecutor(
        campaign, tmp_path / "execution", EXECUTOR.MemoryLeaseAdapter()
    ).run(passing)
    verify_evidence = queue._verify_result_evidence

    def recover_during_validation(result_packet: dict, evidence_root: Path) -> None:
        verify_evidence(result_packet, evidence_root)
        queue.recover_stale(
            mission_id,
            stale_before="2026-07-23T00:01:01Z",
            at="2026-07-23T00:02:00Z",
        )

    monkeypatch.setattr(queue, "_verify_result_evidence", recover_during_validation)
    terminal = queue.terminalize(
        mission_id,
        "worker-a",
        result,
        tmp_path / "execution",
        at="2026-07-23T00:03:00Z",
    )
    assert terminal["state"] == "TERMINAL"


def test_status_conforms_to_schema(tmp_path: Path) -> None:
    _, mission, queue = fixture(tmp_path)
    status = queue.admit(mission, tmp_path, at="2026-07-23T00:00:00Z")
    schema = json.loads(
        (
            ROOT
            / "Plan/08_SCHEMAS/runpod_autonomous_mission_queue_state.schema.json"
        ).read_text(encoding="utf-8")
    )
    jsonschema.Draft7Validator(
        schema, format_checker=jsonschema.FormatChecker()
    ).validate(status)
