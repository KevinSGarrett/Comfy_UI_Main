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
    "phase_lease_runtime_canary_evidence": ROOT
    / "Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_PHASE_LEASE_RUNTIME_CANARY_20260721T213703Z.json",
    "strict_model_admission_hold_evidence": ROOT
    / "Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_STRICT_MODEL_ADMISSION_HOLD_20260721T215000Z.json",
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
    "image_shadow_evidence_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_image_shadow_evidence.schema.json",
    "image_shadow_evidence_producer": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_image_shadow_evidence.py",
    "image_shadow_evidence": ROOT
    / "Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_IMAGE_SHADOW_20260721T223341Z.json",
    "video_measurement_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_video_measurement.schema.json",
    "video_measurement": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/measure_wave64_runpod_autonomous_video_quality.py",
    "video_shadow_evidence_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_video_shadow_evidence.schema.json",
    "video_shadow_evidence_producer": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_video_shadow_evidence.py",
    "video_shadow_evidence": ROOT
    / "Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_VIDEO_SHADOW_20260721T224034Z.json",
    "audio_measurement_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_audio_measurement.schema.json",
    "audio_measurement": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/measure_wave64_runpod_autonomous_audio_quality.py",
    "audio_shadow_evidence_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_audio_shadow_evidence.schema.json",
    "audio_shadow_evidence_producer": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_audio_shadow_evidence.py",
    "audio_shadow_evidence": ROOT
    / "Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_AUDIO_SHADOW_20260721T221732Z.json",
    "av_shadow_evidence_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_av_shadow_evidence.schema.json",
    "av_shadow_evidence_producer": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_av_shadow_evidence.py",
    "av_shadow_evidence": ROOT
    / "Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_AV_SHADOW_20260721T222452Z.json",
    "mask_measurement_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_mask_measurement.schema.json",
    "mask_measurement": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/measure_wave64_runpod_autonomous_mask_quality.py",
    "maskfactory_consumer_contract_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_maskfactory_consumer_contract.schema.json",
    "maskfactory_consumer_contract_compiler": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_maskfactory_consumer_contract.py",
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
    "evidence_bundle_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_evidence_bundle.schema.json",
    "promotion_transaction_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_promotion_transaction.schema.json",
    "evidence_bundle_compiler": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/compile_and_replay_wave64_runpod_autonomous_evidence_bundle.py",
    "role_qualification_report_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_role_qualification_report.schema.json",
    "role_qualification_certificate_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_role_qualification_certificate.schema.json",
    "role_drift_decision_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_role_drift_decision.schema.json",
    "role_qualification_compiler": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/compile_and_evaluate_wave64_runpod_autonomous_role_qualification.py",
    "migration_event_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_one_pod_migration_event.schema.json",
    "migration_state_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_one_pod_migration_state.schema.json",
    "migration_policy": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_one_pod_migration_policy.json",
    "migration_controller": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_one_pod_migration_controller.py",
    "reviewer_observation_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_reviewer_observation.schema.json",
    "review_authority_decision_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_review_authority_decision.schema.json",
    "review_authority_evaluator": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_runpod_autonomous_review_authority.py",
    "review_disagreement_decision_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_review_disagreement_decision.schema.json",
    "review_disagreement_resolver": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/resolve_wave64_runpod_autonomous_review_disagreement.py",
    "phase_lease_runtime_canary_producer": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_phase_lease_runtime_canary.py",
    "strict_model_runtime_canary_producer": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_strict_model_runtime_canary.py",
    "e2e_shadow_job_runner": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_e2e_shadow_job.py",
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
        phase_lease_runtime_canary_evidence = load_json(
            PATHS["phase_lease_runtime_canary_evidence"]
        )
        strict_model_admission_hold_evidence = load_json(
            PATHS["strict_model_admission_hold_evidence"]
        )
        registry = load_json(PATHS["registry"])
        schema = load_json(PATHS["schema"])
        job_contract_schema = load_json(PATHS["job_contract_schema"])
        phase_lease_schema = load_json(PATHS["phase_lease_schema"])
        image_measurement_schema = load_json(PATHS["image_measurement_schema"])
        image_shadow_evidence_schema = load_json(PATHS["image_shadow_evidence_schema"])
        image_shadow_evidence = load_json(PATHS["image_shadow_evidence"])
        video_measurement_schema = load_json(PATHS["video_measurement_schema"])
        video_shadow_evidence_schema = load_json(PATHS["video_shadow_evidence_schema"])
        video_shadow_evidence = load_json(PATHS["video_shadow_evidence"])
        audio_measurement_schema = load_json(PATHS["audio_measurement_schema"])
        audio_shadow_evidence_schema = load_json(PATHS["audio_shadow_evidence_schema"])
        audio_shadow_evidence = load_json(PATHS["audio_shadow_evidence"])
        av_shadow_evidence_schema = load_json(PATHS["av_shadow_evidence_schema"])
        av_shadow_evidence = load_json(PATHS["av_shadow_evidence"])
        mask_measurement_schema = load_json(PATHS["mask_measurement_schema"])
        maskfactory_consumer_contract_schema = load_json(
            PATHS["maskfactory_consumer_contract_schema"]
        )
        tool_gateway_request_schema = load_json(PATHS["tool_gateway_request_schema"])
        tool_gateway_decision_schema = load_json(PATHS["tool_gateway_decision_schema"])
        tool_gateway_policy = load_json(PATHS["tool_gateway_policy"])
        workflow_patch_schema = load_json(PATHS["workflow_patch_schema"])
        workflow_validation_schema = load_json(PATHS["workflow_validation_schema"])
        workflow_patch_policy = load_json(PATHS["workflow_patch_policy"])
        correction_attempt_schema = load_json(PATHS["correction_attempt_schema"])
        correction_state_schema = load_json(PATHS["correction_state_schema"])
        evidence_bundle_schema = load_json(PATHS["evidence_bundle_schema"])
        promotion_transaction_schema = load_json(PATHS["promotion_transaction_schema"])
        role_qualification_report_schema = load_json(PATHS["role_qualification_report_schema"])
        role_qualification_certificate_schema = load_json(PATHS["role_qualification_certificate_schema"])
        role_drift_decision_schema = load_json(PATHS["role_drift_decision_schema"])
        migration_event_schema = load_json(PATHS["migration_event_schema"])
        migration_state_schema = load_json(PATHS["migration_state_schema"])
        migration_policy = load_json(PATHS["migration_policy"])
        reviewer_observation_schema = load_json(PATHS["reviewer_observation_schema"])
        review_authority_decision_schema = load_json(PATHS["review_authority_decision_schema"])
        review_disagreement_decision_schema = load_json(PATHS["review_disagreement_decision_schema"])
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
        phase_lease_runtime_canary_evidence,
        strict_model_admission_hold_evidence,
        registry,
    )
    for document in json_docs:
        if document.get("program_id") != PROGRAM:
            errors.append("JSON document has the wrong program_id")

    if (
        phase_lease_runtime_canary_evidence.get("canary_disposition")
        != "PASS_ADMISSION_AND_RELEASE_NO_GENERATION"
    ):
        errors.append("phase lease runtime canary must pass admission and release")
    final_canary_state = phase_lease_runtime_canary_evidence.get(
        "final_controller_state", {}
    )
    if final_canary_state.get("state") != "IDLE" or final_canary_state.get("lease") is not None:
        errors.append("phase lease runtime canary must finish IDLE without a lease")
    if (
        phase_lease_runtime_canary_evidence.get("strict_model_inventory", {}).get(
            "inference_executed"
        )
        is not False
    ):
        errors.append("phase lease admission canary must not claim model inference")
    if phase_lease_runtime_canary_evidence.get("resource_mutations") != []:
        errors.append("phase lease admission canary must not contain resource mutations")
    if strict_model_admission_hold_evidence.get("admission_disposition") != "BLOCKED_NO_ACTION":
        errors.append("strict model admission hold must remain a no-action block")
    required_hold_flags = {
        "inference_executed": False,
        "model_load_executed": False,
        "lease_acquired": False,
        "product_approval_granted": False,
    }
    for key, expected in required_hold_flags.items():
        if strict_model_admission_hold_evidence.get(key) is not expected:
            errors.append(f"strict model admission hold {key} must be {expected}")
    if strict_model_admission_hold_evidence.get("resource_mutations") != []:
        errors.append("strict model admission hold must not contain resource mutations")
    if "ACTIVE_FOREIGN_GPU_WORKLOAD_PRESENT" not in strict_model_admission_hold_evidence.get(
        "blocker_codes", []
    ):
        errors.append("strict model admission hold must bind the observed foreign workload")

    if (
        audio_shadow_evidence.get("overall_disposition")
        != "PASS_DETERMINISTIC_SHADOW_BLOCKED_SEMANTIC_AUDIO_AUTHORITY"
    ):
        errors.append("canonical audio shadow must pass deterministic gates and block semantic authority")
    if audio_shadow_evidence.get("product_promotion_eligible") is not False:
        errors.append("canonical audio shadow must not grant product promotion")
    if audio_shadow_evidence.get("measurement", {}).get("disposition") != "PASS_DETERMINISTIC_GATES":
        errors.append("canonical audio shadow deterministic measurement must pass")
    if audio_shadow_evidence.get("semantic_release_gate", {}).get("runtime_executed") is not False:
        errors.append("canonical audio shadow must not claim semantic runtime execution")
    if audio_shadow_evidence.get("diagnostic_review", {}).get("semantic_audio_review_claimed") is not False:
        errors.append("rendered audio diagnostics must not claim semantic audio review")
    audio_required_roles = set(
        audio_shadow_evidence.get("technical_contract", {})
        .get("quality_profile", {})
        .get("required_approval_roles", [])
    )
    if audio_required_roles != {"W64-AQA-ROLE-DETERMINISTIC"}:
        errors.append("audio technical shadow must require deterministic authority only")
    if (
        av_shadow_evidence.get("overall_disposition")
        != "PASS_DETERMINISTIC_AV_SHADOW_BLOCKED_SEMANTIC_AUTHORITIES"
    ):
        errors.append("canonical AV shadow must pass deterministic gates and block semantic authorities")
    if av_shadow_evidence.get("product_promotion_eligible") is not False:
        errors.append("canonical AV shadow must not grant product promotion")
    if av_shadow_evidence.get("measurement", {}).get("disposition") != "PASS_DETERMINISTIC_GATES":
        errors.append("canonical AV shadow deterministic measurement must pass")
    if av_shadow_evidence.get("decoded_frame_review", {}).get("motion_review_claimed") is not False:
        errors.append("single decoded AV frame must not claim motion review")
    av_metrics = av_shadow_evidence.get("measurement", {}).get("metrics", {})
    if av_metrics.get("av_stream_start_offset_ms") != 0.0:
        errors.append("canonical AV shadow stream start offset must be zero")
    if av_metrics.get("av_stream_duration_delta_ms") != 0.0:
        errors.append("canonical AV shadow stream duration delta must be zero")
    av_required_roles = set(
        av_shadow_evidence.get("technical_contract", {})
        .get("quality_profile", {})
        .get("required_approval_roles", [])
    )
    if av_required_roles != {"W64-AQA-ROLE-DETERMINISTIC"}:
        errors.append("AV technical shadow must require deterministic authority only")
    if (
        image_shadow_evidence.get("overall_disposition")
        != "PASS_DETERMINISTIC_IMAGE_GATES_REJECT_VISUAL_DEFECTS_STRICT_RUNTIME_HELD"
    ):
        errors.append("canonical image shadow must retain deterministic pass and visual rejection")
    if image_shadow_evidence.get("product_promotion_eligible") is not False:
        errors.append("canonical rejected image shadow must not grant product promotion")
    if image_shadow_evidence.get("measurement", {}).get("disposition") != "PASS_DETERMINISTIC_GATES":
        errors.append("canonical image shadow deterministic measurement must pass")
    if image_shadow_evidence.get("codex_visual_review", {}).get("status") != "REJECT_KNOWN_BLOCKING_DEFECTS":
        errors.append("canonical image shadow must retain the whole-image rejection")
    image_defects = set(
        image_shadow_evidence.get("codex_visual_review", {}).get("blocking_findings", [])
    )
    if image_defects != {"contact_placement_not_exact_target", "contact_shadow_not_clear"}:
        errors.append("canonical image shadow blocking defect set changed")
    if image_shadow_evidence.get("strict_model_gate", {}).get("runtime_executed") is not False:
        errors.append("canonical image shadow must not claim held strict-model execution")
    if (
        video_shadow_evidence.get("overall_disposition")
        != "PASS_DETERMINISTIC_VIDEO_GATES_DIAGNOSTIC_CONTACT_SHEET_ONLY_STRICT_RUNTIME_HELD"
    ):
        errors.append("canonical video shadow must pass deterministic gates and retain review limits")
    if video_shadow_evidence.get("product_promotion_eligible") is not False:
        errors.append("canonical video shadow must not grant product promotion")
    if video_shadow_evidence.get("measurement", {}).get("disposition") != "PASS_DETERMINISTIC_GATES":
        errors.append("canonical video shadow deterministic measurement must pass")
    video_metrics = video_shadow_evidence.get("measurement", {}).get("metrics", {})
    if video_metrics.get("frame_count") != 49 or video_metrics.get("sample_count") != 24:
        errors.append("canonical video shadow frame and sample counts changed")
    if video_metrics.get("duplicate_sample_fraction") != 0.0:
        errors.append("canonical video shadow must retain zero sampled duplicates")
    if video_shadow_evidence.get("contact_sheet_review", {}).get("whole_clip_review_claimed") is not False:
        errors.append("video contact sheet must not claim whole-clip review")
    if video_shadow_evidence.get("strict_model_gate", {}).get("runtime_executed") is not False:
        errors.append("canonical video shadow must not claim held strict-model execution")

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
    if migration_policy.get("decision_only") is not True:
        errors.append("migration controller must remain decision-only")
    if migration_policy.get("old_pod_stops_only_after_integration_switch") is not True:
        errors.append("migration policy must forbid old-pod stop before integration switch")
    migration_preferred = migration_policy.get("preferred_profile", {})
    if migration_preferred.get("gpu_type") != "NVIDIA A40" or migration_preferred.get("gpu_count") != 2:
        errors.append("migration preferred profile must remain exact 2x A40")
    if migration_preferred.get("maximum_hourly_usd") != 0.70:
        errors.append("migration preferred 2x A40 price ceiling must remain 0.70 USD/hour")

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
        jsonschema.Draft7Validator.check_schema(image_shadow_evidence_schema)
        jsonschema.Draft7Validator(
            image_shadow_evidence_schema,
            format_checker=jsonschema.FormatChecker(),
        ).validate(image_shadow_evidence)
        jsonschema.Draft7Validator.check_schema(video_measurement_schema)
        jsonschema.Draft7Validator.check_schema(video_shadow_evidence_schema)
        jsonschema.Draft7Validator(
            video_shadow_evidence_schema,
            format_checker=jsonschema.FormatChecker(),
        ).validate(video_shadow_evidence)
        jsonschema.Draft7Validator.check_schema(audio_measurement_schema)
        jsonschema.Draft7Validator.check_schema(audio_shadow_evidence_schema)
        jsonschema.Draft7Validator(
            audio_shadow_evidence_schema,
            format_checker=jsonschema.FormatChecker(),
        ).validate(audio_shadow_evidence)
        jsonschema.Draft7Validator.check_schema(av_shadow_evidence_schema)
        jsonschema.Draft7Validator(
            av_shadow_evidence_schema,
            format_checker=jsonschema.FormatChecker(),
        ).validate(av_shadow_evidence)
        jsonschema.Draft7Validator.check_schema(mask_measurement_schema)
        jsonschema.Draft7Validator.check_schema(maskfactory_consumer_contract_schema)
        jsonschema.Draft7Validator.check_schema(tool_gateway_request_schema)
        jsonschema.Draft7Validator.check_schema(tool_gateway_decision_schema)
        jsonschema.Draft7Validator.check_schema(workflow_patch_schema)
        jsonschema.Draft7Validator.check_schema(workflow_validation_schema)
        jsonschema.Draft7Validator.check_schema(correction_attempt_schema)
        jsonschema.Draft7Validator.check_schema(correction_state_schema)
        jsonschema.Draft7Validator.check_schema(evidence_bundle_schema)
        jsonschema.Draft7Validator.check_schema(promotion_transaction_schema)
        jsonschema.Draft7Validator.check_schema(role_qualification_report_schema)
        jsonschema.Draft7Validator.check_schema(role_qualification_certificate_schema)
        jsonschema.Draft7Validator.check_schema(role_drift_decision_schema)
        jsonschema.Draft7Validator.check_schema(migration_event_schema)
        jsonschema.Draft7Validator.check_schema(migration_state_schema)
        jsonschema.Draft7Validator.check_schema(reviewer_observation_schema)
        jsonschema.Draft7Validator.check_schema(review_authority_decision_schema)
        jsonschema.Draft7Validator.check_schema(review_disagreement_decision_schema)
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
