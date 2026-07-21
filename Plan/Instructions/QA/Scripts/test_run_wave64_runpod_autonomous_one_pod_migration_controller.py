from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
CONTROLLER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_one_pod_migration_controller.py"
GATES = ["storage_binding", "runtime_health", "gpu_topology", "model_residency", "failure_recovery", "quality_equivalence", "cost_ceiling", "rollback_readiness"]


def load_controller():
    spec = importlib.util.spec_from_file_location("w64_aqa_migration", CONTROLLER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def event(
    event_type: str, *, number: int = 1, candidate: str | None = None,
    profile: str = "preferred_2xa40", observed: dict | None = None, gate: str | None = None,
    passed: bool | None = None, queue_idle: bool | None = None, volume: str | None = None,
    approval: str | None = None,
) -> dict:
    return {
        "schema_version": "wave64.aqa.one_pod_migration_event.v1",
        "event_id": f"W64-AQA-MIG-test-{number}", "event_type": event_type,
        "profile_id": profile, "candidate_pod_id": candidate,
        "observed_profile": observed, "gate_id": gate, "passed": passed,
        "queue_idle": queue_idle, "network_volume_id": volume,
        "integration_authority_approval_sha256": approval,
        "evidence_sha256": [f"{number % 16:x}" * 64] if event_type not in {"STOCK_UNAVAILABLE", "REQUEST_OLD_POD_STOP"} else [],
    }


def a40_profile(*, hourly: float = 0.70) -> dict:
    return {"gpu_type": "NVIDIA A40", "gpu_count": 2, "aggregate_vram_gb": 96, "ram_gb": 100, "vcpu": 18, "hourly_usd": hourly}


def candidate_created(module) -> dict:
    state = module.initialize_state("current-pod", "volume-1")
    return module.transition(state, event(
        "CANDIDATE_CREATED", candidate="candidate-pod", observed=a40_profile(),
        queue_idle=True, volume="volume-1",
    ))


def test_initial_and_stock_wait_states_keep_current_pod_authoritative() -> None:
    module = load_controller()
    state = module.initialize_state("current-pod", "volume-1")
    assert state["phase"] == "STOCK_WAIT"
    assert state["current_pod_remains_authoritative"] is True
    assert state["old_pod_stop_authorized"] is False
    waited = module.transition(state, event("STOCK_UNAVAILABLE"))
    assert waited["phase"] == "STOCK_WAIT"
    assert waited["execution_performed"] is False


def test_exact_idle_queue_a40_candidate_is_admitted_without_execution() -> None:
    module = load_controller()
    state = candidate_created(module)
    assert state["phase"] == "CANDIDATE_QUALIFYING"
    assert state["candidate_pod_id"] == "candidate-pod"
    assert state["candidate_hourly_usd"] == 0.70
    assert state["authoritative_pod_id"] == "current-pod"
    assert state["execution_performed"] is False


@pytest.mark.parametrize("observed,idle,volume,match", [
    (a40_profile(hourly=0.71), True, "volume-1", "hourly_cost"),
    ({**a40_profile(), "gpu_count": 1}, True, "volume-1", "gpu_count"),
    (a40_profile(), False, "volume-1", "idle"),
    (a40_profile(), True, "wrong-volume", "network volume"),
])
def test_price_topology_busy_queue_and_volume_mismatch_fail_closed(observed: dict, idle: bool, volume: str, match: str) -> None:
    module = load_controller()
    state = module.initialize_state("current-pod", "volume-1")
    with pytest.raises(module.MigrationError, match=match):
        module.transition(state, event("CANDIDATE_CREATED", candidate="candidate-pod", observed=observed, queue_idle=idle, volume=volume))


def test_all_eight_gates_are_required_before_migration_ready() -> None:
    module = load_controller()
    state = candidate_created(module)
    for index, gate in enumerate(GATES, start=2):
        state = module.transition(state, event("QUALIFICATION_GATE", number=index, candidate="candidate-pod", gate=gate, passed=True))
        if gate != GATES[-1]:
            assert state["phase"] == "CANDIDATE_QUALIFYING"
    assert state["phase"] == "MIGRATION_READY"
    assert set(state["passed_gates"]) == set(GATES)
    assert state["old_pod_stop_authorized"] is False


def test_failed_gate_requires_rollback_and_candidate_termination_preserves_current() -> None:
    module = load_controller()
    state = candidate_created(module)
    failed = module.transition(state, event("QUALIFICATION_GATE", number=2, candidate="candidate-pod", gate="quality_equivalence", passed=False))
    assert failed["phase"] == "ROLLBACK_REQUIRED"
    rolled = module.transition(failed, event("CANDIDATE_TERMINATED", number=3, candidate="candidate-pod"))
    assert rolled["phase"] == "ROLLED_BACK"
    assert rolled["authoritative_pod_id"] == "current-pod"
    assert rolled["candidate_pod_id"] is None


def test_switch_and_old_stop_require_all_gates_and_separate_integration_approvals() -> None:
    module = load_controller()
    qualifying = candidate_created(module)
    with pytest.raises(module.MigrationError, match="old pod stop"):
        module.transition(qualifying, event("REQUEST_OLD_POD_STOP"))
    state = qualifying
    for index, gate in enumerate(GATES, start=2):
        state = module.transition(state, event("QUALIFICATION_GATE", number=index, candidate="candidate-pod", gate=gate, passed=True))
    with pytest.raises(module.MigrationError, match="approval"):
        module.transition(state, event("INTEGRATION_SWITCH_COMMITTED", number=20, candidate="candidate-pod"))
    switched = module.transition(state, event("INTEGRATION_SWITCH_COMMITTED", number=21, candidate="candidate-pod", approval="a" * 64))
    assert switched["phase"] == "NEW_AUTHORITATIVE"
    assert switched["authoritative_pod_id"] == "candidate-pod"
    assert switched["legacy_pod_id"] == "current-pod"
    assert switched["old_pod_stop_authorized"] is True
    stop = module.transition(switched, event("REQUEST_OLD_POD_STOP", number=22, approval="b" * 64))
    assert stop["execution_performed"] is False
    assert "OLD_POD_STOP_ADMITTED_FOR_SEPARATE_EXECUTOR_NOT_EXECUTED" in stop["reason_codes"]


def test_blackwell_fallback_requires_explicit_approval_and_exact_profile() -> None:
    module = load_controller()
    state = module.initialize_state("current-pod", "volume-1")
    profile = {"gpu_type": "NVIDIA RTX PRO 6000 Blackwell Server Edition", "gpu_count": 1, "aggregate_vram_gb": 96, "ram_gb": 124, "vcpu": 32, "hourly_usd": 1.69}
    request = event("CANDIDATE_CREATED", profile="performance_fallback_blackwell96", candidate="candidate-pod", observed=profile, queue_idle=True, volume="volume-1")
    with pytest.raises(module.MigrationError, match="explicit"):
        module.transition(state, request)
    request["integration_authority_approval_sha256"] = "c" * 64
    result = module.transition(state, request)
    assert result["profile_id"] == "performance_fallback_blackwell96"


def test_duplicate_candidate_out_of_order_gate_and_tampered_state_are_denied() -> None:
    module = load_controller()
    state = candidate_created(module)
    with pytest.raises(module.MigrationError, match="duplicate"):
        module.transition(state, event("CANDIDATE_CREATED", number=2, candidate="other", observed=a40_profile(), queue_idle=True, volume="volume-1"))
    waiting = module.initialize_state("current-pod", "volume-1")
    with pytest.raises(module.MigrationError, match="active candidate"):
        module.transition(waiting, event("QUALIFICATION_GATE", candidate="candidate-pod", gate="storage_binding", passed=True))
    state["authoritative_pod_id"] = "tampered"
    with pytest.raises(module.MigrationError, match="hash chain"):
        module.transition(state, event("QUALIFICATION_GATE", candidate="candidate-pod", gate="storage_binding", passed=True))
