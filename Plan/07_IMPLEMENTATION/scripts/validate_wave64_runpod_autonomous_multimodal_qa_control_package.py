#!/usr/bin/env python3
"""Validate the additive W64-AQA project-control package."""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PROGRAM = "W64-AQA"
EXPECTED_IDS = {f"W64-AQA-{number:03d}" for number in range(1, 17)}

PATHS = {
    "master": ROOT
    / "Plan/00_PROJECT_CONTROL/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_AND_CORRECTION_MASTER_PLAN.md",
    "architecture": ROOT
    / "Plan/02_TARGET_ARCHITECTURE/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_CONTROL_PLANE_ARCHITECTURE.md",
    "items": ROOT
    / "Plan/Items/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_ITEM_ROWS.csv",
    "tracker": ROOT
    / "Plan/Tracker/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_TRACKER_ROWS.csv",
    "requirements": ROOT
    / "Plan/Tracker/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_REQUIREMENTS.json",
    "evidence": ROOT
    / "Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_EXTERNAL_STATE_RECONCILIATION_20260721.json",
    "capacity_evidence": ROOT
    / "Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_CAPACITY_OPTIONS_20260721.json",
    "phase_lease_shadow_evidence": ROOT
    / "Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_PHASE_LEASE_SHADOW_20260721.json",
    "operations": ROOT
    / "Plan/Instructions/Operations/RUNPOD_AUTONOMOUS_MULTIMODAL_QA_OPERATING_PROTOCOL.md",
    "qa": ROOT
    / "Plan/Instructions/QA/RUNPOD_AUTONOMOUS_MULTIMODAL_QA_AND_BOUNDED_CORRECTION_PROTOCOL.md",
    "registry": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_multimodal_qa_role_registry.json",
    "schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_multimodal_qa_decision.schema.json",
    "job_contract_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_multimodal_job_contract.schema.json",
    "job_contract_compiler": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_multimodal_job_contract.py",
    "phase_lease_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_multimodal_phase_lease.schema.json",
    "phase_lease_controller": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_phase_lease_controller.py",
    "image_measurement_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_image_measurement.schema.json",
    "image_measurement": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/measure_wave64_runpod_autonomous_image_quality.py",
    "video_measurement_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_video_measurement.schema.json",
    "video_measurement": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/measure_wave64_runpod_autonomous_video_quality.py",
    "audio_measurement_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_audio_measurement.schema.json",
    "audio_measurement": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/measure_wave64_runpod_autonomous_audio_quality.py",
    "mask_measurement_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_mask_measurement.schema.json",
    "mask_measurement": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/measure_wave64_runpod_autonomous_mask_quality.py",
    "tool_gateway_request_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_tool_gateway_request.schema.json",
    "tool_gateway_decision_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_tool_gateway_decision.schema.json",
    "tool_gateway_policy": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_tool_gateway_policy.json",
    "tool_gateway": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_runpod_autonomous_tool_gateway.py",
    "workflow_patch_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_workflow_patch.schema.json",
    "workflow_validation_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_workflow_validation.schema.json",
    "workflow_patch_policy": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_workflow_patch_policy.json",
    "workflow_validator": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_runpod_autonomous_workflow.py",
    "correction_attempt_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_correction_attempt.schema.json",
    "correction_state_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_correction_state.schema.json",
    "correction_policy": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_correction_policy.py",
}

SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\bgh[opusr]_[A-Za-z0-9]{20,}\b"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "runpod_bearer": re.compile(r"(?i)bearer\s+[A-Za-z0-9_-]{24,}"),
}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def collect_errors() -> list[str]:
    errors: list[str] = []
    missing = [str(path.relative_to(ROOT)) for path in PATHS.values() if not path.is_file()]
    if missing:
        return [f"missing required file: {path}" for path in missing]

    try:
        items = load_csv(PATHS["items"])
        tracker = load_csv(PATHS["tracker"])
        requirements = load_json(PATHS["requirements"])
        evidence = load_json(PATHS["evidence"])
        capacity_evidence = load_json(PATHS["capacity_evidence"])
        phase_lease_shadow_evidence = load_json(PATHS["phase_lease_shadow_evidence"])
        registry = load_json(PATHS["registry"])
        schema = load_json(PATHS["schema"])
        job_contract_schema = load_json(PATHS["job_contract_schema"])
        phase_lease_schema = load_json(PATHS["phase_lease_schema"])
        image_measurement_schema = load_json(PATHS["image_measurement_schema"])
        video_measurement_schema = load_json(PATHS["video_measurement_schema"])
        audio_measurement_schema = load_json(PATHS["audio_measurement_schema"])
        mask_measurement_schema = load_json(PATHS["mask_measurement_schema"])
        tool_gateway_request_schema = load_json(PATHS["tool_gateway_request_schema"])
        tool_gateway_decision_schema = load_json(PATHS["tool_gateway_decision_schema"])
        tool_gateway_policy = load_json(PATHS["tool_gateway_policy"])
        workflow_patch_schema = load_json(PATHS["workflow_patch_schema"])
        workflow_validation_schema = load_json(PATHS["workflow_validation_schema"])
        workflow_patch_policy = load_json(PATHS["workflow_patch_policy"])
        correction_attempt_schema = load_json(PATHS["correction_attempt_schema"])
        correction_state_schema = load_json(PATHS["correction_state_schema"])
    except (csv.Error, json.JSONDecodeError, OSError) as exc:
        return [f"parse failure: {exc}"]

    item_ids = {row.get("Item_ID", "") for row in items}
    tracker_ids = {row.get("Tracker_ID", "") for row in tracker}
    requirement_ids = {entry.get("id", "") for entry in requirements.get("requirements", [])}
    for label, observed in (
        ("items", item_ids),
        ("tracker", tracker_ids),
        ("requirements", requirement_ids),
    ):
        if observed != EXPECTED_IDS:
            errors.append(
                f"{label} ID parity failure: missing={sorted(EXPECTED_IDS - observed)} "
                f"extra={sorted(observed - EXPECTED_IDS)}"
            )

    if {row.get("Item_ID") for row in tracker} != EXPECTED_IDS:
        errors.append("tracker Item_ID references do not match the W64-AQA item set")

    json_docs = (
        requirements,
        evidence,
        capacity_evidence,
        phase_lease_shadow_evidence,
        registry,
    )
    for document in json_docs:
        if document.get("program_id") != PROGRAM:
            errors.append("JSON document has the wrong program_id")

    runtime = registry.get("runtime_policy", {})
    expected_limits = {
        "max_repair_attempts_per_defect": 2,
        "max_total_generation_attempts": 4,
        "max_no_progress_cycles": 2,
    }
    for key, expected in expected_limits.items():
        if runtime.get(key) != expected:
            errors.append(f"registry {key} must equal {expected}")
    if runtime.get("generation_host") != "runpod_only":
        errors.append("registry must bind generation_host to runpod_only")
    if runtime.get("ec2_forbidden") is not True:
        errors.append("registry must explicitly forbid EC2")
    if runtime.get("phase_safe_exclusive_gpu") is not True:
        errors.append("registry must require phase-safe exclusive GPU use")
    if runtime.get("primary_pod_first_for_every_role") is not True:
        errors.append("registry must target every role to the primary pod first")
    if runtime.get("external_inference_forbidden") is not True:
        errors.append("registry must forbid external inference")
    one_pod = runtime.get("one_pod_capacity_policy", {})
    preferred = one_pod.get("preferred_profile", {})
    fallback = one_pod.get("performance_fallback_profile", {})
    if preferred.get("gpu_type") != "NVIDIA A40" or preferred.get("gpu_count") != 2:
        errors.append("preferred one-pod profile must be 2x NVIDIA A40")
    if preferred.get("aggregate_vram_is_single_allocation") is not False:
        errors.append("2x A40 aggregate VRAM must not be treated as one allocation")
    if fallback.get("gpu_type") != "NVIDIA RTX PRO 6000 Blackwell Server Edition":
        errors.append("one-pod performance fallback must be RTX PRO 6000 Blackwell Server")
    if one_pod.get("old_pod_stops_only_after_candidate_acceptance") is not True:
        errors.append("current pod must remain until candidate acceptance")
    burst = runtime.get("secondary_burst_policy", {})
    if burst.get("default_power_state") != "STOPPED":
        errors.append("secondary burst pod must be stopped by default")
    if burst.get("shared_vram_assumed") is not False:
        errors.append("secondary burst policy must not assume cross-pod shared VRAM")

    roles = {entry.get("role_id"): entry for entry in registry.get("roles", [])}
    required_roles = {
        "W64-AQA-ROLE-GENERATION",
        "W64-AQA-ROLE-DETERMINISTIC",
        "W64-AQA-ROLE-STRICT-VISUAL",
        "W64-AQA-ROLE-FAST-TRIAGE",
        "W64-AQA-ROLE-TEXT-PLANNER",
        "W64-AQA-ROLE-CONTROLLER",
        "W64-AQA-ROLE-PRIMARY-VISUAL",
        "W64-AQA-ROLE-INDEPENDENT-JUROR",
        "W64-AQA-ROLE-AUDIO-SEMANTIC",
        "W64-AQA-ROLE-WORKFLOW-ENGINEER",
        "W64-AQA-ROLE-GOLDEN-MASK",
        "W64-AQA-ROLE-SENIOR-ARBITER",
    }
    if not required_roles.issubset(roles):
        errors.append(f"missing roles: {sorted(required_roles - roles.keys())}")

    strict = roles.get("W64-AQA-ROLE-STRICT-VISUAL", {})
    if strict.get("model") != "qwen2.5vl:32b":
        errors.append("current strict visual role must bind qwen2.5vl:32b")
    if strict.get("product_approval_sufficient") is not False:
        errors.append("strict reviewer alone must not be sufficient for approval")

    triage = roles.get("W64-AQA-ROLE-FAST-TRIAGE", {})
    if triage.get("product_approval_sufficient") is not False:
        errors.append("triage role must not have product approval authority")
    if "PASS_PRODUCT" not in triage.get("forbidden_decisions", []):
        errors.append("triage role must explicitly forbid PASS_PRODUCT")

    arbiter = roles.get("W64-AQA-ROLE-SENIOR-ARBITER", {})
    if arbiter.get("deployment_target") != "primary_one_pod_only":
        errors.append("senior arbiter must target the one primary pod")
    if arbiter.get("operational") is not False:
        errors.append("unqualified senior arbiter must not be operational")

    workflow = roles.get("W64-AQA-ROLE-WORKFLOW-ENGINEER", {})
    if workflow.get("proposal_only") is not True:
        errors.append("workflow engineer must be proposal-only")

    if tool_gateway_policy.get("decision_only") is not True:
        errors.append("tool gateway must remain decision-only until a separate executor qualifies")
    if tool_gateway_policy.get("external_inference_allowed") is not False:
        errors.append("tool gateway must forbid external inference")
    forbidden_actions = set(tool_gateway_policy.get("forbidden_action_types", []))
    required_forbidden_actions = {"shell", "git", "cloud", "tracker_write", "promotion", "secret_read", "arbitrary_network"}
    if not required_forbidden_actions.issubset(forbidden_actions):
        errors.append("tool gateway forbidden action coverage is incomplete")
    workflow_actions = {
        action_id for action_id, action in tool_gateway_policy.get("allowed_actions", {}).items()
        if "W64-AQA-ROLE-WORKFLOW-ENGINEER" in action.get("roles", [])
    }
    if {"candidate_write", "evidence_append", "shadow_generation_submit"} & workflow_actions:
        errors.append("workflow engineer must not write candidates/evidence or submit generation")
    if workflow_patch_policy.get("copy_on_write_required") is not True:
        errors.append("workflow patching must be copy-on-write")
    if workflow_patch_policy.get("graph_mutation_allowed") is not False:
        errors.append("workflow graph mutation must remain forbidden")
    if workflow_patch_policy.get("threshold_mutation_allowed") is not False:
        errors.append("workflow threshold mutation must remain forbidden")

    modalities = set(schema.get("properties", {}).get("modality", {}).get("enum", []))
    required_modalities = {"image", "video", "audio", "av", "mask", "workflow"}
    if modalities != required_modalities:
        errors.append("decision schema modality coverage is incomplete")

    all_text = "\n".join(path.read_text(encoding="utf-8") for path in PATHS.values())
    required_phrases = (
        "Qwen3-Coder-Next",
        "Qwen3-Omni",
        "Qwen3-ASR",
        "Qwen3.5-397B",
        "Qwen3.5-122B",
        "InternVL3.5-241B",
        "InternVL",
        "golden-mask",
        "MaskFactory",
        "workflow",
        "two repair attempts",
        "four total generation attempts",
        "two no-progress",
        "EC2",
        "RunPod",
        "A40",
        "RTX A6000",
    )
    lowered = all_text.lower()
    for phrase in required_phrases:
        if phrase.lower() not in lowered:
            errors.append(f"required cross-surface concept missing: {phrase}")

    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(all_text):
            errors.append(f"possible secret literal detected: {name}")

    try:
        import jsonschema

        jsonschema.Draft7Validator.check_schema(schema)
        jsonschema.Draft7Validator.check_schema(job_contract_schema)
        jsonschema.Draft7Validator.check_schema(phase_lease_schema)
        jsonschema.Draft7Validator.check_schema(image_measurement_schema)
        jsonschema.Draft7Validator.check_schema(video_measurement_schema)
        jsonschema.Draft7Validator.check_schema(audio_measurement_schema)
        jsonschema.Draft7Validator.check_schema(mask_measurement_schema)
        jsonschema.Draft7Validator.check_schema(tool_gateway_request_schema)
        jsonschema.Draft7Validator.check_schema(tool_gateway_decision_schema)
        jsonschema.Draft7Validator.check_schema(workflow_patch_schema)
        jsonschema.Draft7Validator.check_schema(workflow_validation_schema)
        jsonschema.Draft7Validator.check_schema(correction_attempt_schema)
        jsonschema.Draft7Validator.check_schema(correction_state_schema)
    except ImportError:
        pass
    except Exception as exc:  # pragma: no cover - library supplies exact detail
        errors.append(f"decision schema invalid: {exc}")

    return errors


def main() -> int:
    errors = collect_errors()
    result = {
        "status": "PASS" if not errors else "FAIL",
        "classification": (
            "W64_AQA_CONTROL_PACKAGE_VALID" if not errors else "W64_AQA_CONTROL_PACKAGE_INVALID"
        ),
        "program_id": PROGRAM,
        "validated_files": [str(path.relative_to(ROOT)).replace("\\", "/") for path in PATHS.values()],
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
