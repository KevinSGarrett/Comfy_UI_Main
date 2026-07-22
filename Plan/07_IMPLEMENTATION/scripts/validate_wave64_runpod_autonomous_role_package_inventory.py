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
    "OpenGVLab/InternVL3_5-241B-A28B-HF",
    "OpenGVLab/InternVL3_5-8B",
    "Qwen/Qwen3-Omni-30B-A3B-Thinking",
    "Qwen/Qwen3-ASR-1.7B",
    "Qwen/Qwen3-Coder-Next",
    "Qwen/Qwen3.5-397B-A17B",
}

EXPECTED_PROMOTED = {
    "laion/larger_clap_general": "b35a1ac3fc7cf0ed32822667e85240b0620cba5ed65988c0a707445ef7e593cc",
}

PINNED_PLANNED = {
    "Qwen/Qwen3-ASR-1.7B": "7278e1e70fe206f11671096ffdd38061171dd6e5",
    "Qwen/Qwen3-Omni-30B-A3B-Thinking": "2f443cfc4c54b14a815c0e2bb9a9d6cbcd9a748b",
    "OpenGVLab/InternVL3_5-241B-A28B-HF": "b941ed62ed4e2b711be4271b55034c2c97c57f33",
    "OpenGVLab/InternVL3_5-8B": "9bb6a56ad9cc69db95e2d4eeb15a52bbcac4ef79",
}


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != "wave64.aqa.role_package_inventory.v1":
        errors.append("schema_version mismatch")
    if data.get("scope") != "REPOSITORY_BACKED_STATIC_AND_SCOPED_RUNTIME_EVIDENCE":
        errors.append("scope must bind static and scoped runtime evidence")
    policy = data.get("runtime_policy", {})
    if policy.get("current_pod_remains_authoritative") is not True:
        errors.append("current pod must remain authoritative")
    if policy.get("single_gpu_role_at_a_time") is not True or policy.get("durable_root") != "/workspace":
        errors.append("current-pod residency policy mismatch")
    current_pod = policy.get("current_pod_only", {})
    expected_current_pod = {
        "pod_id": "1q4ji0gg1fkhvt",
        "gpu": "NVIDIA RTX 6000 Ada Generation",
        "physical_vram_mib": 49140,
        "shared_coordinator_required": True,
        "sequential_residency_required": True,
        "cpu_nvme_offload_allowed": True,
        "alternative_hardware_watcher": False,
        "alternative_pod_creation": False,
        "external_inference": False,
    }
    if current_pod != expected_current_pod:
        errors.append("current-pod-only runtime policy mismatch")

    packages = data.get("packages", [])
    ids = [item.get("package_id") for item in packages]
    if len(ids) != len(set(ids)):
        errors.append("package_id values must be unique")
    installed: dict[str, str | None] = {}
    planned: set[str] = set()
    promoted: dict[str, str | None] = {}
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
            if identity.get("repository_id") == "qwen3-vl:4b-instruct-q4_K_M":
                expected_identity = {
                    "display_name": "qwen3-vl:4b-instruct-q4_K_M",
                    "publisher": "Ollama library / Qwen",
                    "repository_id": "qwen3-vl:4b-instruct-q4_K_M",
                    "source_url": "https://registry.ollama.ai/v2/library/qwen3-vl/manifests/4b-instruct-q4_K_M",
                    "identity_state": "OFFICIAL_UPSTREAM_IDENTITY_VERIFIED_REVISION_PINNED",
                    "license_state": "APACHE-2.0_ACCEPTED_FOR_COMFY_UI_MAIN_PROJECT_USE",
                }
                expected_static = {
                    "state": "OFFICIAL_MANIFEST_AND_APACHE_2_0_LICENSE_PASS_RUNTIME_PENDING",
                    "evidence": "Plan/Tracker/Evidence/W64_AQA_QWEN3VL4_OFFICIAL_MANIFEST_IDENTITY_20260722.json",
                    "manifest_sha256": EXPECTED_INSTALLED["qwen3-vl:4b-instruct-q4_K_M"],
                    "config_sha256": "1b50ee65d6560b990272302c6df3026990f58d355bc400a66e4337c60e898876",
                    "model_sha256": "16b83be682148a4d8201dbf720ea7eace5de98b69f63f05e0c908b4d7977ecb5",
                    "license_sha256": "7339fa418c9ad3e8e12e74ad0fd26a9cc4be8703f9c110728a992b193be85cb2",
                    "parameters_sha256": "f6417cb1e26962991f8e875a93f3cb0f92bc9b4955e004881251ccbf934a19d2",
                }
                if identity != expected_identity:
                    errors.append(f"{item.get('package_id')}: Qwen3-VL 4B official identity mismatch")
                if item.get("static_qualification") != expected_static:
                    errors.append(f"{item.get('package_id')}: Qwen3-VL 4B official manifest mismatch")
        elif state == "PROMOTED_EXACT_PACKAGE_IDENTITY_VERIFIED_ACTIVATION_PENDING":
            repository_id = identity.get("repository_id", "")
            source_pin = item.get("source_pin", {})
            supporting_canary = item.get("supporting_runtime_canary", {})
            expected_source_pin = {
                "revision": "ada0c23a36c4e8582805bb38fec3905903f18b41",
                "verified_at_utc": "2026-07-22T05:45:22Z",
                "aggregate_manifest_sha256": "b35a1ac3fc7cf0ed32822667e85240b0620cba5ed65988c0a707445ef7e593cc",
                "file_count": 15,
                "total_bytes": 777702854,
                "weight_sha256": "314eb00cce6ad68d25237b8446b659ccdb136ed4672c1bca470f142f72455026",
            }
            expected_canary = {
                "state": "EXACT_FIXTURE_CUDA_INFERENCE_EMBEDDING_DETERMINISM_AND_PROCESS_EXIT_CLEANUP_PASS_SPEECH_EVENT_GATE_FAIL",
                "control_commit": "245f3a1562e48e0a21496cb29609654ee0554c56",
                "script_sha256": "07691b5c2248c3c46e69a376fd64b53a1a72923aa27d9252f7ad0d569a213873",
                "receipt_sha256": "ad0a53e22275e8467f06cfc13658cd641a7735a13bddd67140f581eb34078910",
                "evidence": "Plan/Tracker/Evidence/W64_AQA_LAION_CLAP_AUDIO_RUNTIME_CANARY_20260722T054522Z/integration_acceptance.json",
                "fixture_sha256": "5a07f0a654499266509453421c3efdc1b2e4ce83b8706e0138ebc4b1d3ad924a",
                "vector_dimension": 512,
                "repeat_max_abs_delta": 0.0,
                "load_seconds": 0.910125382244587,
                "inference_seconds": 0.5741430670022964,
                "peak_used_mib": 1984,
                "process_exit_cleanup_delta_mib": 0,
                "expected_top_label": "a person speaking clearly",
                "observed_top_label": "silence",
            }
            if repository_id != "laion/larger_clap_general":
                errors.append(f"{item.get('package_id')}: unsupported promoted package")
            if identity.get("identity_state") != "OFFICIAL_UPSTREAM_IDENTITY_VERIFIED_REVISION_PINNED":
                errors.append(f"{item.get('package_id')}: promoted identity state mismatch")
            if identity.get("license_state") != "LOCAL_RUNTIME_LICENSE_NOT_REVERIFIED":
                errors.append(f"{item.get('package_id')}: promoted license state mismatch")
            if install.get("artifact_digest") != EXPECTED_PROMOTED.get(repository_id):
                errors.append(f"{item.get('package_id')}: promoted artifact digest mismatch")
            if install.get("durable_root") != "/workspace/ComfyUI/models/audio/embeddings/laion_clap_general":
                errors.append(f"{item.get('package_id')}: promoted durable root mismatch")
            if source_pin != expected_source_pin:
                errors.append(f"{item.get('package_id')}: promoted source pin mismatch")
            if supporting_canary != expected_canary:
                errors.append(f"{item.get('package_id')}: supporting runtime canary mismatch")
            if qualification.get("state") != "IDENTITY_AND_BOUNDED_RUNTIME_PASS_SPEECH_EVENT_AND_BROAD_GATES_PENDING":
                errors.append(f"{item.get('package_id')}: promoted qualification state mismatch")
            if "speech_event_approval" not in authority.get("forbidden", []):
                errors.append(f"{item.get('package_id')}: failed speech gate must remain forbidden")
            promoted[repository_id] = install.get("artifact_digest")
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
                    runtime_canary = item.get("runtime_canary", {})
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
                    if qualification.get("state") != "STATIC_IMPORT_AND_EXACT_FIXTURE_RUNTIME_PASS_BROAD_GATES_PENDING":
                        errors.append(f"{item.get('package_id')}: qualification state mismatch")
                    for completed_gate in (
                        "license_acceptance",
                        "artifact_hash",
                        "capacity",
                        "runtime",
                    ):
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
                    expected_runtime_canary = {
                        "state": "EXACT_FIXTURE_TRANSCRIPTION_AND_PROCESS_EXIT_CLEANUP_PASS",
                        "control_commit": "0854c5b706c4292b96dce62c82895764984a4a41",
                        "script_sha256": "54facb0be9813d4171aee76493a8afa8cb4250762c87f49ac12497700c1e5200",
                        "receipt_sha256": "fcac29d05809997fbeddd913dca5f988713b5b48cc6375ebd1e3207990b43d33",
                        "evidence": "Plan/Tracker/Evidence/W64_AQA_QWEN3_ASR_RUNTIME_CANARY_20260722T035531Z/qwen3_asr_runtime_canary.json",
                        "audio_sha256": "5a07f0a654499266509453421c3efdc1b2e4ce83b8706e0138ebc4b1d3ad924a",
                        "transcript": "Once upon a midnight.",
                        "language": "English",
                        "load_seconds": 10.843007050454617,
                        "inference_seconds": 10.259523160755634,
                        "peak_used_mib": 5656,
                        "process_exit_cleanup_delta_mib": 5,
                        "coordinator_lease_mode": "exclusive",
                    }
                    if runtime_canary != expected_runtime_canary:
                        errors.append(f"{item.get('package_id')}: runtime canary evidence mismatch")
                    if identity.get("license_state") != "APACHE-2.0_ACCEPTED_FOR_COMFY_UI_MAIN_PROJECT_USE":
                        errors.append(f"{item.get('package_id')}: license decision mismatch")
                elif repository_id == "Qwen/Qwen3-Omni-30B-A3B-Thinking":
                    admission = item.get("install_admission", {})
                    omni_receipt = item.get("installation_receipt", {})
                    omni_preflight = item.get("dependency_preflight", {})
                    omni_environment = item.get("dependency_environment", {})
                    omni_import_canary = item.get("import_canary", {})
                    if state != "INSTALLED_FILE_SET_VERIFIED_ACTIVATION_PENDING":
                        errors.append(f"{item.get('package_id')}: Omni storage install state mismatch")
                    if install.get("artifact_digest") != "46d9695468fac6ff986a683b42df3e8872a01f9e16703ee0772ca4ba2136d480":
                        errors.append(f"{item.get('package_id')}: Omni artifact digest mismatch")
                    if install.get("durable_root") != "/workspace/w64_aqa/models/Qwen3-Omni-30B-A3B-Thinking/2f443cfc4c54b14a815c0e2bb9a9d6cbcd9a748b":
                        errors.append(f"{item.get('package_id')}: Omni durable root mismatch")
                    if identity.get("license_state") != "APACHE-2.0_ACCEPTED_FOR_COMFY_UI_MAIN_PROJECT_USE":
                        errors.append(f"{item.get('package_id')}: Omni license decision mismatch")
                    if qualification.get("state") != "STORAGE_DEPENDENCY_IMPORT_GATES_PASS_RUNTIME_GATES_PENDING":
                        errors.append(f"{item.get('package_id')}: Omni qualification state mismatch")
                    for completed_gate in ("pinned_revision", "artifact_hash", "dependency_environment", "import_canary"):
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
                        "state": "CONFIG_IDENTITY_PASS_DEPENDENCY_ACTION_REQUIRED",
                        "evidence": "Plan/Tracker/Evidence/W64_AQA_QWEN3_OMNI_30B_A3B_DEPENDENCY_PREFLIGHT_20260722T022053Z/evidence.json",
                        "receipt_sha256": "b9a8d357d385f16a38d4fe36b3bd8930b220548c77dc227c780d8c4de513ca38",
                        "gaps": [
                            "QWEN_OMNI_UTILS_DISTRIBUTION_MISSING",
                            "INSTALLED_TRANSFORMERS_LACKS_QWEN3_OMNI_SUPPORT",
                        ],
                    }
                    if omni_preflight != expected_omni_preflight:
                        errors.append(f"{item.get('package_id')}: Omni dependency preflight mismatch")
                    expected_omni_environment = {
                        "state": "INSTALLED_IMPORT_VERIFIED_RUNTIME_PENDING",
                        "root": "/workspace/w64_aqa/environments/Qwen3-Omni-30B-A3B-Thinking/transformers-5.2.0-qwen-omni-utils-0.0.9-py3.12.13-cu124/a19d160721dfb74cf89bc70eebec10f45b2e6f58b7a109726d658db7d361277c",
                        "lock_sha256": "a19d160721dfb74cf89bc70eebec10f45b2e6f58b7a109726d658db7d361277c",
                        "receipt_sha256": "d89ec8ba5588e8ba07f76522c74bfbfe51284c55baf934ab7f4729fed298deb8",
                        "tree_sha256": "2ae7708993cab848861688ae1b89a2233d61fa02b49e1c14bf51b188a2dd59c5",
                        "distribution_count": 75,
                        "pip_check": "PASS_75_PACKAGES_COMPATIBLE",
                        "active_environment_unchanged": True,
                        "replay": "REUSED_VERIFIED_ENVIRONMENT",
                        "evidence": "Plan/Tracker/Evidence/W64_AQA_QWEN3_OMNI_ENVIRONMENT_BUILD_20260722T024800Z/evidence.json",
                    }
                    if omni_environment != expected_omni_environment:
                        errors.append(f"{item.get('package_id')}: Omni dependency environment admission mismatch")
                    expected_omni_import_canary = {
                        "state": "IMPORT_ONLY_CLASS_RESOLUTION_PASS_RUNTIME_PENDING",
                        "commit": "6a1fa04b",
                        "script_sha256": "01a9107601db6580e714d4be6425125b1d1e58b8d62bc65d8b289ddcd0a5a5c8",
                        "admission_sha256": "c25935363d2e641d584a7a0fa56e45be3048a1404be315f8c93bda3cf191d2c0",
                        "receipt_sha256": "213cdc57cf72a537ff979767ff08599d9cd8ff717518bc9f8762c696d4b2e47c",
                        "post_canary_tree_sha256": "2ae7708993cab848861688ae1b89a2233d61fa02b49e1c14bf51b188a2dd59c5",
                        "evidence": "Plan/Tracker/Evidence/W64_AQA_QWEN3_OMNI_IMPORT_CANARY_20260722T025500Z/evidence.json",
                    }
                    if omni_import_canary != expected_omni_import_canary:
                        errors.append(f"{item.get('package_id')}: Omni import canary evidence mismatch")
                elif repository_id == "OpenGVLab/InternVL3_5-241B-A28B-HF":
                    expected_source_pin = {
                        "revision": "b941ed62ed4e2b711be4271b55034c2c97c57f33",
                        "verified_at_utc": "2026-07-22T03:00:00Z",
                        "native_hf_format": True,
                        "source_manifest_sha256": "3011b54a9235a92b161253b400f9ffa9726310c76f7b4c8f9d89335562b03413",
                        "source_file_count": 136,
                        "source_total_bytes": 481433908402,
                        "weight_shard_count": 97,
                        "weight_bytes": 481403989568,
                        "evidence": "Plan/Tracker/Evidence/W64_AQA_INTERNVL35_241B_A28B_NATIVE_HF_SOURCE_QUALIFICATION_20260722T030000Z.json",
                    }
                    if source_pin != expected_source_pin:
                        errors.append(f"{item.get('package_id')}: native HF source pin mismatch")
                    if identity.get("license_state") != "WEIGHTS_APACHE-2.0_AND_PROJECT_CODE_MIT_ACCEPTED_FOR_COMFY_UI_MAIN_PROJECT_USE":
                        errors.append(f"{item.get('package_id')}: independent juror license decision mismatch")
                    expected_quantized_route = {
                        "state": "COMMUNITY_QUANT_PINNED_HEADER_COMPATIBILITY_PASS_DOWNLOAD_NOT_ADMITTED",
                        "model_repository_id": "mradermacher/InternVL3_5-241B-A28B-i1-GGUF",
                        "model_revision": "a5d7824f8e2b9ea813bab7aad36bd2b505ac2f74e",
                        "quantization": "i1-IQ4_XS",
                        "multipart_concatenation_required": True,
                        "model_part_count": 3,
                        "model_part_bytes": [41875931136, 41875931136, 41532046688],
                        "model_part_sha256": [
                            "6b40342482ce538351042b4b5fde2ebc30cb89861cac0c056a42dc2015731c25",
                            "3b0f6f1952ae3742d73a9a696acd43745ac09df279c7d52bf38f6c50d55a1479",
                            "b919c1e516368bd1e3ea7a12bfbc1ebfb638e8fa003fe17e771c4d7aaf09485a",
                        ],
                        "model_total_bytes": 125283908960,
                        "model_header": {
                            "general_architecture": "qwen3moe",
                            "gguf_version": 3,
                            "tensor_count": 1131,
                            "metadata_count": 53,
                            "metadata_end_offset": 5930811,
                        },
                        "projector_repository_id": "mradermacher/InternVL3_5-241B-A28B-GGUF",
                        "projector_revision": "cba880f5aab84c74eaeed388c2209346b76c3bf8",
                        "projector_filename": "InternVL3_5-241B-A28B.mmproj-Q8_0.gguf",
                        "projector_bytes": 5976491584,
                        "projector_sha256": "15d6aa2ad647525f72c954f8825e3973be6d78849ba05f07e4413da957baf126",
                        "projector_header": {
                            "general_architecture": "clip",
                            "general_type": "mmproj",
                            "projector_type": "internvl",
                            "image_size": 448,
                            "patch_size": 14,
                            "projection_dim": 4096,
                        },
                        "combined_bytes": 131260400544,
                        "evidence": "Plan/Tracker/Evidence/W64_AQA_INTERNVL35_241B_GGUF_STATIC_ADMISSION_20260722T130625Z.json",
                    }
                    if item.get("candidate_quantized_route") != expected_quantized_route:
                        errors.append(f"{item.get('package_id')}: independent juror quantized route mismatch")
                    loader_preflight = item.get("loader_preflight", {})
                    if loader_preflight.get("revision") != "e8e6c7af2456fd50bb62f7a2bbd642e6fb14ae77":
                        errors.append(f"{item.get('package_id')}: independent juror loader pin mismatch")
                    if loader_preflight.get("model_architecture") != "qwen3moe" or loader_preflight.get("projector_type") != "internvl":
                        errors.append(f"{item.get('package_id')}: independent juror header identifiers mismatch")
                    if loader_preflight.get("internvl_3_5_explicitly_documented") is not False:
                        errors.append(f"{item.get('package_id')}: InternVL3.5 support must remain unproven")
                    if loader_preflight.get("runtime_binary_present_on_pod") is not False:
                        errors.append(f"{item.get('package_id')}: absent pinned loader runtime mismatch")
                    storage = item.get("storage_admission", {})
                    expected_storage = {
                        "state": "DOWNLOAD_HELD_EXACT_LIVE_FREE_QUOTA_AND_RESERVE_GATES_FAIL",
                        "network_volume_id": "o9qv2ld91c",
                        "network_volume_size_gb_control_plane": 1000,
                        "exact_live_free_quota_known": False,
                        "candidate_bytes": 131260400544,
                        "candidate_gib": 122.24577417969704,
                        "minimum_post_install_reserve_gib": 50.0,
                        "minimum_free_before_download_gib": 172.24577417969704,
                        "latest_conservative_free_reserve_gib": 53.335322,
                        "shortfall_to_artifact_gib": 68.91045217969705,
                        "shortfall_to_artifact_plus_reserve_gib": 118.91045217969705,
                        "download_started": False,
                        "evidence": "Plan/Tracker/Evidence/W64_AQA_INTERNVL35_241B_GGUF_STATIC_ADMISSION_20260722T130625Z.json",
                    }
                    if storage != expected_storage:
                        errors.append(f"{item.get('package_id')}: independent juror storage admission mismatch")
                    if qualification.get("state") != "NATIVE_SOURCE_AND_GGUF_HEADER_IDENTIFIERS_PINNED_DOWNLOAD_HELD_STORAGE_BUILD_AND_RUNTIME_GATES_PENDING":
                        errors.append(f"{item.get('package_id')}: independent juror qualification state mismatch")
                    for completed_gate in ("pinned_revision", "license_acceptance", "remote_code_review"):
                        if completed_gate in qualification.get("required_gates", []):
                            errors.append(f"{item.get('package_id')}: completed or avoided {completed_gate} gate remains open")
                    for required_gate in ("exact_live_free_quota", "minimum_50_gib_post_install_reserve", "pinned_loader_build", "multipart_concatenation_hash"):
                        if required_gate not in qualification.get("required_gates", []):
                            errors.append(f"{item.get('package_id')}: independent juror {required_gate} gate required")
                    if "trust_remote_code" not in authority.get("forbidden", []):
                        errors.append(f"{item.get('package_id')}: native HF route must forbid remote code")
                    if "download_without_storage_admission" not in authority.get("forbidden", []):
                        errors.append(f"{item.get('package_id')}: storage-unadmitted download must be forbidden")
                elif repository_id == "OpenGVLab/InternVL3_5-8B":
                    expected_source_pin = {
                        "revision": "9bb6a56ad9cc69db95e2d4eeb15a52bbcac4ef79",
                        "verified_at_utc": "2026-07-22T12:10:57Z",
                        "custom_code_required": True,
                        "source_file_count": 24,
                        "source_total_bytes": 17072800269,
                        "weight_shard_count": 4,
                        "weight_bytes": 17056729432,
                        "storage_audit_sha256": "410f3673d769f25c3a69676676863cabceb550e340bc384855bed2c429dcce31",
                    }
                    if state != "INSTALLED_FILE_SET_VERIFIED_ACTIVATION_PENDING":
                        errors.append(f"{item.get('package_id')}: provisional InternVL install state mismatch")
                    if source_pin != expected_source_pin:
                        errors.append(f"{item.get('package_id')}: provisional InternVL source pin mismatch")
                    if install.get("artifact_digest") != expected_source_pin["storage_audit_sha256"]:
                        errors.append(f"{item.get('package_id')}: provisional InternVL audit digest mismatch")
                    if install.get("durable_root") != "/workspace/models/visual_critics/internvl3_5_8b_bf16":
                        errors.append(f"{item.get('package_id')}: provisional InternVL root mismatch")
                    if identity.get("license_state") != "PACKAGE_AND_WEIGHTS_APACHE_2_0_INTERNVL_CODE_MIT_FASTCHAT_DERIVATION_APACHE_2_0_ACCEPTED_FOR_COMFY_UI_MAIN_PROJECT_USE":
                        errors.append(f"{item.get('package_id')}: provisional InternVL license state mismatch")
                    expected_license = {
                        "state": "PROJECT_USE_ACCEPTED_NOTICE_RETENTION_REQUIRED",
                        "evidence": "Plan/Tracker/Evidence/W64_AQA_INTERNVL35_8B_LICENSE_RECONCILIATION_20260722T125200Z/integration_acceptance.json",
                        "standalone_license_file_in_snapshot": False,
                        "package_readme_sha256": "47383e9746907dbfabfcad9c786aab81e43586b5e4b0bb07ad893d8b58f3b1e9",
                        "internvl_mit_license_sha256": "8f03d25fbcffafa2254d4d1414bf2a38423a966006b4a6964ee21f728d610bff",
                        "fastchat_apache_2_0_license_sha256": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
                    }
                    if item.get("license_qualification") != expected_license:
                        errors.append(f"{item.get('package_id')}: provisional InternVL license qualification mismatch")
                    if qualification.get("state") != "EXACT_STORAGE_STATIC_CODE_LICENSE_AND_IMMUTABLE_ENVIRONMENT_PASS_IMPORT_CANARY_ADMITTED_EXECUTION_HELD_RUNTIME_GATES_PENDING":
                        errors.append(f"{item.get('package_id')}: provisional InternVL qualification mismatch")
                    static_review = item.get("static_code_review", {})
                    if static_review.get("state") != "AST_AND_MANUAL_SEMANTIC_REVIEW_PASS_WITH_FAIL_CLOSED_QUALITY_GATES":
                        errors.append(f"{item.get('package_id')}: provisional InternVL static review mismatch")
                    if static_review.get("reviewer_script_sha256") != "2b4fa339162decd1a88ff5b47d7819dfe685410e60144c655666ad128e19c3da":
                        errors.append(f"{item.get('package_id')}: provisional InternVL reviewer script mismatch")
                    if static_review.get("remote_receipt_sha256") != "fef7ea03da4388acfb38b5d999d03396b0b53c9635978a669e05af92b462bd83":
                        errors.append(f"{item.get('package_id')}: provisional InternVL static review receipt mismatch")
                    if static_review.get("quality_findings") != [
                        "FLASH_ATTN_IMPORT_CATCHES_BROAD_EXCEPTION",
                        "TOKEN_COUNT_MISMATCH_FALLBACK_USES_CHAINED_ADVANCED_INDEX_ASSIGNMENT",
                    ]:
                        errors.append(f"{item.get('package_id')}: provisional InternVL quality findings mismatch")
                    preflight = item.get("dependency_preflight", {})
                    if preflight.get("state") != "BASE_ENVIRONMENT_INCOMPATIBLE_VERIFIED_OMNI_ENVIRONMENT_REUSE_CANDIDATE_NEEDS_TWO_ADDONS":
                        errors.append(f"{item.get('package_id')}: provisional InternVL dependency preflight mismatch")
                    if preflight.get("reuse_candidate", {}).get("missing_required_addons") != ["timm", "einops"]:
                        errors.append(f"{item.get('package_id')}: provisional InternVL reuse candidate gaps mismatch")
                    if preflight.get("import_attempted") is not False or preflight.get("model_load_attempted") is not False:
                        errors.append(f"{item.get('package_id')}: provisional InternVL preflight must remain static")
                    environment = item.get("dependency_environment", {})
                    expected_environment = {
                        "state": "IMMUTABLE_LAYERED_ENVIRONMENT_BUILT_METADATA_CLOSURE_PASS_IMPORT_PENDING",
                        "root": "/workspace/w64_aqa/environments/InternVL3_5-8B/transformers-5.2.0-timm-1.0.28-einops-0.8.2-py3.12.13-cu124/9f7317aef1cf2beb0f67bc879b8d3676d542fb691dc61d337aff268474cda5a6",
                        "lock_sha256": "9f7317aef1cf2beb0f67bc879b8d3676d542fb691dc61d337aff268474cda5a6",
                        "admission_sha256": "5ef6117658e1555133e67bb5c536667676e02ef64d395530d2c535d087a071e4",
                        "manifest_sha256": "429ecdddf96132ee46dc1b21d14d95d1ed6f83268a579a1e75db9291807e6ce7",
                        "installed_tree_sha256": "1191178fb3f8ff148b7330767f8d0e1dd0f3418cfacd29d0f3ce19490f6895b7",
                        "installed_file_count": 345,
                        "installed_bytes": 9389082,
                        "base_environment_mutated": False,
                        "metadata_validation": {
                            "state": "PASS_75_BASE_2_OVERLAY_5_REQUIREMENTS_ZERO_ERRORS",
                            "receipt": "/workspace/wave64_evidence/internvl35_8b_layered_environment_metadata_20260722T123557Z.json",
                            "receipt_sha256": "e3fbd176c84114f5360f46cf5986e2514682539414f47dc09638da75e9ddc711",
                        },
                        "import_attempted": False,
                        "model_load_attempted": False,
                        "evidence": "Plan/Tracker/Evidence/W64_AQA_INTERNVL35_8B_DEPENDENCY_OVERLAY_20260722T123557Z/integration_acceptance.json",
                    }
                    if environment != expected_environment:
                        errors.append(f"{item.get('package_id')}: provisional InternVL dependency environment mismatch")
                    expected_import_canary = {
                        "state": "EXACT_ADMISSION_READY_EXECUTION_HELD_BY_FOREIGN_COORDINATOR_RECOVERY",
                        "admission": "Plan/10_REGISTRIES/wave64_internvl35_8b_import_canary_admission.json",
                        "admission_sha256": "2f723b1b9341087553fb3abe44c83060248aa8316f065997371d54d93589f191",
                        "lock_sha256": "02e6f2566da9e5ab2002ac15d456c32e8770f72102c21b9b8f6b9eef413c55d9",
                        "runner_sha256": "d567bafa96710cd6824d6fa05884b8fe68cacb3295f13170815ae69a3fc3cf82",
                        "coordinator_mode": "RECOVERY_REQUIRED",
                        "foreign_lease_id": "lease_f31c0165ee8f4c9bb31e5ef96ef87d22",
                        "executed": False,
                        "evidence": "Plan/Tracker/Evidence/W64_AQA_INTERNVL35_8B_IMPORT_CANARY_ADMISSION_20260722T124343Z/integration_acceptance.json",
                    }
                    if item.get("import_canary") != expected_import_canary:
                        errors.append(f"{item.get('package_id')}: provisional InternVL import admission mismatch")
                    if "full_remote_code_review" in qualification.get("required_gates", []):
                        errors.append(f"{item.get('package_id')}: completed static review gate must be removed")
                    if "dependency_environment" in qualification.get("required_gates", []):
                        errors.append(f"{item.get('package_id')}: completed dependency environment gate must be removed")
                    if "license_acceptance" in qualification.get("required_gates", []):
                        errors.append(f"{item.get('package_id')}: completed license gate must be removed")
                    if "import_canary" not in qualification.get("required_gates", []):
                        errors.append(f"{item.get('package_id')}: provisional InternVL import gate required")
                    if "independent_juror_substitution" not in authority.get("forbidden", []):
                        errors.append(f"{item.get('package_id')}: provisional InternVL cannot substitute for the juror")
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
    if promoted != EXPECTED_PROMOTED:
        errors.append("promoted exact package inventory mismatch")
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
