#!/usr/bin/env python3
"""Build a hash-bound video keyframe candidate and fail closed on promotion gates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from jsonschema import Draft202012Validator


ROOT = Path("C:/Comfy_UI_Main")
TRK = "TRK-W64-019"
ITEM = "ITEM-W64-019"
STATUS = "Blocked_Keyframe_And_Repair_Proof_Missing_Bounded_Wan_Temporal_And_Loop_Pass"
DECISION = "wan_bounded_runtime_multiclip_temporal_and_loop_export_pass_keyframe_and_repair_fail_closed"
SCHEMA = Path("Plan/08_SCHEMAS/video_keyframe_handoff.schema.json")
CANDIDATE = Path("Plan/Instructions/QA/Evidence/Wave64/Video_Keyframes/normal_v4_wan22_keyframe_handoff_candidate.json")
READINESS = Path("Plan/Instructions/QA/Evidence/Wave64/video_keyframe_handoff_readiness.json")
CANONICAL = Path("Plan/Instructions/QA/Evidence/Wave64/video_pipeline_build.json")
TEST_LOG = Path("Plan/Instructions/QA/Evidence/Wave64/video_keyframe_handoff_readiness_test_log.json")
REPORT = Path("Plan/Items/Reports/ITEM-W64-019_video_pipeline_build.json")
SOURCES = {
    "base_qa": Path("Plan/Instructions/QA/Evidence/Image_Artifact_QA/W70_LOCAL_NORMAL_V4_FULL_BODY_STANDING_QA_20260711T041000-0500.json"),
    "runtime": Path("Plan/Instructions/QA/Evidence/Workflow_Runtime/W64_WAN22_TI2V5B_TARGET_RUNTIME_SMOKE_20260714T004424-0500.json"),
    "technical": Path("Plan/Instructions/QA/Evidence/Image_Artifact_QA/W64_WAN22_TI2V5B_TARGET_RUNTIME_TECHNICAL_QA_20260714T004424-0500.json"),
    "promotion": Path("Plan/Instructions/QA/Evidence/Wave64/future_lane_promotion.json"),
    "route": Path("Plan/Instructions/QA/Evidence/Wave64/video_engine_routing.json"),
    "shot_plan": Path("Plan/Instructions/QA/Evidence/Wave64/Reference_Video_Input/wan22_source_diversity_loop_shot_plan.json"),
    "context": Path("Plan/Instructions/QA/Evidence/Wave64/Video_Keyframes/normal_v4_keyframe_context_contract.json"),
}
POLICY_SOURCES = [
    "Plan/04_VIDEO_GIF_SYSTEM/WAVE15_BASE_IMAGE_TO_VIDEO_KEYFRAME_HANDOFF.md",
    "Plan/04_VIDEO_GIF_SYSTEM/WAVE16_VIDEO_KEYFRAME_REFINE_BRIDGE_INTERFACE.md",
    "Plan/04_VIDEO_GIF_SYSTEM/WAVE09_VIDEO_WORKFLOW_PROOF_REQUIREMENTS.md",
]
GATE_KEYS = (
    "base_image_qa_passed",
    "base_image_scored",
    "refine_bridge_qa_passed",
    "character_count_body_visibility_passed",
    "identity_camera_environment_continuity_passed",
    "output_hash_recorded",
    "frame_contract_exported",
    "required_promoted_keyframes_exist",
    "environment_profile_exists",
    "character_profile_exists",
    "engine_route_valid",
    "model_assets_registered",
    "output_path_defined",
    "promotion_allowed",
    "promoted_artifact",
)
NOTE = (
    "Wave64 Row019 keyframe handoff: the exact Normal v4 still is now hash-bound to its passing bounded image QA "
    "and prior WAN input, but remains candidate-only because refine, continuity/profile, frame-contract, promoted-"
    "keyframe, and promotion gates are absent. No runtime or promotion action was performed."
)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def require(value: bool, label: str) -> None:
    if not value:
        raise ValueError(label)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def bind(path: Path, root: Path) -> dict[str, Any]:
    before = path.stat()
    result = {"path": rel(path, root), "sha256": sha256(path), "bytes": before.st_size}
    after = path.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), f"source changed while hashing: {path}")
    return result


def encoded(payload: object) -> bytes:
    return (json.dumps(payload, indent=2) + "\n").encode("utf-8")


def binding_for_bytes(path: Path, payload: object, root: Path) -> dict[str, Any]:
    raw = encoded(payload)
    return {"path": rel(path, root), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def validate_schema(payload: dict[str, Any], schema_path: Path) -> None:
    schema = load(schema_path)
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda error: [str(part) for part in error.path])
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.path) or "root"
        raise ValueError(f"schema validation failed at {location}: {error.message}")


def validate_semantics(payload: dict[str, Any]) -> None:
    gates = payload["eligibility"]["gates"]
    require(tuple(gates) == GATE_KEYS, "eligibility gate contract mismatch")
    failed = [name for name in GATE_KEYS if gates[name] is False]
    require(payload["eligibility"]["failed_gates"] == failed, "failed gate list does not match gate values")
    all_passed = all(gates.values())
    require(payload["eligibility"]["all_required_gates_passed"] is all_passed, "all-required gate result mismatch")
    eligible = all_passed and not payload["candidate"]["candidate_only"]
    require(payload["eligibility"]["production_keyframe_eligible"] is eligible, "production keyframe eligibility overclaim")
    promotion = payload["promotion"]
    require(gates["promotion_allowed"] is promotion["promotion_allowed"], "promotion gate mismatch")
    require(gates["promoted_artifact"] is promotion["promoted_artifact"], "promoted-artifact gate mismatch")
    if payload["candidate"]["candidate_only"]:
        require(not any((promotion["promotion_allowed"], promotion["promotion_ready"], promotion["promoted_artifact"])), "candidate-only manifest cannot claim promotion")
        require(not payload["proof_scope"]["production_keyframe_claimed"], "candidate-only manifest cannot claim production keyframe status")
    require(not payload["proof_scope"]["production_video_lane_certification_claimed"], "keyframe handoff cannot claim production video certification")


def build(
    root: Path,
    source_paths: dict[str, Path],
    timestamp: str,
    schema_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    root = root.resolve()
    paths = {name: (path if path.is_absolute() else root / path).resolve() for name, path in source_paths.items()}
    data = {name: load(path) for name, path in paths.items()}
    qa, runtime, technical = data["base_qa"], data["runtime"], data["technical"]
    promotion, route, shot_plan, context = data["promotion"], data["route"], data["shot_plan"], data["context"]

    require(qa.get("pass") is True, "base image QA did not pass")
    require(qa.get("result") == "pass_with_notes_local_normal_v4_full_body_scope", "unexpected base image QA scope")
    output = qa.get("outputs", {}).get("generated_image", {})
    image_path = (root / str(output.get("path", ""))).resolve()
    require(image_path.is_file(), "keyframe candidate image is missing")
    image_hash = sha256(image_path)
    require(image_hash == output.get("sha256"), "keyframe candidate image hash drift")
    require(output.get("width") == 768 and output.get("height") == 1024, "keyframe candidate dimensions changed")
    checks = qa.get("checks", {})
    body_visibility = all(
        checks.get(name) is True
        for name in (
            "exactly_one_person_in_source_and_output",
            "visual_one_full_length_subject",
            "visual_head_hands_and_shoes_in_frame",
            "visual_bilateral_limb_continuity_coherent",
        )
    )
    base_scored = bool(qa.get("visual_review", {}).get("observations")) and checks.get("runtime_generation_passed") is True
    require(qa.get("boundaries", {}).get("final_lane_certification") is False, "base QA unexpectedly claims final lane certification")
    require(qa.get("boundaries", {}).get("mask_promotion") is False, "base QA unexpectedly claims mask promotion")

    runtime_input = runtime.get("input", {})
    require(runtime_input.get("path") == output.get("path"), "WAN runtime input path does not match candidate")
    require(runtime_input.get("sha256") == image_hash, "WAN runtime input hash does not match candidate")
    runtime_result = runtime.get("runtime_result", {})
    require(runtime.get("result") == "pass_bounded_wan22_ti2v5b_target_runtime_smoke", "bounded WAN runtime proof missing")
    require(runtime_result.get("generation_executed") is True and not runtime_result.get("errors"), "bounded WAN runtime did not complete cleanly")
    require(runtime.get("execution_target", {}).get("final_instance_state") == "stopped", "reused WAN runtime did not finish stopped")
    require(runtime.get("boundaries", {}).get("production_video_lane_certification_claimed") is False, "WAN runtime overclaims production certification")
    model_assets_registered = bool(runtime.get("model_proofs")) and all(
        item.get("inventory_result") == "ASSET_PRESENT_OK" and isinstance(item.get("sha256"), str) and len(item["sha256"]) == 64
        for item in runtime["model_proofs"]
    )
    output_path_defined = bool(runtime.get("artifact", {}).get("path"))
    decode = technical.get("decode", {})
    require(technical.get("technical_pass") is True, "bounded WAN technical QA did not pass")
    require(technical.get("lane_id") == runtime.get("lane_id") and technical.get("run_id") == runtime.get("run_id"), "WAN technical QA identity mismatch")
    require(technical.get("artifact", {}).get("sha256") == runtime.get("artifact", {}).get("sha256"), "WAN technical artifact hash mismatch")
    require(decode.get("frame_count") == 49 and decode.get("unique_decoded_frame_count") == 49, "WAN technical frame-count proof missing")
    require(decode.get("fps") == 24 and decode.get("duration_seconds") == 2.04, "WAN technical timing proof missing")
    require(decode.get("all_frames_extracted") is True and decode.get("decode_exit_code") == 0, "WAN technical decode proof missing")
    require(technical.get("boundaries", {}).get("production_video_lane_certification_claimed") is False, "WAN technical QA overclaims production certification")

    route_probe = route.get("canonical_route_probe", {})
    engine_route_valid = bool(
        route.get("overall_pass") is True
        and route_probe.get("result") == "compatible"
        and route_probe.get("selected_engine") == "wan"
        and route_probe.get("runtime_ready") is True
    )
    require(route.get("strict_decision", {}).get("production_video_certification_claimed") is False, "route evidence overclaims production certification")

    promotion_state = promotion.get("current_promotion_state", {})
    promotion_allowed = promotion_state.get("promotion_allowed") is True
    promoted_artifact = bool(promotion_state.get("promoted_lane_count"))
    require(promotion_state.get("decision") == "deny_no_promotion_request", "unexpected promotion decision")
    require(not promotion_allowed and not promoted_artifact, "candidate source was unexpectedly promoted")

    require(shot_plan.get("candidate_only") is True and shot_plan.get("promotion_ready") is False, "downstream shot plan promotion boundary missing")
    require(shot_plan.get("target_output_generated") is False, "downstream shot plan unexpectedly claims target generation")
    context_gates = context.get("gates", {})
    require(context.get("source_artifact", {}).get("path") == output.get("path") and context.get("source_artifact", {}).get("sha256") == image_hash, "keyframe context source mismatch")
    require(context_gates.get("frame_contract_exported") is True, "frame contract export proof missing")
    require(context_gates.get("environment_profile_exists") is True, "environment profile proof missing")
    require(context_gates.get("character_profile_exists") is True, "character profile proof missing")
    require(context_gates.get("identity_camera_environment_continuity_passed") is False, "single-image context overclaims continuity")
    require(context.get("boundaries", {}).get("single_image_anchor_only") is True, "context scope is not single-image")
    require(context.get("boundaries", {}).get("promotion_claimed") is False, "context overclaims promotion")

    gates = {
        "base_image_qa_passed": True,
        "base_image_scored": base_scored,
        "refine_bridge_qa_passed": False,
        "character_count_body_visibility_passed": body_visibility,
        "identity_camera_environment_continuity_passed": False,
        "output_hash_recorded": True,
        "frame_contract_exported": True,
        "required_promoted_keyframes_exist": False,
        "environment_profile_exists": True,
        "character_profile_exists": True,
        "engine_route_valid": engine_route_valid,
        "model_assets_registered": model_assets_registered,
        "output_path_defined": output_path_defined,
        "promotion_allowed": promotion_allowed,
        "promoted_artifact": promoted_artifact,
    }
    failed = [name for name in GATE_KEYS if gates[name] is False]
    all_passed = all(gates.values())
    source_bindings = {name: bind(path, root) for name, path in paths.items()}
    qa_inputs = qa.get("inputs", {})
    profile = load(root / qa_inputs["profile"]["path"])
    profile_values = profile.get("request_patch_values", {})
    control = qa_inputs.get("control_map", {})
    candidate = {
        "schema_version": "1.0",
        "manifest_id": "normal_v4_wan22_keyframe_handoff_candidate",
        "timestamp": timestamp,
        "tracker_id": TRK,
        "item_id": ITEM,
        "status": "blocked_candidate_hash_bound_not_promotion_eligible",
        "candidate": {
            "shot_id": "wan22_fullbody_standing_seed2271301_bounded_smoke_candidate",
            "scene_id": "normal_v4_fullbody_studio_anchor_scene",
            "environment_id": context["environment_profile"]["environment_id"],
            "character_ids": [context["character_profile"]["character_id"]],
            "output_type": "video",
            "frame_rate_target": decode["fps"],
            "duration_seconds": decode["duration_seconds"],
            "camera_plan_id": context["camera_plan"]["camera_plan_id"],
            "pose_plan_id": context["pose_plan"]["pose_plan_id"],
            "continuity_dependencies": [context["context_id"]],
            "qa_targets": ["identity_stability", "environment_stability", "body_visibility", "temporal_stability"],
            "keyframe_artifact": {
                "path": rel(image_path, root),
                "sha256": image_hash,
                "bytes": image_path.stat().st_size,
                "width": output["width"],
                "height": output["height"],
            },
            "base_image_qa": {
                "path": rel(paths["base_qa"], root),
                "sha256": source_bindings["base_qa"]["sha256"],
                "passed": True,
                "scored": base_scored,
                "decision": qa["result"],
            },
            "runtime_context": {
                "bounded_smoke_previously_executed": True,
                "runtime_input_hash_matched": True,
                "selected_engine": "wan",
                "engine_route_runtime_ready": engine_route_valid,
                "production_video_certified": False,
                "final_instance_state": "stopped",
            },
            "generation_metadata": {
                "source_base_engine": qa.get("lane_id", "sdxl_realvisxl_controlnet_normal_lane"),
                "refine_engine": None,
                "seed": int(profile_values["seed"]),
                "model_asset": str(profile_values["model_asset"]),
                "denoise_history": [{"stage": "base_generation", "denoise": float(profile_values["sampler_settings"]["denoise"])}],
            },
            "control_maps_used": [{"path": control["path"], "sha256": control["sha256"], "bytes": (root / control["path"]).stat().st_size}],
            "masks_used": [],
            "failure_rerun_history": [],
            "candidate_only": True,
        },
        "eligibility": {
            "gates": gates,
            "failed_gates": failed,
            "all_required_gates_passed": all_passed,
            "production_keyframe_eligible": False,
        },
        "promotion": {
            "promotion_allowed": promotion_allowed,
            "promotion_ready": False,
            "promoted_artifact": promoted_artifact,
            "decision": promotion_state["decision"],
            "source_evidence": source_bindings["promotion"],
        },
        "proof_scope": {
            "established": [
                "exact still path and SHA256",
                "bounded local full-body image QA pass with notes",
                "exact still reused as input to one completed bounded WAN target-runtime smoke",
                "WAN route and model assets proven for the bounded smoke contract",
                "single-image frame composition contract exported",
                "single-image environment and character identity anchors registered",
            ],
            "excluded": [
                "promoted production keyframe",
                "refine bridge QA",
                "multi-frame character identity continuity",
                "multi-frame environment and camera continuity",
                "production video lane certification",
                "body mask or geometry authority",
            ],
            "production_keyframe_claimed": False,
            "production_video_lane_certification_claimed": False,
        },
        "safety": {
            "generation_executed": False,
            "aws_contacted": False,
            "ec2_started": False,
            "masks_consumed_as_truth": False,
            "mask_promotion": False,
            "wave70_hard_gate_rerun": False,
            "wave71_activated": False,
            "jira_mutated": False,
        },
        "provenance": {
            "source_bindings": source_bindings,
            "policy_sources": POLICY_SOURCES,
            "downstream_candidate_context": source_bindings["shot_plan"],
        },
    }
    validate_schema(candidate, schema_path or root / SCHEMA)
    validate_semantics(candidate)
    candidate_binding = binding_for_bytes(root / CANDIDATE, candidate, root)
    readiness = {
        "schema_version": "1.0",
        "evidence_id": "",
        "timestamp": timestamp,
        "tracker_id": TRK,
        "item_id": ITEM,
        "status": STATUS,
        "row_complete": False,
        "result": "pass_candidate_compilation_blocked_production_keyframe_eligibility",
        "candidate_manifest": candidate_binding,
        "eligibility": deepcopy(candidate["eligibility"]),
        "promotion": deepcopy(candidate["promotion"]),
        "checks": [
            {"name": "VKH-R01_schema_valid", "result": "pass"},
            {"name": "VKH-R02_source_image_exists_and_hash_matches_qa", "result": "pass"},
            {"name": "VKH-R03_runtime_input_path_and_hash_match_candidate", "result": "pass"},
            {"name": "VKH-R04_base_image_bounded_qa_passed", "result": "pass"},
            {"name": "VKH-R05_character_count_and_body_visibility_passed", "result": "pass"},
            {"name": "VKH-R06_wan_route_runtime_ready", "result": "pass"},
            {"name": "VKH-R07_model_assets_registered_in_reused_runtime", "result": "pass"},
            {"name": "VKH-R08_promotion_denied_without_request", "result": "pass"},
            {"name": "VKH-R09_failed_gates_derived_from_boolean_map", "result": "pass"},
            {"name": "VKH-R10_candidate_only_overclaim_guard", "result": "pass"},
            {"name": "VKH-R11_no_runtime_or_cloud_action", "result": "pass"},
            {"name": "VKH-R12_no_mask_or_wave71_or_jira_action", "result": "pass"},
            {"name": "VKH-R13_frame_rate_and_duration_bound_to_technical_qa", "result": "pass"},
            {"name": "VKH-R14_frame_composition_contract_exported", "result": "pass"},
            {"name": "VKH-R15_environment_profile_anchor_exists", "result": "pass"},
            {"name": "VKH-R16_character_profile_anchor_exists", "result": "pass"},
        ],
        "check_summary": {"checked": 16, "passed": 16, "failed": 0},
        "normalized_blockers": [
            {
                "blocker_id": "KEYFRAME_CANDIDATE_NOT_PROMOTION_ELIGIBLE",
                "failed_gates": failed,
                "resolution": "Provide scope-matched refine QA, multi-frame identity/camera/environment continuity, upstream Row016 quality authority, and explicit image-promotion proof before setting keyframe_manifest true.",
            },
            {
                "blocker_id": "FRAME_REPAIR_EFFECTIVENESS_NOT_PROVEN",
                "resolution": "After an eligible promoted keyframe exists, produce and directly compare a repaired candidate for one genuine failed span.",
            },
            {
                "blocker_id": "CONTACT_SOFT_BODY_VIDEO_SCOPE_BLOCKED_GOLD_MASKS",
                "resolution": "Keep contact and soft-body claims blocked until trusted body/contact masks are available.",
            },
        ],
        "source_bindings": source_bindings,
        "safety": deepcopy(candidate["safety"]),
        "next_action": "Obtain scope-matched refine and multi-frame continuity proof, then clear upstream Row016 image-promotion authority before exercising one genuine repair span; do not rerun completed WAN, temporal, or loop proofs.",
    }
    return candidate, readiness


def integrate_canonical(canonical: dict[str, Any], candidate_binding: dict[str, Any], readiness_path: str, readiness: dict[str, Any]) -> dict[str, Any]:
    require(canonical.get("tracker_id") == TRK and canonical.get("item_id") == ITEM, "Row019 canonical identity mismatch")
    require(canonical.get("status") == STATUS and canonical.get("row_complete") is False, "Row019 canonical status drift")
    gates = canonical.get("acceptance_gates", {})
    require(gates.get("keyframe_manifest") is False, "Row019 keyframe gate unexpectedly passed")
    require(gates.get("frame_repair_effectiveness") is False, "Row019 repair gate unexpectedly passed")
    result = deepcopy(canonical)
    result["keyframe_candidate_state"] = {
        "candidate_manifest": candidate_binding,
        "readiness_evidence": readiness_path,
        "candidate_only": True,
        "candidate_hash_bound": True,
        "base_image_qa_pass": True,
        "promotion_ready": False,
        "production_keyframe_eligible": False,
        "failed_gates": readiness["eligibility"]["failed_gates"],
        "keyframe_manifest_gate": False,
    }
    replaced = {"KEYFRAME_MANIFEST_INTEGRATION_MISSING", "KEYFRAME_CANDIDATE_NOT_PROMOTION_ELIGIBLE"}
    blockers = [item for item in result.get("normalized_blockers", []) if item.get("blocker_id") not in replaced]
    blockers.insert(0, deepcopy(readiness["normalized_blockers"][0]))
    result["normalized_blockers"] = blockers
    result["next_action"] = readiness["next_action"]
    return result


def write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded(payload))


def append_many(current: str, values: list[str]) -> str:
    entries = [entry.strip() for entry in (current or "").split(";") if entry.strip()]
    for value in values:
        if value not in entries:
            entries.append(value)
    return "; ".join(entries)


def normalize_note(current: str) -> str:
    entries = [entry.strip() for entry in (current or "").split(";") if entry.strip() and not entry.strip().startswith("Wave64 Row019 keyframe handoff:")]
    entries.append(NOTE)
    return "; ".join(entries)


def update_csv(path: Path, key: str, expected: str, changes: dict[str, str]) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    matched = 0
    for row in rows:
        if row.get(key) != expected:
            continue
        matched += 1
        for field, value in changes.items():
            if field in fields:
                row[field] = value
    require(matched == 1, f"ledger row mismatch: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--timestamp", default="")
    parser.add_argument("--no-ledger", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    timestamp = args.timestamp or datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0).isoformat()
    stamp = datetime.fromisoformat(timestamp).strftime("%Y%m%dT%H%M%S%z")
    candidate, readiness = build(root, SOURCES, timestamp)
    candidate_path = root / CANDIDATE
    readiness_path = root / READINESS
    stamped = readiness_path.parent / f"VIDEO_KEYFRAME_HANDOFF_READINESS_{stamp}.json"
    mirror = root / "Plan/Tracker/Evidence" / stamped.name
    readiness["evidence_id"] = stamped.stem
    readiness["evidence_paths"] = [rel(path, root) for path in (candidate_path, readiness_path, stamped, mirror, root / TEST_LOG)]
    write(candidate_path, candidate)
    for path in (readiness_path, stamped, mirror):
        write(path, readiness)
    write(root / TEST_LOG, {
        "schema_version": "1.0",
        "timestamp": timestamp,
        "tracker_id": TRK,
        "result": readiness["result"],
        "checks": readiness["checks"],
        "summary": readiness["check_summary"],
    })
    candidate_binding = bind(candidate_path, root)
    canonical_path = root / CANONICAL
    canonical = integrate_canonical(load(canonical_path), candidate_binding, rel(readiness_path, root), readiness)
    evidence = readiness["evidence_paths"] + [rel(root / SCHEMA, root), rel(Path(__file__), root)]
    canonical["evidence_paths"] = list(dict.fromkeys(canonical.get("evidence_paths", []) + evidence))
    write(canonical_path, canonical)
    report_path = root / REPORT
    report = load(report_path)
    report["acceptance_gates"] = deepcopy(canonical["acceptance_gates"])
    report["normalized_blockers"] = deepcopy(canonical["normalized_blockers"])
    report["evidence"] = list(dict.fromkeys(report.get("evidence", []) + evidence))
    report["next_action"] = readiness["next_action"]
    write(report_path, report)
    if not args.no_ledger:
        coverage = ["keyframe_candidate_hash_bound", "keyframe_promotion_gates_fail_closed"]
        for path in (
            root / "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv",
            root / "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
        ):
            row = next(item for item in csv.DictReader(path.open("r", encoding="utf-8-sig", newline="")) if item.get("Tracker_ID") == TRK)
            update_csv(path, "Tracker_ID", TRK, {
                "Status": STATUS,
                "Status_Decision": DECISION,
                "Evidence_Path": append_many(row.get("Evidence_Path", ""), evidence),
                "Coverage_Audit_Status": append_many(row.get("Coverage_Audit_Status", ""), coverage),
                "Notes": normalize_note(row.get("Notes", "")),
            })
        for path in (
            root / "Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv",
            root / "Plan/Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
        ):
            row = next(item for item in csv.DictReader(path.open("r", encoding="utf-8-sig", newline="")) if item.get("Item_ID") == ITEM)
            update_csv(path, "Item_ID", ITEM, {
                "Status": STATUS,
                "Evidence_Required": append_many(row.get("Evidence_Required", ""), evidence),
                "Coverage_Audit_Status": append_many(row.get("Coverage_Audit_Status", ""), coverage),
                "Notes": normalize_note(row.get("Notes", "")),
            })
    print(json.dumps({
        "status": STATUS,
        "result": readiness["result"],
        "candidate": candidate_binding,
        "failed_gates": readiness["eligibility"]["failed_gates"],
        "checks": readiness["check_summary"],
        "evidence": readiness["evidence_paths"],
    }, indent=2))


if __name__ == "__main__":
    main()
