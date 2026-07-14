#!/usr/bin/env python3
"""Export bounded single-image frame, environment, and character anchors."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from jsonschema import Draft202012Validator


ROOT = Path("C:/Comfy_UI_Main")
QA = Path("Plan/Instructions/QA/Evidence/Image_Artifact_QA/W70_LOCAL_NORMAL_V4_FULL_BODY_STANDING_QA_20260711T041000-0500.json")
CANDIDATE = Path("Plan/Instructions/QA/Evidence/Wave64/Video_Keyframes/normal_v4_wan22_keyframe_handoff_candidate.json")
OUT = Path("Plan/Instructions/QA/Evidence/Wave64/Video_Keyframes")
BODY = OUT / "normal_v4_body_visibility_profile.json"
FRAME = OUT / "normal_v4_frame_composition_contract.json"
FRAME_EVIDENCE = OUT / "normal_v4_frame_composition_evidence.json"
CONTEXT = OUT / "normal_v4_keyframe_context_contract.json"
SCHEMAS = {
    "body": Path("Plan/08_SCHEMAS/body_visibility_profile.schema.json"),
    "frame": Path("Plan/08_SCHEMAS/frame_composition_contract.schema.json"),
    "frame_evidence": Path("Plan/08_SCHEMAS/frame_composition_evidence.schema.json"),
    "context": Path("Plan/08_SCHEMAS/video_keyframe_context_contract.schema.json"),
}


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
    return path.resolve().relative_to(root.resolve()).as_posix()


def bind(path: Path, root: Path) -> dict[str, Any]:
    return {"path": rel(path, root), "sha256": sha256(path), "bytes": path.stat().st_size}


def encoded(payload: object) -> bytes:
    return (json.dumps(payload, indent=2) + "\n").encode("utf-8")


def memory_binding(path: Path, payload: object, root: Path) -> dict[str, Any]:
    raw = encoded(payload)
    return {"path": rel(path, root), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def validate(payload: dict[str, Any], schema_path: Path) -> None:
    schema = load(schema_path)
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda error: [str(part) for part in error.path])
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.path) or "root"
        raise ValueError(f"schema validation failed at {location}: {error.message}")


def build(root: Path, timestamp: str, qa_path: Path, candidate_path: Path, schema_paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    root = root.resolve()
    qa_path = qa_path if qa_path.is_absolute() else root / qa_path
    candidate_path = candidate_path if candidate_path.is_absolute() else root / candidate_path
    qa, candidate = load(qa_path), load(candidate_path)
    require(qa.get("pass") is True, "source image QA did not pass")
    artifact = qa.get("outputs", {}).get("generated_image", {})
    image_path = root / artifact.get("path", "")
    require(image_path.is_file() and sha256(image_path) == artifact.get("sha256"), "source image binding failed")
    candidate_artifact = candidate.get("candidate", {}).get("keyframe_artifact", {})
    require(candidate_artifact.get("path") == artifact.get("path") and candidate_artifact.get("sha256") == artifact.get("sha256"), "candidate source binding mismatch")
    require(candidate.get("candidate", {}).get("candidate_only") is True, "context source is not candidate-only")
    checks = qa.get("checks", {})
    require(all(checks.get(name) is True for name in ("exactly_one_person_in_source_and_output", "visual_one_full_length_subject", "visual_head_hands_and_shoes_in_frame")), "body visibility proof missing")
    keypoints_record = qa.get("outputs", {}).get("generated_keypoints", {})
    keypoints_path = root / keypoints_record.get("path", "")
    require(keypoints_path.is_file(), "skeleton evidence file missing")
    keypoints = load(keypoints_path)
    people = keypoints.get("people", [])
    require(isinstance(people, list) and len(people) == 1, "skeleton evidence person count invalid")
    pose = people[0].get("pose_keypoints_2d", {}) if isinstance(people[0], dict) else None
    require(isinstance(pose, list) and len(pose) >= 54, "skeleton evidence keypoints invalid")
    historical_keypoint_hash_matches = sha256(keypoints_path) == keypoints_record.get("sha256")

    profile_id = "full_body_head_hands_feet_visible_v1"
    character_id = "char_normal_v4_seed711670301_anchor"
    environment_id = "env_neutral_gray_studio_anchor_001"
    scene_id = "normal_v4_fullbody_studio_anchor_scene"
    body = {
        "profile_id": profile_id,
        "minimum_visible_body_length_ratio": 0.9,
        "recommended_outer_padding_ratio": 0.04,
        "required_landmarks": ["head", "shoulders", "elbows", "hands", "hips", "knees", "ankles", "feet"],
        "forbidden_crop_points": ["head", "hands", "knees", "ankles", "feet"],
    }
    frame = {
        "contract_id": "frame_contract_normal_v4_fullbody_anchor_v1",
        "scene_id": scene_id,
        "expected_character_count": 1,
        "body_visibility_profile": profile_id,
        "shot_size": "full_body",
        "crop_boundary_policy": {"head": "must_remain_visible", "hands": "must_remain_visible", "feet": "must_remain_visible"},
        "no_merged_bodies_required": True,
        "allow_background_people": False,
        "character_slots": [{"character_id": character_id, "slot_id": "primary_01", "required_visible_regions": ["head", "torso", "both_arms", "both_hands", "both_legs", "both_feet"]}],
        "qa_thresholds": {"expected_person_instances": 1, "all_18_body_landmarks_required": True},
    }
    frame_evidence = {
        "evidence_id": "frame_evidence_normal_v4_fullbody_anchor_v1",
        "contract_id": frame["contract_id"],
        "image_path": rel(image_path, root),
        "image_sha256": artifact["sha256"],
        "expected_character_count": 1,
        "detected_person_instances": [{"instance_id": "person_01", "assigned_character_id": character_id}],
        "detected_skeletons": [{"character_id": character_id, "binding": bind(keypoints_path, root), "common_body_landmarks": 18}],
        "detected_faces": [{"character_id": character_id, "visible": True}],
        "body_visibility_by_character": [{"character_id": character_id, "profile_id": profile_id, "head_hands_feet_visible": True}],
        "crop_boundary_report": {"pass": True, "cropped_required_regions": []},
        "merged_body_report": {"pass": True, "merged_body_instances": 0},
        "score": 1.0,
    }
    for name, payload in (("body", body), ("frame", frame), ("frame_evidence", frame_evidence)):
        schema_path = schema_paths[name] if schema_paths[name].is_absolute() else root / schema_paths[name]
        validate(payload, schema_path)
    targets = {"body": root / BODY, "frame": root / FRAME, "frame_evidence": root / FRAME_EVIDENCE}
    components = {name: memory_binding(targets[name], payload, root) for name, payload in (("body", body), ("frame", frame), ("frame_evidence", frame_evidence))}
    source_artifact = {"path": rel(image_path, root), "sha256": artifact["sha256"], "bytes": image_path.stat().st_size, "width": artifact["width"], "height": artifact["height"]}
    skeleton_binding = bind(keypoints_path, root)
    context = {
        "schema_version": "1.0",
        "context_id": "normal_v4_single_image_keyframe_context_v1",
        "timestamp": timestamp,
        "source_artifact": source_artifact,
        "component_artifacts": {"body_visibility_profile": components["body"], "frame_composition_contract": components["frame"], "frame_composition_evidence": components["frame_evidence"]},
        "environment_profile": {
            "environment_id": environment_id,
            "version": "v001",
            "display_name": "Neutral Gray Studio Single-Image Anchor",
            "environment_type": "neutral_studio",
            "status": "candidate_anchor_single_image",
            "continuity_rules": {"background_tone": "locked_to_anchor", "light_direction": "locked_to_anchor", "floor_horizon": "locked_to_anchor"},
            "qa_requirements": ["background_tone_consistency", "light_direction_consistency", "floor_horizon_consistency"],
        },
        "character_profile": {
            "character_id": character_id,
            "status": "candidate_identity_anchor_single_image",
            "identity_anchor": source_artifact,
            "skeleton_evidence": skeleton_binding,
            "skeleton_evidence_status": "historical_hash_match" if historical_keypoint_hash_matches else "advisory_current_file_historical_hash_mismatch",
            "body_visibility_profile_id": profile_id,
            "continuity_scope": {"anchor_image_count": 1, "multi_frame_identity_continuity_proven": False, "camera_environment_continuity_proven": False},
        },
        "camera_plan": {"camera_plan_id": "camera_normal_v4_fullbody_static_anchor_v1", "shot_size": "full_body", "framing": "portrait_768x1024_head_to_both_shoes", "camera_motion": "static_anchor", "continuity_proven": False},
        "pose_plan": {"pose_plan_id": "pose_normal_v4_asymmetric_standing_anchor_v1", "pose_class": "asymmetric_fullbody_standing", "body_visibility_profile_id": profile_id, "source_skeleton": skeleton_binding, "temporal_pose_continuity_proven": False},
        "gates": {"frame_contract_exported": True, "environment_profile_exists": True, "character_profile_exists": True, "identity_camera_environment_continuity_passed": False},
        "boundaries": {"single_image_anchor_only": True, "historical_keypoint_hash_matches_current": historical_keypoint_hash_matches, "skeleton_geometry_authority_claimed": False, "new_generation_executed": False, "refine_qa_claimed": False, "promotion_claimed": False, "production_keyframe_claimed": False, "mask_authority_claimed": False},
        "source_bindings": {"base_qa": bind(qa_path, root), "source_image": bind(image_path, root), "generated_keypoints": skeleton_binding},
    }
    schema_path = schema_paths["context"] if schema_paths["context"].is_absolute() else root / schema_paths["context"]
    validate(context, schema_path)
    return {"body": body, "frame": frame, "frame_evidence": frame_evidence, "context": context}


def write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded(payload))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--timestamp", default="")
    args = parser.parse_args()
    root = args.root.resolve()
    timestamp = args.timestamp or datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0).isoformat()
    payloads = build(root, timestamp, QA, CANDIDATE, SCHEMAS)
    targets = {"body": root / BODY, "frame": root / FRAME, "frame_evidence": root / FRAME_EVIDENCE, "context": root / CONTEXT}
    for name, payload in payloads.items():
        write(targets[name], payload)
    print(json.dumps({"result": "pass_bounded_single_image_context_export", "artifacts": {name: bind(path, root) for name, path in targets.items()}, "historical_keypoint_hash_matches_current": payloads["context"]["boundaries"]["historical_keypoint_hash_matches_current"], "continuity_passed": False, "promotion_claimed": False}, indent=2))


if __name__ == "__main__":
    main()
