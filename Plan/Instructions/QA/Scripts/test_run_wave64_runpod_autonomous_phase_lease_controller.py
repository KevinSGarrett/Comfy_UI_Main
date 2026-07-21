from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
CONTROLLER_PATH = (
    ROOT
    / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_phase_lease_controller.py"
)
CONTRACT_ID = "a" * 64


def load_controller():
    spec = importlib.util.spec_from_file_location("w64_aqa_phase_lease", CONTROLLER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Clock:
    def __init__(self) -> None:
        self.value = datetime(2026, 7, 21, 20, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: int) -> None:
        self.value += timedelta(seconds=seconds)


def snapshot(**changes) -> dict:
    value = {
        "foreign_jobs": 0,
        "queue_running": 0,
        "queue_pending": 0,
        "vram_free_mib": 49000,
        "required_free_vram_mib": 40000,
        "overlay_used_percent": 70,
        "cost_per_hour_usd": 0.77,
        "estimated_phase_seconds": 600,
    }
    value.update(changes)
    return value


def new_controller(tmp_path: Path, clock: Clock):
    module = load_controller()
    controller = module.PhaseLeaseController(tmp_path / "lease.json", clock=clock)
    return module, controller


def test_generation_then_review_are_exclusive_and_replayable(tmp_path: Path) -> None:
    clock = Clock()
    module, controller = new_controller(tmp_path, clock)
    generation = controller.acquire(
        phase="generation",
        owner="job-owner",
        contract_id=CONTRACT_ID,
        snapshot=snapshot(),
        max_cost_usd=1.0,
        ttl_seconds=900,
    )
    with pytest.raises(module.LeaseError, match="ACTIVE_LEASE_CONFLICT"):
        controller.acquire(
            phase="review",
            owner="job-owner",
            contract_id=CONTRACT_ID,
            snapshot=snapshot(),
            max_cost_usd=1.0,
            ttl_seconds=900,
        )
    controller.complete(generation["lease_id"], actual_cost_usd=0.2, queue_idle=True)
    review = controller.acquire(
        phase="review",
        owner="job-owner",
        contract_id=CONTRACT_ID,
        snapshot=snapshot(required_free_vram_mib=20000),
        max_cost_usd=1.0,
        ttl_seconds=900,
    )
    controller.complete(review["lease_id"], actual_cost_usd=0.1, queue_idle=True)
    assert controller.state["state"] == "IDLE"
    controller.verify()
    reloaded = module.PhaseLeaseController(tmp_path / "lease.json", clock=clock)
    reloaded.verify()


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"foreign_jobs": 1}, "FOREIGN_JOB_PRESENT"),
        ({"queue_running": 1}, "QUEUE_NOT_IDLE"),
        ({"vram_free_mib": 1000}, "INSUFFICIENT_FREE_VRAM"),
        ({"overlay_used_percent": 85}, "OVERLAY_PRESSURE"),
        ({"estimated_phase_seconds": 7200}, "COST_BUDGET_EXCEEDED"),
    ],
)
def test_admission_failures_block_without_creating_a_lease(
    tmp_path: Path, changes: dict, reason: str
) -> None:
    clock = Clock()
    module, controller = new_controller(tmp_path, clock)
    with pytest.raises(module.LeaseError, match=reason):
        controller.acquire(
            phase="generation",
            owner="job-owner",
            contract_id=CONTRACT_ID,
            snapshot=snapshot(**changes),
            max_cost_usd=0.5,
            ttl_seconds=900,
        )
    assert controller.state["state"] == "BLOCKED"
    assert controller.state["lease"] is None
    assert reason in controller.state["blocked_reasons"]
    controller.clear_admission_block()
    assert controller.state["state"] == "IDLE"


def test_runtime_oom_preserves_lease_for_reconciliation(tmp_path: Path) -> None:
    clock = Clock()
    module, controller = new_controller(tmp_path, clock)
    lease = controller.acquire(
        phase="review",
        owner="job-owner",
        contract_id=CONTRACT_ID,
        snapshot=snapshot(),
        max_cost_usd=1,
        ttl_seconds=60,
    )
    controller.fail(lease["lease_id"], "OOM")
    assert controller.state["state"] == "BLOCKED"
    assert controller.state["lease"]["lease_id"] == lease["lease_id"]
    assert controller.state["blocked_reasons"] == ["OOM"]
    clock.advance(61)
    controller.reconcile_expired(queue_idle=True, owned_process_absent=True)
    assert controller.state["state"] == "IDLE"
    assert controller.state["lease"] is None


def test_expired_lease_fails_closed_until_owned_state_is_proven(tmp_path: Path) -> None:
    clock = Clock()
    module, controller = new_controller(tmp_path, clock)
    lease = controller.acquire(
        phase="model_load",
        owner="job-owner",
        contract_id=CONTRACT_ID,
        snapshot=snapshot(),
        max_cost_usd=1,
        ttl_seconds=30,
    )
    clock.advance(31)
    with pytest.raises(module.LeaseError, match="LEASE_EXPIRED"):
        controller.heartbeat(lease["lease_id"])
    with pytest.raises(module.LeaseError, match="OWNERSHIP_UNPROVEN"):
        controller.reconcile_expired(queue_idle=True, owned_process_absent=False)
    assert controller.state["state"] == "BLOCKED"


def test_completion_refuses_busy_queue_and_overspend(tmp_path: Path) -> None:
    clock = Clock()
    module, controller = new_controller(tmp_path, clock)
    lease = controller.acquire(
        phase="audio",
        owner="job-owner",
        contract_id=CONTRACT_ID,
        snapshot=snapshot(),
        max_cost_usd=0.5,
        ttl_seconds=300,
    )
    with pytest.raises(module.LeaseError, match="QUEUE_NOT_IDLE"):
        controller.complete(lease["lease_id"], actual_cost_usd=0.1, queue_idle=False)
    assert controller.state["lease"] is not None

    other_path = tmp_path / "other.json"
    other = module.PhaseLeaseController(other_path, clock=clock)
    other_lease = other.acquire(
        phase="audio",
        owner="job-owner",
        contract_id=CONTRACT_ID,
        snapshot=snapshot(),
        max_cost_usd=0.5,
        ttl_seconds=300,
    )
    with pytest.raises(module.LeaseError, match="COST_BUDGET_EXCEEDED"):
        other.complete(other_lease["lease_id"], actual_cost_usd=0.6, queue_idle=True)
    assert other.state["lease"] is not None


def test_journal_tampering_is_detected(tmp_path: Path) -> None:
    clock = Clock()
    module, controller = new_controller(tmp_path, clock)
    controller.verify()
    path = tmp_path / "lease.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["journal"][0]["details"]["controller_id"] = "tampered"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(module.LeaseError, match="event hash"):
        module.PhaseLeaseController(path, clock=clock)
