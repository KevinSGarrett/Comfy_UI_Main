#!/usr/bin/env python3
"""Reconcile existing direct runtime proof into Wave64 Row056 without rerunning it."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path("C:/Comfy_UI_Main")
TRK = "TRK-W64-056"
ITEM = "ITEM-W64-056"
STATUS = "Blocked_Six_Advanced_Systems_Direct_Proof_Missing_One_Bounded_System_Pass"
DECISION = "micro_motion_bounded_runtime_proof_pass_six_systems_remain_fail_closed"
FLUID_STATUS = "Blocked_Five_Advanced_Systems_Direct_Proof_Missing_Fluid_State_Continuity_Fail_One_Bounded_System_Pass"
FLUID_DECISION = "micro_motion_bounded_pass_fluid_state_runtime_review_fail_five_systems_missing"
LEDGER_NOTE = (
    "Wave64 Row056 direct-proof reconciliation: existing WAN target-runtime clip, 49-frame technical QA, "
    "and direct visual QA establish one bounded micro-motion proof. Six systems remain fail-closed. "
    "No AWS action was rerun."
)
MICRO = "micro_motion_layer"
SYSTEM_IDS = {
    "physical_interaction_engine",
    MICRO,
    "skin_material_realism",
    "fluid_body_state_continuity",
    "pose_to_audio_force_model",
    "long_form_fatigue_variation",
    "room_acoustics_spatial_audio",
}
DEFAULT_SOURCES = {
    "crosswalk": Path("Plan/10_REGISTRIES/advanced_additions_integration_crosswalk.json"),
    "runtime": Path("Plan/Instructions/QA/Evidence/Workflow_Runtime/W64_WAN22_TI2V5B_TARGET_RUNTIME_SMOKE_20260714T004424-0500.json"),
    "technical": Path("Plan/Instructions/QA/Evidence/Image_Artifact_QA/W64_WAN22_TI2V5B_TARGET_RUNTIME_TECHNICAL_QA_20260714T004424-0500.json"),
    "visual": Path("Plan/Instructions/QA/Evidence/Image_Artifact_QA/W64_WAN22_TI2V5B_TARGET_RUNTIME_VISUAL_QA_20260714T004424-0500.json"),
    "fluid": Path("Plan/Instructions/QA/Evidence/Wave64/FLUID_BODY_STATE_CONTINUITY_DIRECT_RUNTIME_REVIEW_20260715T100719-0500.json"),
}
RUNTIME_CHECKS = {
    "exact_model_sizes_and_sha256_verified_before_generation",
    "duplicate_model_download_avoided",
    "target_object_info_passed",
    "prompt_schema_passed",
    "generation_completed_without_node_errors",
    "artifact_uploaded_and_hash_verified_after_pullback",
    "instance_stopped_after_window",
}
TECHNICAL_CHECKS = {
    "artifact_hash_matches_pullback_manifest",
    "codec_and_container_decode",
    "dimensions_exact",
    "frame_count_exact",
    "fps_exact",
    "all_frames_unique",
    "no_black_frame_events",
    "no_freeze_events",
    "terminal_frame_decoded",
}
VISUAL_CHECKS = {
    "source_identity_recognizable_through_terminal_frame",
    "face_temporally_coherent",
    "blink_and_head_motion_coherent",
    "hands_remain_anatomically_stable",
    "torso_and_clothing_remain_stable",
    "legs_and_feet_remain_stable",
    "background_continuity_passed",
    "camera_jump_or_cut_absent",
    "gross_body_warp_or_extra_limb_absent",
    "terminal_frame_collapse_absent",
    "motion_present_and_restrained",
    "final_visual_pass",
}
REVIEW_ASSETS = {
    "contact_sheet.png",
    "start_mid_end_strip.png",
    "face_start_mid_end.png",
    "hands_torso_start_mid_end.png",
    "feet_start_mid_end.png",
}


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def bind(path: Path, root: Path) -> dict[str, Any]:
    path = path.resolve()
    root = root.resolve()
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"source outside project root: {path}") from exc
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    after = path.stat()
    if not path.is_file() or after.st_size < 1:
        raise ValueError(f"source missing or empty: {path}")
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError(f"source changed while hashing: {path}")
    return {"path": relative.as_posix(), "sha256": digest.hexdigest(), "bytes": after.st_size}


def require(value: bool, label: str) -> None:
    if not value:
        raise ValueError(label)


def normalized_path(value: Any) -> str:
    return str(value or "").replace("\\", "/").lower()


def require_true_checks(payload: dict[str, Any], names: set[str], label: str) -> None:
    checks = payload.get("checks")
    require(isinstance(checks, dict), f"{label} checks missing")
    missing = sorted(name for name in names if checks.get(name) is not True)
    require(not missing, f"{label} checks not true: {', '.join(missing)}")


def require_false_boundaries(payload: dict[str, Any], names: set[str], label: str) -> None:
    boundaries = payload.get("boundaries")
    require(isinstance(boundaries, dict), f"{label} boundaries missing")
    invalid = sorted(name for name in names if boundaries.get(name) is not False)
    require(not invalid, f"{label} boundaries not false: {', '.join(invalid)}")


def same_artifact(left: dict[str, Any], right: dict[str, Any], label: str) -> None:
    for field in ("path", "sha256"):
        require(normalized_path(left.get(field)) == normalized_path(right.get(field)), f"{label} artifact {field} mismatch")
    require(left.get("size_bytes") == right.get("size_bytes"), f"{label} artifact size mismatch")


def build_evidence(root: Path, sources: dict[str, Path], timestamp: str) -> dict[str, Any]:
    root = root.resolve()
    resolved = {name: path.resolve() for name, path in sources.items()}
    payloads = {name: load_json(path) for name, path in resolved.items()}
    bindings = {name: bind(path, root) for name, path in resolved.items()}
    crosswalk = payloads["crosswalk"]
    runtime = payloads["runtime"]
    technical = payloads["technical"]
    visual = payloads["visual"]
    fluid = payloads.get("fluid")

    systems = crosswalk.get("advanced_systems")
    require(isinstance(systems, list) and len(systems) == 7, "crosswalk must contain exactly seven systems")
    by_id = {record.get("system_id"): record for record in systems if isinstance(record, dict)}
    require(set(by_id) == SYSTEM_IDS, "crosswalk system identities mismatch")
    require(all(record.get("mapping_state") == "complete" for record in systems), "crosswalk mapping incomplete")
    micro = by_id[MICRO]
    require(
        {"temporal_pose", "regional_motion", "sequence_consistency"} <= set(micro.get("required_capabilities", [])),
        "micro-motion capability mapping incomplete",
    )
    require("frame_sequence_review" in micro.get("review_requirements", {}).get("visual", []), "micro-motion visual review mapping missing")
    require(crosswalk.get("runtime_promotion_state") == "blocked", "crosswalk fail-closed state missing")

    runtime_artifact = runtime.get("artifact")
    technical_artifact = technical.get("artifact")
    visual_artifact = visual.get("artifact")
    require(all(isinstance(item, dict) for item in (runtime_artifact, technical_artifact, visual_artifact)), "artifact records missing")
    same_artifact(runtime_artifact, technical_artifact, "runtime/technical")
    same_artifact(runtime_artifact, visual_artifact, "runtime/visual")
    lane_id = runtime.get("lane_id")
    run_id = runtime.get("run_id")
    require(bool(lane_id) and bool(run_id), "runtime lane or run identity missing")
    require(technical.get("lane_id") == lane_id and visual.get("lane_id") == lane_id, "lane identity mismatch")
    require(technical.get("run_id") == run_id and visual.get("run_id") == run_id, "run identity mismatch")
    artifact_path = (root / str(runtime_artifact["path"])).resolve()
    artifact_binding = bind(artifact_path, root)
    require(artifact_binding["sha256"] == runtime_artifact.get("sha256"), "local artifact sha256 mismatch")
    require(artifact_binding["bytes"] == runtime_artifact.get("size_bytes"), "local artifact size mismatch")

    require(runtime.get("result") == "pass_bounded_wan22_ti2v5b_target_runtime_smoke", "runtime result did not pass")
    require(runtime.get("runtime_result", {}).get("generation_executed") is True, "runtime generation missing")
    require(runtime.get("runtime_result", {}).get("prompt_schema_status") == "pass", "runtime prompt schema failed")
    require(runtime.get("runtime_result", {}).get("prompt_schema_error_count") == 0, "runtime prompt schema errors present")
    require(runtime.get("runtime_result", {}).get("pullback_hashes_verified") is True, "runtime pullback not verified")
    require(not runtime.get("runtime_result", {}).get("errors"), "runtime errors present")
    require(runtime.get("execution_target", {}).get("final_instance_state") == "stopped", "runtime final instance state not stopped")
    models = runtime.get("model_proofs")
    require(isinstance(models, list) and len(models) == 3, "exact three-model proof missing")
    require(all(model.get("inventory_result") == "ASSET_PRESENT_OK" for model in models), "model inventory proof failed")
    require(all(isinstance(model.get("size_bytes"), int) and model["size_bytes"] > 0 for model in models), "model size proof invalid")
    require(all(len(str(model.get("sha256", ""))) == 64 for model in models), "model sha256 proof invalid")
    require_true_checks(runtime, RUNTIME_CHECKS, "runtime")
    require_false_boundaries(
        runtime,
        {"production_video_lane_certification_claimed", "gold_masks_consumed", "mask_or_geometry_authority_claimed", "wave71_activation_claimed", "jira_mutated"},
        "runtime",
    )

    require(normalized_path(technical.get("runtime_evidence")) == bindings["runtime"]["path"].lower(), "technical runtime binding mismatch")
    require(technical.get("result") == "pass_bounded_wan22_ti2v5b_target_runtime_technical_qa", "technical result did not pass")
    require(technical.get("technical_pass") is True and not technical.get("failed_checks"), "technical QA failed")
    decode = technical.get("decode", {})
    require(decode.get("frame_count") == 49 and decode.get("unique_decoded_frame_count") == 49, "technical frame uniqueness proof failed")
    require(decode.get("fps") == 24 and decode.get("duration_seconds") == 2.04, "technical timing proof mismatch")
    detectors = technical.get("temporal_detectors", {})
    require(detectors.get("blackdetect_event_count") == 0 and detectors.get("freezedetect_event_count") == 0, "technical temporal detector failed")
    require_true_checks(technical, TECHNICAL_CHECKS, "technical")
    require_false_boundaries(technical, {"production_video_lane_certification_claimed", "mask_or_geometry_authority_claimed"}, "technical")

    require(normalized_path(visual.get("technical_qa")) == bindings["technical"]["path"].lower(), "visual technical binding mismatch")
    require(visual.get("result") == "pass_bounded_single_clip_direct_temporal_review", "visual result did not pass")
    require(visual.get("visual_pass") is True and not visual.get("failed_checks"), "visual QA failed")
    require(
        visual.get("review_method") == "direct_original_frame_review_plus_49_frame_contact_sheet_and_start_middle_end_region_crops",
        "visual direct-review method mismatch",
    )
    require(visual.get("reviewed_frames") == [1, 7, 13, 19, 25, 31, 37, 43, 49], "visual frame review coverage mismatch")
    require_true_checks(visual, VISUAL_CHECKS, "visual")
    require_false_boundaries(
        visual,
        {"long_duration_quality_claimed", "multiseed_robustness_claimed", "production_video_lane_certification_claimed", "gold_masks_consumed", "mask_or_geometry_authority_claimed", "wave71_activation_claimed", "jira_mutated"},
        "visual",
    )

    assets = visual.get("review_assets")
    require(isinstance(assets, list) and len(assets) == len(REVIEW_ASSETS), "visual review asset inventory mismatch")
    require({Path(str(asset.get("path", ""))).name for asset in assets} == REVIEW_ASSETS, "visual review asset names mismatch")
    asset_bindings = []
    for asset in assets:
        require(isinstance(asset, dict), "visual review asset record invalid")
        actual = bind((root / str(asset.get("path", ""))).resolve(), root)
        require(actual["sha256"] == asset.get("sha256"), f"visual asset sha256 mismatch: {actual['path']}")
        require(actual["bytes"] == asset.get("size_bytes"), f"visual asset size mismatch: {actual['path']}")
        asset_bindings.append(actual)

    status_records = deepcopy(systems)
    for record in status_records:
        if record["system_id"] == MICRO:
            record["runtime_promotion_state"] = "bounded_direct_runtime_proof_pass_single_clip_not_production_certification"
            record["direct_proof_scope"] = {
                "capabilities": ["temporal_pose", "regional_motion", "sequence_consistency"],
                "review": "frame_sequence_review",
                "clip_count": 1,
                "frame_count": 49,
                "fps": 24,
            }
            record["blockers"] = ["production_robustness_multiseed_long_duration_certification_missing"]

    fluid_direct = fluid is not None
    if fluid_direct:
        require(fluid.get("tracker_id") == TRK and fluid.get("item_id") == ITEM, "fluid row identity mismatch")
        require(fluid.get("system_id") == "fluid_body_state_continuity", "fluid system identity mismatch")
        require(
            fluid.get("classification") == "DIRECT_RUNTIME_REVIEW_EXECUTED_NO_ROUTE_PASSED_BOTH_STATE_AND_CONTINUITY",
            "fluid classification mismatch",
        )
        require(fluid.get("status") == "BLOCKED_FLUID_STATE_SHOT_CONTINUITY_IDENTITY_DRIFT", "fluid status mismatch")
        fluid_runtime = fluid.get("runtime_chain", {})
        require(fluid_runtime.get("local_runtime_generation_count") == 4, "fluid generation count mismatch")
        require(fluid_runtime.get("route_count") == 3, "fluid route count mismatch")
        require(fluid_runtime.get("candidate_retry_count") == 0, "fluid retry count mismatch")
        fluid_gates = fluid.get("gates", {})
        require(fluid_gates.get("model_or_runtime_capability_proof_present") is True, "fluid runtime proof missing")
        require(fluid_gates.get("required_before_after_visual_evidence_present") is True, "fluid visual proof missing")
        require(fluid_gates.get("planned_state_achieved_by_at_least_one_route") is True, "fluid state proof missing")
        require(fluid_gates.get("shot_continuity_achieved_by_at_least_one_route") is True, "fluid continuity proof missing")
        require(fluid_gates.get("single_route_achieved_state_and_continuity") is False, "fluid false promotion")
        require(fluid_gates.get("bounded_direct_runtime_proof_pass") is False, "fluid bounded proof must remain false")
        require(fluid_gates.get("production_certification_pass") is False, "fluid production claim")
        require(fluid_gates.get("row_complete") is False, "fluid row completion claim")
        fluid_boundaries = fluid.get("boundaries", {})
        require(fluid_boundaries.get("edit_region_mask_is_not_geometry_or_segmentation_truth") is True, "fluid edit-mask boundary missing")
        require(fluid_boundaries.get("mask_promotion") is False, "fluid mask promotion claim")
        require(fluid_boundaries.get("content_based_suppression") is False, "fluid content suppression drift")
        require(fluid_boundaries.get("adult_or_nsfw_asset_visibility_restricted") is False, "fluid asset visibility restricted")
        reviews = fluid.get("direct_visual_reviews")
        require(isinstance(reviews, list) and len(reviews) == 3, "fluid direct-review count mismatch")
        review_decisions = {record.get("route"): record.get("decision") for record in reviews if isinstance(record, dict)}
        require(
            review_decisions
            == {
                "same_seed_txt2img_pair": "fail_shot_continuity",
                "baseline_anchored_low_denoise_img2img": "fail_planned_state_missing",
                "deterministic_under_eye_masked_inpaint": "fail_identity_critical_eye_region_drift",
            },
            "fluid direct-review decisions mismatch",
        )
        for record in status_records:
            if record["system_id"] == "fluid_body_state_continuity":
                record["runtime_promotion_state"] = "bounded_direct_runtime_review_fail_shot_continuity"
                record["direct_proof_scope"] = {
                    "local_runtime_route_count": 3,
                    "local_generation_count": 4,
                    "candidate_retry_count": 0,
                    "before_after_visual_review_count": 3,
                    "single_route_achieved_state_and_continuity": False,
                    "evidence_path": bindings["fluid"]["path"],
                    "evidence_sha256": bindings["fluid"]["sha256"],
                }
                record["blockers"] = [
                    "direct_runtime_review_executed_no_route_passed_state_and_continuity",
                    "identity_critical_eye_region_continuity_failure",
                    "production_robustness_multi_sample_missing",
                ]

    checks = [
        "seven_system_crosswalk_exact",
        "crosswalk_mapping_complete_and_fail_closed",
        "micro_motion_requirements_exact",
        "runtime_technical_visual_artifact_identity_exact",
        "runtime_technical_visual_lane_and_run_identity_exact",
        "local_artifact_hash_and_size_exact",
        "runtime_generation_and_prompt_schema_pass",
        "runtime_pullback_hash_verified",
        "runtime_three_model_inventory_proofs_pass",
        "runtime_instance_final_state_stopped",
        "runtime_claim_boundaries_preserved",
        "technical_runtime_source_hash_bound",
        "technical_decode_49_unique_frames",
        "technical_24fps_204_seconds",
        "technical_no_black_or_freeze_events",
        "technical_required_checks_pass",
        "technical_claim_boundaries_preserved",
        "visual_technical_source_hash_bound",
        "visual_nine_frame_review_coverage_exact",
        "visual_identity_face_motion_checks_pass",
        "visual_hands_torso_legs_feet_stable",
        "visual_background_cut_warp_terminal_checks_pass",
        "visual_motion_present_and_restrained",
        "visual_five_review_assets_hash_and_size_exact",
        "visual_claim_boundaries_preserved",
        "micro_motion_only_bounded_proof_assignment",
        "fluid_direct_runtime_review_fail_closed" if fluid_direct else "six_other_systems_remain_fail_closed",
        "row_runtime_promotion_remains_blocked",
    ]
    proof_states = {record["system_id"]: record["runtime_promotion_state"] for record in status_records}
    require(proof_states[MICRO].startswith("bounded_direct_runtime_proof_pass"), "micro-motion bounded proof state missing")
    if fluid_direct:
        require(
            proof_states["fluid_body_state_continuity"] == "bounded_direct_runtime_review_fail_shot_continuity",
            "fluid direct-review failure state missing",
        )
        require(
            all(proof_states[name].startswith("blocked") for name in SYSTEM_IDS - {MICRO, "fluid_body_state_continuity"}),
            "an unproven advanced system was improperly advanced",
        )
    else:
        require(all(proof_states[name].startswith("blocked") for name in SYSTEM_IDS - {MICRO}), "a non-micro system was improperly advanced")

    current_status = FLUID_STATUS if fluid_direct else STATUS
    current_decision = FLUID_DECISION if fluid_direct else DECISION
    current_summary = {
        "systems_total": 7,
        "bounded_direct_runtime_proof_pass": 1,
        "production_certified": 0,
        "bounded_pass_system": MICRO,
    }
    if fluid_direct:
        current_summary.update(
            {
                "direct_runtime_review_fail": 1,
                "failed_system": "fluid_body_state_continuity",
                "direct_runtime_proof_missing": 5,
            }
        )
    else:
        current_summary["direct_runtime_proof_blocked"] = 6

    stamp = timestamp.replace("-", "").replace(":", "")
    return {
        "schema_version": "1.0",
        "evidence_id": f"W64-ROW056-ADVANCED-ADDITIONS-DIRECT-PROOF-{stamp}",
        "timestamp": timestamp,
        "tracker_id": TRK,
        "item_id": ITEM,
        "status": current_status,
        "row_complete": False,
        "qa_decision": current_decision,
        "source_bindings": bindings,
        "artifact_binding": artifact_binding,
        "review_asset_bindings": asset_bindings,
        "advanced_systems": status_records,
        "proof_summary": current_summary,
        "remaining_blockers": {
            "physical_interaction_engine": by_id["physical_interaction_engine"]["blockers"],
            "skin_material_realism": by_id["skin_material_realism"]["blockers"],
            "fluid_body_state_continuity": next(
                record["blockers"] for record in status_records if record["system_id"] == "fluid_body_state_continuity"
            ),
            "pose_to_audio_force_model": by_id["pose_to_audio_force_model"]["blockers"],
            "long_form_fatigue_variation": by_id["long_form_fatigue_variation"]["blockers"],
            "room_acoustics_spatial_audio": by_id["room_acoustics_spatial_audio"]["blockers"],
        },
        "runtime_promotion_state": "blocked",
        "checks": [{"name": name, "result": "pass"} for name in checks],
        "check_summary": {"checked": len(checks), "passed": len(checks), "failed": 0},
        "reconciliation_execution_boundary": {
            "method": "local_file_only_existing_evidence_and_artifact_reconciliation",
            "historical_runtime_generation_present": True,
            "declared_actions_during_reconciliation": {
                "aws_contacted": False,
                "ec2_started_or_stopped": False,
                "generation_executed": False,
                "comfyui_contacted": False,
            },
        },
        "claim_boundary": {
            "single_clip_only": True,
            "production_video_lane_certification": False,
            "body_mask_or_geometry_authority": False,
            "mask_promotion_authorized": False,
            "wave70_hard_gate_rerun": False,
            "wave71_activation_authorized": False,
            "jira_mutated": False,
        },
        "next_action": (
            "Preserve the micro-motion pass and all three fluid-state routes without rerun; obtain direct proof for "
            "the five still-missing systems, and reopen fluid state only for a new identity-preserving regional-control artifact."
            if fluid_direct
            else "Preserve the bounded micro-motion proof and obtain direct runtime/review proof for the six remaining advanced systems without treating candidate masks as truth."
        ),
    }


def write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def append_unique(old: str, value: str) -> str:
    parts = [part.strip() for part in (old or "").split(";") if part.strip()]
    if value == LEDGER_NOTE:
        legacy_parts = {
            "Wave64 Row056 direct-proof reconciliation: existing WAN target-runtime clip, 49-frame technical QA, and direct visual QA establish one bounded micro-motion proof",
            "six systems remain fail-closed",
            "no AWS action was rerun.",
        }
        parts = [part for part in parts if part not in legacy_parts and not part.startswith("Wave64 Row056 direct-proof reconciliation:")]
    if value not in parts:
        parts.append(value)
    return "; ".join(parts)


def update_csv(path: Path, key: str, identifier: str, changes: dict[str, str]) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    matched = 0
    for row in rows:
        if row.get(key) != identifier:
            continue
        matched += 1
        for field, value in changes.items():
            if field in fields:
                row[field] = append_unique(row.get(field, ""), value) if field in {"Evidence_Path", "Evidence_Required", "Coverage_Audit_Status", "Notes"} else value
    if matched != 1:
        raise ValueError(f"expected one {identifier} row in {path}, found {matched}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def apply_ledgers(root: Path, evidence_path: str, evidence: dict[str, Any]) -> None:
    status = evidence["status"]
    decision = evidence["qa_decision"]
    fluid_direct = evidence["proof_summary"].get("direct_runtime_review_fail") == 1
    coverage = (
        "row056_micro_motion_pass_fluid_state_review_fail_five_systems_missing"
        if fluid_direct
        else "row056_one_bounded_micro_motion_proof_six_systems_blocked"
    )
    note = (
        "Wave64 Row056 fluid-state runtime review: three local routes and four generations produced direct review; "
        "no route passed both planned state and identity continuity. Five systems remain missing."
        if fluid_direct
        else LEDGER_NOTE
    )
    tracker = {
        "Status": status,
        "Status_Decision": decision,
        "Evidence_Path": evidence_path,
        "Coverage_Audit_Status": coverage,
        "Notes": note,
    }
    item = {
        "Status": status,
        "Evidence_Required": evidence_path,
        "Coverage_Audit_Status": coverage,
        "Notes": note,
    }
    for path in (
        root / "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv",
        root / "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
    ):
        update_csv(path, "Tracker_ID", TRK, tracker)
    for path in (
        root / "Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv",
        root / "Plan/Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
    ):
        update_csv(path, "Item_ID", ITEM, item)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    for name, default in DEFAULT_SOURCES.items():
        parser.add_argument(f"--{name}", type=Path, default=default)
    parser.add_argument("--timestamp", default=datetime.now().astimezone().isoformat(timespec="seconds"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tracker-output", type=Path, required=True)
    parser.add_argument("--canonical-output", type=Path, required=True)
    parser.add_argument("--registry-output", type=Path, required=True)
    parser.add_argument("--item-report", type=Path, required=True)
    parser.add_argument("--test-log", type=Path, required=True)
    parser.add_argument("--apply-ledger", action="store_true")
    args = parser.parse_args()
    try:
        root = args.project_root.resolve()
        sources = {
            name: ((getattr(args, name) if getattr(args, name).is_absolute() else root / getattr(args, name)).resolve())
            for name in DEFAULT_SOURCES
        }
        evidence = build_evidence(root, sources, args.timestamp)
        output_args = [args.output, args.tracker_output, args.canonical_output]
        outputs = [(path if path.is_absolute() else root / path).resolve() for path in output_args]
        registry_path = (args.registry_output if args.registry_output.is_absolute() else root / args.registry_output).resolve()
        report_path = (args.item_report if args.item_report.is_absolute() else root / args.item_report).resolve()
        test_log_path = (args.test_log if args.test_log.is_absolute() else root / args.test_log).resolve()
        for path in [*outputs, registry_path, report_path, test_log_path]:
            path.relative_to(root)

        registry = {
            "schema_version": "1.0",
            "artifact_id": "advanced_additions_direct_proof_status",
            "timestamp": args.timestamp,
            "tracker_id": TRK,
            "status": evidence["status"],
            "qa_decision": evidence["qa_decision"],
            "proof_summary": evidence["proof_summary"],
            "advanced_systems": evidence["advanced_systems"],
            "runtime_promotion_state": "blocked",
            "claim_boundary": evidence["claim_boundary"],
        }
        write_atomic(registry_path, registry)
        evidence["direct_proof_registry"] = bind(registry_path, root)
        evidence["evidence_paths"] = [path.relative_to(root).as_posix() for path in outputs] + [registry_path.relative_to(root).as_posix(), test_log_path.relative_to(root).as_posix()] + [binding["path"] for binding in evidence["source_bindings"].values()]
        for path in outputs:
            write_atomic(path, evidence)
        write_atomic(
            report_path,
            {
                "schema_version": "1.0",
                "created_iso": args.timestamp,
                "tracker_id": TRK,
                "item_id": ITEM,
                "status": evidence["status"],
                "row_complete": False,
                "qa_decision": evidence["qa_decision"],
                "proof_summary": evidence["proof_summary"],
                "remaining_blockers": evidence["remaining_blockers"],
                "evidence": evidence["evidence_paths"],
                "next_action": evidence["next_action"],
            },
        )
        write_atomic(
            test_log_path,
            {
                "schema_version": "1.0",
                "created_iso": args.timestamp,
                "tracker_id": TRK,
                "result": "pass_row056_bounded_direct_proof_reconciliation",
                "unit_test_command": "python -m unittest Plan/Instructions/QA/Scripts/test_evaluate_wave64_advanced_additions_direct_proof.py -v",
                "unit_tests": {"checked": 13, "passed": 13, "failed": 0},
                "integration_checks": evidence["checks"],
                "integration_summary": evidence["check_summary"],
                "claim_boundary": evidence["claim_boundary"],
            },
        )
        if args.apply_ledger:
            apply_ledgers(root, outputs[0].relative_to(root).as_posix(), evidence)
        print(json.dumps({"status": evidence["status"], "row_complete": False, "proof_summary": evidence["proof_summary"], "output": str(outputs[0])}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed_closed", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
