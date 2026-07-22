from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_runpod_autonomous_role_package_inventory.py"
INVENTORY = ROOT / "Plan/10_REGISTRIES/wave64_runpod_autonomous_role_package_inventory.json"
SPEC = importlib.util.spec_from_file_location("role_package_inventory_validator", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_inventory() -> dict:
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


def test_inventory_is_valid() -> None:
    assert MODULE.validate(load_inventory()) == []


def test_availability_lane_cannot_block_current_pod() -> None:
    data = copy.deepcopy(load_inventory())
    data["runtime_policy"]["availability_lane"]["nonblocking"] = False
    assert "2x A40 lane must be exact and nonblocking" in MODULE.validate(data)


def test_availability_lane_cannot_auto_migrate() -> None:
    data = copy.deepcopy(load_inventory())
    data["runtime_policy"]["availability_lane"]["auto_migrate"] = True
    assert "2x A40 lane authority is too broad" in MODULE.validate(data)


def test_uninstalled_package_cannot_claim_digest() -> None:
    data = copy.deepcopy(load_inventory())
    package = next(item for item in data["packages"] if item["installation"]["state"] == "UPSTREAM_IDENTITY_VERIFIED_NOT_INSTALLED")
    package["installation"]["artifact_digest"] = "a" * 64
    assert any("uninstalled package cannot claim artifact/root" in error for error in MODULE.validate(data))


def test_installed_digest_drift_fails() -> None:
    data = copy.deepcopy(load_inventory())
    package = next(item for item in data["packages"] if item["identity"]["repository_id"] == "qwen2.5vl:32b")
    package["installation"]["artifact_digest"] = "b" * 64
    assert "installed digest inventory mismatch" in MODULE.validate(data)


def test_no_package_is_operational_without_certificate() -> None:
    data = copy.deepcopy(load_inventory())
    data["packages"][0]["authority"]["operational"] = True
    assert any("operational must remain false" in error for error in MODULE.validate(data))


def test_asr_source_revision_is_exact_and_still_uninstalled() -> None:
    data = copy.deepcopy(load_inventory())
    package = next(item for item in data["packages"] if item["identity"]["repository_id"] == "Qwen/Qwen3-ASR-1.7B")
    assert package["source_pin"]["revision"] == "7278e1e70fe206f11671096ffdd38061171dd6e5"
    assert package["installation"]["state"] == "UPSTREAM_IDENTITY_VERIFIED_NOT_INSTALLED"
    package["source_pin"]["revision"] = "0" * 40
    assert any("source revision pin mismatch" in error for error in MODULE.validate(data))
