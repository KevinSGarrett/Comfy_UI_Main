from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_runpod_sole_production_platform_policy.py"


def load_module():
    spec = importlib.util.spec_from_file_location("runpod_platform_policy", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def policy(module):
    return json.loads((ROOT / module.POLICY_PATH).read_text(encoding="utf-8"))


def test_runpod_is_sole_active_production_platform() -> None:
    module = load_module()
    value = policy(module)
    module.validate_policy(ROOT, value)
    assert value["active_platform"] == "RUNPOD"
    assert value["runpod"]["production_runtime"] is True
    assert value["runpod"]["production_storage"] is True
    assert value["legacy_cloud"]["active_production_blocker"] is False
    assert value["tracker_reclassification"]["required_for_runpod_production"] is False


def test_legacy_cloud_cannot_be_reenabled_by_policy_drift() -> None:
    module = load_module()
    value = copy.deepcopy(policy(module))
    value["legacy_cloud"]["automatic_access_allowed"] = True
    with pytest.raises(Exception):
        module.validate_policy(ROOT, value)


def test_cpu_and_gpu_lease_boundaries_are_distinct() -> None:
    module = load_module()
    value = policy(module)
    assert value["local"]["cpu_only_work_allowed_without_lease"] is True
    assert value["runpod"]["gpu_coordinator_required"] is True
    assert value["runpod"]["foreign_hold_override_forbidden"] is True


def test_only_exact_user_authorized_guarded_migration_watcher_is_active() -> None:
    module = load_module()
    value = policy(module)
    watcher = value["guarded_migration_watcher"]
    assert watcher["automation_id"] == "runpod-us-wa-1-2xa40-guarded-migration-watcher"
    assert watcher["gpu_type"] == "NVIDIA A40"
    assert watcher["gpu_count"] == 2
    assert watcher["maximum_total_hourly_usd"] == 0.70
    assert watcher["network_volume_id"] == "o9qv2ld91c"
    assert watcher["current_pod_authoritative_until_verified_migration_complete"] is True
    assert watcher["pod_termination"] is False


def test_competing_watcher_authority_drift_fails() -> None:
    module = load_module()
    value = copy.deepcopy(policy(module))
    value["guarded_migration_watcher"]["competing_watcher_forbidden"] = False
    with pytest.raises(Exception):
        module.validate_policy(ROOT, value)
