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


def test_only_authorized_alternative_hardware_watcher_is_enabled() -> None:
    data = copy.deepcopy(load_inventory())
    data["runtime_policy"]["current_pod_only"]["authorized_watcher_id"] = "competing-watcher"
    assert "current-pod-only runtime policy mismatch" in MODULE.validate(data)


def test_current_pod_must_remain_authoritative_during_candidate_creation() -> None:
    data = copy.deepcopy(load_inventory())
    data["runtime_policy"]["current_pod_only"]["current_pod_authoritative_until_verified_migration_complete"] = False
    assert "current-pod-only runtime policy mismatch" in MODULE.validate(data)


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


def test_qwen3vl4_official_manifest_and_license_are_exact_but_runtime_is_not_operational() -> None:
    data = copy.deepcopy(load_inventory())
    package = next(
        item for item in data["packages"] if item["identity"]["repository_id"] == "qwen3-vl:4b-instruct-q4_K_M"
    )
    assert package["identity"]["identity_state"] == "OFFICIAL_UPSTREAM_IDENTITY_VERIFIED_REVISION_PINNED"
    assert package["identity"]["license_state"] == "APACHE-2.0_ACCEPTED_FOR_COMFY_UI_MAIN_PROJECT_USE"
    assert package["static_qualification"]["manifest_sha256"] == package["installation"]["artifact_digest"]
    assert package["static_qualification"]["license_sha256"] == (
        "7339fa418c9ad3e8e12e74ad0fd26a9cc4be8703f9c110728a992b193be85cb2"
    )
    assert package["qualification"]["state"] == "CURRENT_SCOPED_AUTHORITY_ONLY"
    assert package["authority"]["operational"] is False


def test_qwen3vl4_official_manifest_drift_fails() -> None:
    data = copy.deepcopy(load_inventory())
    package = next(
        item for item in data["packages"] if item["identity"]["repository_id"] == "qwen3-vl:4b-instruct-q4_K_M"
    )
    package["static_qualification"]["model_sha256"] = "0" * 64
    assert any("Qwen3-VL 4B official manifest mismatch" in error for error in MODULE.validate(data))


def test_qwen3vl4_license_drift_fails() -> None:
    data = copy.deepcopy(load_inventory())
    package = next(
        item for item in data["packages"] if item["identity"]["repository_id"] == "qwen3-vl:4b-instruct-q4_K_M"
    )
    package["identity"]["license_state"] = "LOCAL_RUNTIME_LICENSE_NOT_REVERIFIED"
    assert any("Qwen3-VL 4B official identity mismatch" in error for error in MODULE.validate(data))


def test_qwen3vl8_official_manifest_and_license_are_exact_but_runtime_is_not_operational() -> None:
    data = copy.deepcopy(load_inventory())
    package = next(item for item in data["packages"] if item["identity"]["repository_id"] == "qwen3-vl:8b-instruct-q4_K_M")
    assert package["identity"]["identity_state"] == "OFFICIAL_UPSTREAM_IDENTITY_VERIFIED_REVISION_PINNED"
    assert package["identity"]["license_state"] == "APACHE-2.0_ACCEPTED_FOR_COMFY_UI_MAIN_PROJECT_USE"
    assert package["static_qualification"]["manifest_sha256"] == package["installation"]["artifact_digest"]
    assert package["authority"]["operational"] is False


def test_qwen3vl8_official_manifest_drift_fails() -> None:
    data = copy.deepcopy(load_inventory())
    package = next(item for item in data["packages"] if item["identity"]["repository_id"] == "qwen3-vl:8b-instruct-q4_K_M")
    package["static_qualification"]["config_sha256"] = "0" * 64
    assert any("Qwen3-VL 8B official manifest mismatch" in error for error in MODULE.validate(data))


def test_qwen25vl7_official_manifest_and_license_are_exact_but_runtime_is_false() -> None:
    data = copy.deepcopy(load_inventory())
    package = next(item for item in data["packages"] if item["identity"]["repository_id"] == "qwen2.5vl:7b")
    assert package["static_qualification"]["manifest_sha256"] == package["installation"]["artifact_digest"]
    assert package["identity"]["license_state"] == "APACHE-2.0_ACCEPTED_FOR_COMFY_UI_MAIN_PROJECT_USE"
    assert package["authority"]["operational"] is False
    package["static_qualification"]["license_sha256"] = "0" * 64
    assert any("Qwen2.5-VL 7B official manifest mismatch" in error for error in MODULE.validate(data))


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
    assert package["candidate_quantized_route"]["combined_bytes"] == 131260400544
    assert package["candidate_quantized_route"]["model_header"]["general_architecture"] == "qwen3moe"
    assert package["candidate_quantized_route"]["projector_header"]["projector_type"] == "internvl"
    assert package["loader_preflight"]["revision"] == "e8e6c7af2456fd50bb62f7a2bbd642e6fb14ae77"
    assert package["loader_preflight"]["internvl_3_5_explicitly_documented"] is False
    assert package["storage_admission"]["exact_live_free_quota_known"] is False
    assert package["storage_admission"]["minimum_free_before_download_gib"] == 172.24577417969704
    assert package["storage_admission"]["download_started"] is False
    assert "download_without_storage_admission" in package["authority"]["forbidden"]
    assert not package["authority"]["operational"]
    package["source_pin"]["source_manifest_sha256"] = "0" * 64
    assert any("native HF source pin mismatch" in error for error in MODULE.validate(data))


