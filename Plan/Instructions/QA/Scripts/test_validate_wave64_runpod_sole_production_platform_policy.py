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
