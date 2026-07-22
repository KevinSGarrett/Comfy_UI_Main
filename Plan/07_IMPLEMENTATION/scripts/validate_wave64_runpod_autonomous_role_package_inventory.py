#!/usr/bin/env python3
"""Validate the fail-closed W64-AQA role package inventory."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


EXPECTED_INSTALLED = {
    "qwen2.5vl:32b": "3edc3a52fe988de3e8ba4f99ac1f21a1bbc35e1af32a74983fe4e1667d6b6188",
    "qwen3-vl:4b-instruct-q4_K_M": "ee4b975b58c17ce268cd19d40db35d5edc64603035d2ffc1fee1968eb0947f7b",
    "qwen3-vl:8b-instruct-q4_K_M": "0533d74300e4f9bc367d675d4e64ffd073d50ff16a2b4096cc2e8a1cf8c96319",
    "qwen2.5vl:7b": "5ced39dfa4bac325dc183dd1e4febaa1c46b3ea28bce48896c8e69c1e79611cc",
    "llava:13b": "0d0eb4d7f485d7d0a21fd9b0c1d5b04da481d2150a097e81b64acb59758fdef6",
    "qwen2.5:7b-instruct": "845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e",
    "llama3.2-vision:11b": "6f2f9757ae97e8a3f8ea33d6adb2b11d93d9a35bef277cd2c0b1b5af8e8d0b1e",
}

EXPECTED_PLANNED = {
    "Qwen/Qwen3.6-35B-A3B",
    "Qwen/Qwen3.5-122B-A10B",
    "OpenGVLab/InternVL3_5-241B-A28B",
    "Qwen/Qwen3-Omni-30B-A3B-Thinking",
    "Qwen/Qwen3-ASR-1.7B",
    "Qwen/Qwen3-Coder-Next",
    "Qwen/Qwen3.5-397B-A17B",
}

PINNED_PLANNED = {
    "Qwen/Qwen3-ASR-1.7B": "7278e1e70fe206f11671096ffdd38061171dd6e5",
    "Qwen/Qwen3-Omni-30B-A3B-Thinking": "2f443cfc4c54b14a815c0e2bb9a9d6cbcd9a748b",
}


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != "wave64.aqa.role_package_inventory.v1":
        errors.append("schema_version mismatch")
    if data.get("scope") != "METADATA_ONLY_NO_DOWNLOAD_LOAD_INFERENCE_OR_RUNPOD_CONTACT":
        errors.append("scope must remain metadata-only")
    policy = data.get("runtime_policy", {})
    if policy.get("current_pod_remains_authoritative") is not True:
        errors.append("current pod must remain authoritative")
    if policy.get("single_gpu_role_at_a_time") is not True or policy.get("durable_root") != "/workspace":
        errors.append("current-pod residency policy mismatch")
    lane = policy.get("availability_lane", {})
    expected_profile = "2x NVIDIA A40; 96 GB aggregate VRAM; >=100 GB RAM; >=18 vCPU; <=0.70 USD/hour"
    if lane.get("profile") != expected_profile or lane.get("nonblocking") is not True:
        errors.append("2x A40 lane must be exact and nonblocking")
    if lane.get("maximum_idle_candidates") != 1 or lane.get("auto_migrate") is not False or lane.get("auto_stop_current_pod") is not False:
        errors.append("2x A40 lane authority is too broad")

    packages = data.get("packages", [])
    ids = [item.get("package_id") for item in packages]
    if len(ids) != len(set(ids)):
        errors.append("package_id values must be unique")
    installed: dict[str, str | None] = {}
    planned: set[str] = set()
    for item in packages:
        identity = item.get("identity", {})
        install = item.get("installation", {})
        authority = item.get("authority", {})
        qualification = item.get("qualification", {})
        if authority.get("operational") is not False:
            errors.append(f"{item.get('package_id')}: operational must remain false")
        if not authority.get("forbidden"):
            errors.append(f"{item.get('package_id')}: forbidden authority required")
        if not qualification.get("required_gates"):
            errors.append(f"{item.get('package_id')}: qualification gates required")
        state = install.get("state")
        if state == "INSTALLED_DIGEST_VERIFIED_ACTIVATION_SCOPED":
            digest = install.get("artifact_digest")
            if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                errors.append(f"{item.get('package_id')}: installed digest invalid")
            if install.get("durable_root") != "/workspace/ollama":
                errors.append(f"{item.get('package_id')}: installed root mismatch")
            installed[identity.get("repository_id", "")] = digest
        elif state in {
            "UPSTREAM_IDENTITY_VERIFIED_NOT_INSTALLED",
            "INSTALLED_FILE_SET_VERIFIED_ACTIVATION_PENDING",
            "STORAGE_INSTALL_ADMITTED_EXECUTION_PENDING",
        }:
            if state == "UPSTREAM_IDENTITY_VERIFIED_NOT_INSTALLED" and (
                install.get("artifact_digest") is not None or install.get("durable_root") is not None
            ):
                errors.append(f"{item.get('package_id')}: uninstalled package cannot claim artifact/root")
            repository_id = identity.get("repository_id", "")
            source_pin = item.get("source_pin")
            if repository_id in PINNED_PLANNED:
                if identity.get("identity_state") != "OFFICIAL_UPSTREAM_IDENTITY_VERIFIED_REVISION_PINNED":
                    errors.append(f"{item.get('package_id')}: pinned identity state mismatch")
                if not isinstance(source_pin, dict) or source_pin.get("revision") != PINNED_PLANNED[repository_id]:
                    errors.append(f"{item.get('package_id')}: source revision pin mismatch")
                if "pinned_revision" in qualification.get("required_gates", []):
                    errors.append(f"{item.get('package_id')}: completed revision gate must be removed")
                if repository_id == "Qwen/Qwen3-ASR-1.7B" and state == "INSTALLED_FILE_SET_VERIFIED_ACTIVATION_PENDING":
                    receipt = item.get("installation_receipt", {})
                    preflight = item.get("dependency_preflight", {})
                    environment = item.get("dependency_environment", {})
                    import_canary = item.get("import_canary", {})
                    static_qualification = item.get("static_qualification", {})
                    expected_root = f"/workspace/w64_aqa/models/Qwen3-ASR-1.7B/{PINNED_PLANNED[repository_id]}"
                    if install.get("durable_root") != expected_root:
                        errors.append(f"{item.get('package_id')}: installed file-set root mismatch")
                    if install.get("artifact_digest") != "e733f6863ecf6e3cd2d5579cd50c6e8cd35c78739316757633ad70c879edba60":
                        errors.append(f"{item.get('package_id')}: install manifest digest mismatch")
                    if receipt.get("sha256") != "cd52de9d1c4495d42c007d648dfa0355aa57eec64457cbdf967ba9ef39aa004e":
                        errors.append(f"{item.get('package_id')}: installation receipt mismatch")
                    if receipt.get("replay") != "REUSED_VERIFIED_INSTALL":
                        errors.append(f"{item.get('package_id')}: verified install replay required")
                    if preflight.get("state") != "CONFIG_IDENTITY_PASS_DEPENDENCY_ACTION_REQUIRED":
                        errors.append(f"{item.get('package_id')}: dependency preflight state mismatch")
                    if preflight.get("receipt_sha256") != "ce3e2d78a2bfb13827f0aa4a73cc89d7dc8bb615192b7c3c71fef290d5267b0e":
                        errors.append(f"{item.get('package_id')}: dependency preflight receipt mismatch")
                    if preflight.get("gaps") != [
                        "QWEN_ASR_DISTRIBUTION_MISSING",
                        "INSTALLED_TRANSFORMERS_LACKS_QWEN3_ASR_SUPPORT",
                    ]:
                        errors.append(f"{item.get('package_id')}: dependency gaps mismatch")
                    if "dependency_environment" in qualification.get("required_gates", []):
                        errors.append(f"{item.get('package_id')}: completed dependency environment gate must be removed")
                    if "import_canary" in qualification.get("required_gates", []):
                        errors.append(f"{item.get('package_id')}: completed import canary gate must be removed")
                    if qualification.get("state") != "STATIC_AND_IMPORT_GATES_PASS_RUNTIME_GATES_PENDING":
                        errors.append(f"{item.get('package_id')}: qualification state mismatch")
                    for completed_gate in ("license_acceptance", "artifact_hash"):
                        if completed_gate in qualification.get("required_gates", []):
                            errors.append(
                                f"{item.get('package_id')}: completed {completed_gate} gate must be removed"
                            )
                    if environment.get("state") != "INSTALLED_IMPORT_VERIFIED_RUNTIME_PENDING":
                        errors.append(f"{item.get('package_id')}: dependency environment state mismatch")
                    if environment.get("receipt_sha256") != "e09c67aee503f511124b50af539067c9f82f1969490ab9b7d5127d9870c9dcd4":
                        errors.append(f"{item.get('package_id')}: dependency environment receipt mismatch")
                    if environment.get("tree_sha256") != "6625aa3c76c411424ede40ce6275d0fb378a1d9a017c205f74ffd356386f7c4a":
                        errors.append(f"{item.get('package_id')}: dependency environment tree mismatch")
                    if environment.get("distribution_count") != 105:
                        errors.append(f"{item.get('package_id')}: dependency environment distribution count mismatch")
                    expected_canary = {
                        "state": "IMPORT_ONLY_CLASS_RESOLUTION_PASS_RUNTIME_PENDING",
                        "commit": "79b24a0a8bd03100fb8e086e57c346685002a94f",
                        "script_sha256": "8469b3761f7ea9df9867b4a57f5641660692731bc39b83b509a87673973c8a56",
                        "receipt_sha256": "2e734d753744cf1c017fc9f92de111a0cee0a76d45ff8612a93ee70d10e0126f",
                        "post_canary_tree_sha256": "6625aa3c76c411424ede40ce6275d0fb378a1d9a017c205f74ffd356386f7c4a",
                        "evidence": "Plan/Tracker/Evidence/W64_AQA_QWEN3_ASR_17B_IMPORT_CANARY_20260722T013835Z/evidence.json",
                    }
                    if import_canary != expected_canary:
                        errors.append(f"{item.get('package_id')}: import canary evidence mismatch")
                    expected_static_qualification = {
                        "state": "LICENSE_AND_ARTIFACT_HASH_PASS",
                        "evidence": "Plan/Tracker/Evidence/W64_AQA_QWEN3_ASR_17B_STATIC_QUALIFICATION_20260722T014335Z/evidence.json",
                        "admission_manifest_sha256": "e733f6863ecf6e3cd2d5579cd50c6e8cd35c78739316757633ad70c879edba60",
                        "installation_receipt_sha256": "cd52de9d1c4495d42c007d648dfa0355aa57eec64457cbdf967ba9ef39aa004e",
                    }
                    if static_qualification != expected_static_qualification:
                        errors.append(f"{item.get('package_id')}: static qualification evidence mismatch")
                    if identity.get("license_state") != "APACHE-2.0_ACCEPTED_FOR_COMFY_UI_MAIN_PROJECT_USE":
                        errors.append(f"{item.get('package_id')}: license decision mismatch")
                elif repository_id == "Qwen/Qwen3-Omni-30B-A3B-Thinking":
                    admission = item.get("install_admission", {})
                    omni_receipt = item.get("installation_receipt", {})
                    omni_preflight = item.get("dependency_preflight", {})
                    if state != "INSTALLED_FILE_SET_VERIFIED_ACTIVATION_PENDING":
                        errors.append(f"{item.get('package_id')}: Omni storage install state mismatch")
                    if install.get("artifact_digest") != "46d9695468fac6ff986a683b42df3e8872a01f9e16703ee0772ca4ba2136d480":
                        errors.append(f"{item.get('package_id')}: Omni artifact digest mismatch")
                    if install.get("durable_root") != "/workspace/w64_aqa/models/Qwen3-Omni-30B-A3B-Thinking/2f443cfc4c54b14a815c0e2bb9a9d6cbcd9a748b":
                        errors.append(f"{item.get('package_id')}: Omni durable root mismatch")
                    if identity.get("license_state") != "APACHE-2.0_ACCEPTED_FOR_COMFY_UI_MAIN_PROJECT_USE":
                        errors.append(f"{item.get('package_id')}: Omni license decision mismatch")
                    if qualification.get("state") != "STORAGE_INSTALLED_RUNTIME_GATES_PENDING":
                        errors.append(f"{item.get('package_id')}: Omni qualification state mismatch")
                    for completed_gate in ("pinned_revision", "artifact_hash"):
                        if completed_gate in qualification.get("required_gates", []):
                            errors.append(f"{item.get('package_id')}: completed Omni {completed_gate} gate must be removed")
                    expected_admission = {
                        "manifest_sha256": "46d9695468fac6ff986a683b42df3e8872a01f9e16703ee0772ca4ba2136d480",
                        "target_root": "/workspace/w64_aqa/models/Qwen3-Omni-30B-A3B-Thinking/2f443cfc4c54b14a815c0e2bb9a9d6cbcd9a748b",
                        "source_file_count": 26,
                        "weight_shard_count": 16,
                        "weight_bytes": 63440997640,
                    }
                    if admission != expected_admission:
                        errors.append(f"{item.get('package_id')}: Omni install admission mismatch")
                    expected_omni_receipt = {
                        "remote_path": "/workspace/w64_aqa/models/Qwen3-Omni-30B-A3B-Thinking/2f443cfc4c54b14a815c0e2bb9a9d6cbcd9a748b/.w64_aqa_install_receipt.json",
                        "sha256": "f9fd05a3f2c8379178bd943794d0dc945f81b033b32870f229e832732557668a",
                        "file_count": 27,
                        "total_bytes": 63450501064,
                        "replay": "REUSED_VERIFIED_INSTALL",
                    }
                    if omni_receipt != expected_omni_receipt:
                        errors.append(f"{item.get('package_id')}: Omni installation receipt mismatch")
                    expected_omni_preflight = {
                        "state": "METADATA_ONLY_IMPLEMENTED_EXECUTION_PENDING",
                        "script": "Plan/07_IMPLEMENTATION/scripts/preflight_wave64_qwen3_omni_dependencies.py",
                        "schema": "Plan/08_SCHEMAS/runpod_autonomous_qwen3_omni_dependency_preflight.schema.json",
                        "controls": [
                            "no_library_import",
                            "no_weight_open",
                            "no_tensor",
                            "no_gpu_or_lease",
                            "no_network",
                            "no_process",
                        ],
                    }
                    if omni_preflight != expected_omni_preflight:
                        errors.append(f"{item.get('package_id')}: Omni dependency preflight mismatch")
            else:
                if identity.get("identity_state") != "OFFICIAL_UPSTREAM_IDENTITY_VERIFIED_REVISION_UNPINNED":
                    errors.append(f"{item.get('package_id')}: planned identity state mismatch")
                if source_pin is not None:
                    errors.append(f"{item.get('package_id')}: unpinned package cannot claim source pin")
                if "pinned_revision" not in qualification.get("required_gates", []):
                    errors.append(f"{item.get('package_id')}: pinned revision gate required")
            if not str(identity.get("source_url", "")).startswith("https://huggingface.co/"):
                errors.append(f"{item.get('package_id')}: official source URL required")
            planned.add(repository_id)
    if installed != EXPECTED_INSTALLED:
        errors.append("installed digest inventory mismatch")
    if planned != EXPECTED_PLANNED:
        errors.append("planned official repository inventory mismatch")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory", type=Path)
    args = parser.parse_args()
    data = json.loads(args.inventory.read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("W64_AQA_ROLE_PACKAGE_INVENTORY_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