def test_independent_juror_download_gate_fails_closed_on_drift() -> None:
    data = copy.deepcopy(load_inventory())
    package = next(
        item
        for item in data["packages"]
        if item["identity"]["repository_id"] == "OpenGVLab/InternVL3_5-241B-A28B-HF"
    )
    package["storage_admission"]["download_started"] = True
    assert any("storage admission mismatch" in error for error in MODULE.validate(data))


def test_provisional_internvl_storage_is_exact_but_cannot_replace_juror() -> None:
    data = copy.deepcopy(load_inventory())
    package = next(item for item in data["packages"] if item["identity"]["repository_id"] == "OpenGVLab/InternVL3_5-8B")
    assert package["source_pin"]["revision"] == "9bb6a56ad9cc69db95e2d4eeb15a52bbcac4ef79"
    assert package["source_pin"]["source_file_count"] == 24
    assert package["source_pin"]["source_total_bytes"] == 17072800269
    assert package["installation"]["artifact_digest"] == "410f3673d769f25c3a69676676863cabceb550e340bc384855bed2c429dcce31"
    assert package["static_code_review"]["reviewer_script_sha256"] == "2b4fa339162decd1a88ff5b47d7819dfe685410e60144c655666ad128e19c3da"
    assert package["static_code_review"]["remote_receipt_sha256"] == "fef7ea03da4388acfb38b5d999d03396b0b53c9635978a669e05af92b462bd83"
    assert package["static_code_review"]["quality_findings"] == [
        "FLASH_ATTN_IMPORT_CATCHES_BROAD_EXCEPTION",
        "TOKEN_COUNT_MISMATCH_FALLBACK_USES_CHAINED_ADVANCED_INDEX_ASSIGNMENT",
    ]
    assert package["dependency_preflight"]["reuse_candidate"]["missing_required_addons"] == ["timm", "einops"]
    assert package["dependency_environment"]["lock_sha256"] == "9f7317aef1cf2beb0f67bc879b8d3676d542fb691dc61d337aff268474cda5a6"
    assert package["dependency_environment"]["installed_tree_sha256"] == "1191178fb3f8ff148b7330767f8d0e1dd0f3418cfacd29d0f3ce19490f6895b7"
    assert package["dependency_environment"]["metadata_validation"]["receipt_sha256"] == "e3fbd176c84114f5360f46cf5986e2514682539414f47dc09638da75e9ddc711"
    assert package["license_qualification"]["state"] == "PROJECT_USE_ACCEPTED_NOTICE_RETENTION_REQUIRED"
    assert package["license_qualification"]["standalone_license_file_in_snapshot"] is False
    assert "license_acceptance" not in package["qualification"]["required_gates"]
    assert package["import_canary"]["admission_sha256"] == "2f723b1b9341087553fb3abe44c83060248aa8316f065997371d54d93589f191"
    assert package["import_canary"]["executed"] is False
    assert "full_remote_code_review" not in package["qualification"]["required_gates"]
    assert "dependency_environment" not in package["qualification"]["required_gates"]
    assert "import_canary" in package["qualification"]["required_gates"]
    assert "independent_juror_substitution" in package["authority"]["forbidden"]
    assert package["authority"]["operational"] is False
    package["source_pin"]["source_total_bytes"] += 1
    assert any("provisional InternVL source pin mismatch" in error for error in MODULE.validate(data))


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
    assert "capacity" not in package["qualification"]["required_gates"]
    assert "runtime" not in package["qualification"]["required_gates"]
    assert package["runtime_canary"]["state"] == "EXACT_FIXTURE_TRANSCRIPTION_AND_PROCESS_EXIT_CLEANUP_PASS"
    assert package["runtime_canary"]["process_exit_cleanup_delta_mib"] == 5
    assert package["runtime_canary"]["audio_sha256"] == "5a07f0a654499266509453421c3efdc1b2e4ce83b8706e0138ebc4b1d3ad924a"
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


def test_promoted_clap_runtime_is_exact_but_speech_authority_remains_forbidden() -> None:
    data = copy.deepcopy(load_inventory())
    package = next(
        item
        for item in data["packages"]
        if item["identity"]["repository_id"] == "laion/larger_clap_general"
    )
    canary = package["supporting_runtime_canary"]
    assert package["source_pin"]["revision"] == "ada0c23a36c4e8582805bb38fec3905903f18b41"
    assert package["installation"]["artifact_digest"] == "b35a1ac3fc7cf0ed32822667e85240b0620cba5ed65988c0a707445ef7e593cc"
    assert canary["vector_dimension"] == 512
    assert canary["repeat_max_abs_delta"] == 0.0
    assert canary["process_exit_cleanup_delta_mib"] == 0
    assert canary["expected_top_label"] == "a person speaking clearly"
    assert canary["observed_top_label"] == "silence"
    assert "speech_event_approval" in package["authority"]["forbidden"]
    assert not package["authority"]["operational"]
    canary["observed_top_label"] = "a person speaking clearly"
    assert any("supporting runtime canary mismatch" in error for error in MODULE.validate(data))
