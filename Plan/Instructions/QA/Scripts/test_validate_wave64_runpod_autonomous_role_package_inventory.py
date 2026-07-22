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


def test_independent_juror_uses_pinned_native_hf_without_remote_code() -> None:
    data = copy.deepcopy(load_inventory())
    package = next(
        item
        for item in data["packages"]
        if item["identity"]["repository_id"] == "OpenGVLab/InternVL3_5-241B-A28B-HF"
    )
    assert package["source_pin"]["revision"] == "b941ed62ed4e2b711be4271b55034c2c97c57f33"
    assert package["source_pin"]["native_hf_format"] is True
    assert package["source_pin"]["weight_shard_count"] == 97
    assert package["installation"]["state"] == "UPSTREAM_IDENTITY_VERIFIED_NOT_INSTALLED"
    assert "trust_remote_code" in package["authority"]["forbidden"]
    assert "remote_code_review" not in package["qualification"]["required_gates"]
    assert not package["authority"]["operational"]
    package["source_pin"]["source_manifest_sha256"] = "0" * 64
    assert any("native HF source pin mismatch" in error for error in MODULE.validate(data))


def test_asr_source_revision_and_storage_install_are_exact_but_not_operational() -> None:
    data = copy.deepcopy(load_inventory())
    package = next(item for item in data["packages"] if item["identity"]["repository_id"] == "Qwen/Qwen3-ASR-1.7B")
    assert package["source_pin"]["revision"] == "7278e1e70fe206f11671096ffdd38061171dd6e5"
    assert package["installation"]["state"] == "INSTALLED_FILE_SET_VERIFIED_ACTIVATION_PENDING"
    assert package["dependency_preflight"]["state"] == "CONFIG_IDENTITY_PASS_DEPENDENCY_ACTION_REQUIRED"
    assert package["dependency_environment"]["state"] == "INSTALLED_IMPORT_VERIFIED_RUNTIME_PENDING"
    assert package["dependency_environment"]["distribution_count"] == 105
    assert package["import_canary"]["state"] == "IMPORT_ONLY_CLASS_RESOLUTION_PASS_RUNTIME_PENDING"
    assert package["import_canary"]["post_canary_tree_sha256"] == package["dependency_environment"]["tree_sha256"]
    assert package["static_qualification"]["state"] == "LICENSE_AND_ARTIFACT_HASH_PASS"
    assert package["identity"]["license_state"] == "APACHE-2.0_ACCEPTED_FOR_COMFY_UI_MAIN_PROJECT_USE"
    assert "dependency_environment" not in package["qualification"]["required_gates"]
    assert "import_canary" not in package["qualification"]["required_gates"]
    assert "license_acceptance" not in package["qualification"]["required_gates"]
    assert "artifact_hash" not in package["qualification"]["required_gates"]
    assert not package["authority"]["operational"]
    package["source_pin"]["revision"] = "0" * 40
    assert any("source revision pin mismatch" in error for error in MODULE.validate(data))


def test_omni_source_pin_and_storage_install_are_exact_but_not_operational() -> None:
    data = copy.deepcopy(load_inventory())
    package = next(
        item
        for item in data["packages"]
        if item["identity"]["repository_id"]
        == "Qwen/Qwen3-Omni-30B-A3B-Thinking"
    )
    assert package["source_pin"]["revision"] == "2f443cfc4c54b14a815c0e2bb9a9d6cbcd9a748b"
    assert package["installation"]["state"] == "INSTALLED_FILE_SET_VERIFIED_ACTIVATION_PENDING"
    assert package["installation"]["artifact_digest"] == package["install_admission"]["manifest_sha256"]
    assert package["install_admission"]["weight_shard_count"] == 16
    assert package["install_admission"]["weight_bytes"] == 63440997640
    assert package["installation_receipt"]["replay"] == "REUSED_VERIFIED_INSTALL"
    assert package["dependency_preflight"]["state"] == "CONFIG_IDENTITY_PASS_DEPENDENCY_ACTION_REQUIRED"
    assert package["dependency_preflight"]["gaps"] == [
        "QWEN_OMNI_UTILS_DISTRIBUTION_MISSING",
        "INSTALLED_TRANSFORMERS_LACKS_QWEN3_OMNI_SUPPORT",
    ]
    assert package["dependency_environment"]["state"] == "INSTALLED_IMPORT_VERIFIED_RUNTIME_PENDING"
    assert package["dependency_environment"]["distribution_count"] == 75
    assert package["dependency_environment"]["pip_check"] == "PASS_75_PACKAGES_COMPATIBLE"
    assert package["dependency_environment"]["active_environment_unchanged"] is True
    assert package["dependency_environment"]["replay"] == "REUSED_VERIFIED_ENVIRONMENT"
    assert package["import_canary"]["state"] == "IMPORT_ONLY_CLASS_RESOLUTION_PASS_RUNTIME_PENDING"
    assert package["import_canary"]["post_canary_tree_sha256"] == package[
        "dependency_environment"
    ]["tree_sha256"]
    assert "import_canary" not in package["qualification"]["required_gates"]
    assert "pinned_revision" not in package["qualification"]["required_gates"]
    assert "artifact_hash" not in package["qualification"]["required_gates"]
    assert not package["authority"]["operational"]
    package["install_admission"]["weight_bytes"] += 1
    assert any("Omni install admission mismatch" in error for error in MODULE.validate(data))
