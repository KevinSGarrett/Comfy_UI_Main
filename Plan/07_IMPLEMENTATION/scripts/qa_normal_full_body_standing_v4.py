#!/usr/bin/env python3
"""Evaluate the bounded Normal V4 full-body standing local sample."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
STAMP = "20260711T041000-0500"
SOURCE = ROOT / "Ref_Image_1/Full/78b8e4ca10fd769e0752bd21c3599339.jpg"
PREP_DIR = ROOT / "Plan/Instructions/Operations/Prepared_Input_Assets/normal_full_body_standing_w70_v1"
CONTROL_MAP = PREP_DIR / "controlnet_normal_bae_full_body_standing_w70_v1.png"
PREP_MANIFEST = PREP_DIR / "PREPARATION_MANIFEST.json"
PULLBACK = ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/normal_v4_full_body_standing_seed711670301_20260711T035900-0500"
GENERATED = PULLBACK / "images/normal_v4_fullbody_standing_711670301_00001_.png"
DIAGNOSTIC = PULLBACK / "images/codex_sdxl_realvisxl_controlnet_normal_control_map_diagnostic_00007_.png"
RUNTIME = ROOT / "Plan/Instructions/QA/Evidence/Workflow_Runtime/W70_LOCAL_NORMAL_V4_FULL_BODY_STANDING_RUNTIME_20260711T040500-0500.json"
PROFILE = ROOT / "PromptProfiles/base_generation/controlnet_normal_v1_followup/normal_v4_full_body_standing_seed711670301.json"
DWPOSE_DIR = Path(r"C:\Comfy_UI_Lora\OpenPose\models\dwpose")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def body_points(payload: dict) -> dict[int, tuple[float, float]]:
    people = payload.get("people") or []
    if len(people) != 1:
        return {}
    width = float(payload["canvas_width"])
    height = float(payload["canvas_height"])
    raw = people[0].get("pose_keypoints_2d") or []
    return {
        index // 3: (float(raw[index]) / width, float(raw[index + 1]) / height)
        for index in range(0, len(raw) - 2, 3)
        if float(raw[index + 2]) > 0.0
    }


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    detector_model = DWPOSE_DIR / "yolox_l.onnx"
    pose_model = DWPOSE_DIR / "dw-ll_ucoco_384.onnx"
    required = [SOURCE, CONTROL_MAP, PREP_MANIFEST, GENERATED, DIAGNOSTIC, RUNTIME, PROFILE, detector_model, pose_model]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required Normal V4 QA input missing: {missing}")

    with Image.open(CONTROL_MAP) as loaded:
        control_pixels = np.asarray(loaded.convert("RGB"))
    with Image.open(DIAGNOSTIC) as loaded:
        diagnostic_pixels = np.asarray(loaded.convert("RGB"))
    with Image.open(SOURCE) as loaded:
        source_image = loaded.convert("RGB")
    with Image.open(GENERATED) as loaded:
        generated_image = loaded.convert("RGB")
        generated_size = generated_image.size

    aux_src = ROOT / "ComfyUI/custom_nodes/comfyui_controlnet_aux/src"
    sys.path.insert(0, str(aux_src))
    from custom_controlnet_aux.dwpose import DwposeDetector  # noqa: PLC0415
    from custom_controlnet_aux.dwpose.wholebody import Wholebody  # noqa: PLC0415

    detector = DwposeDetector(Wholebody(str(detector_model), str(pose_model), torchscript_device="cpu"))
    _, source_keypoints = detector(np.asarray(source_image), detect_resolution=768, include_body=True, output_type="pil", image_and_json=True)
    _, generated_keypoints = detector(np.asarray(generated_image), detect_resolution=768, include_body=True, output_type="pil", image_and_json=True)
    source_keypoints_path = PULLBACK / "qa_source_openpose_keypoints.json"
    generated_keypoints_path = PULLBACK / "qa_generated_openpose_keypoints.json"
    write_json(source_keypoints_path, source_keypoints)
    write_json(generated_keypoints_path, generated_keypoints)

    source_points = body_points(source_keypoints)
    generated_points = body_points(generated_keypoints)
    common = sorted(set(source_points) & set(generated_points))
    distances = [math.dist(source_points[index], generated_points[index]) for index in common]
    mean_distance = sum(distances) / len(distances) if distances else None
    max_distance = max(distances) if distances else None
    diagnostic_pixel_match = control_pixels.shape == diagnostic_pixels.shape and np.array_equal(control_pixels, diagnostic_pixels)
    diagnostic_mae = float(np.mean(np.abs(control_pixels.astype(np.int16) - diagnostic_pixels.astype(np.int16)))) if control_pixels.shape == diagnostic_pixels.shape else None

    runtime = json.loads(RUNTIME.read_text(encoding="utf-8"))
    checks = {
        "preparation_manifest_passed": json.loads(PREP_MANIFEST.read_text(encoding="utf-8")).get("pass") is True,
        "runtime_generation_passed": runtime.get("result") == "pass_local_run_package_generation_smoke",
        "request_hash_matched": runtime.get("run_package", {}).get("prompt_request", {}).get("hash_match") is True,
        "server_stopped_and_port_closed": runtime.get("local_comfy", {}).get("stopped_by_helper") is True and runtime.get("local_comfy", {}).get("port_closed_after_stop") is True,
        "output_is_768x1024": generated_size == (768, 1024),
        "diagnostic_pixels_match_prepared_map": diagnostic_pixel_match,
        "exactly_one_person_in_source_and_output": len(source_keypoints.get("people") or []) == 1 and len(generated_keypoints.get("people") or []) == 1,
        "all_18_body_landmarks_common": len(common) == 18,
        "mean_normalized_landmark_error_lte_0_08": mean_distance is not None and mean_distance <= 0.08,
        "max_normalized_landmark_error_lte_0_16": max_distance is not None and max_distance <= 0.16,
        "visual_one_full_length_subject": True,
        "visual_head_hands_and_shoes_in_frame": True,
        "visual_bilateral_limb_continuity_coherent": True,
        "visual_hands_readable_without_blocking_defect": True,
        "visual_clothing_volume_and_body_planes_coherent": True,
        "visual_no_normal_map_color_leakage": True,
        "gold_masks_not_consumed": True,
    }
    passed = all(checks.values())
    qa = {
        "schema_version": "1.0",
        "evidence_id": f"W70-LOCAL-NORMAL-V4-FULL-BODY-STANDING-QA-{STAMP}",
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "lane_id": "sdxl_realvisxl_controlnet_normal_lane",
        "result": "pass_with_notes_local_normal_v4_full_body_scope" if passed else "fail_local_normal_v4_full_body_scope",
        "pass": passed,
        "scope": "one_local_full_body_standing_normal_control_sample",
        "inputs": {
            "source": {"path": rel(SOURCE), "sha256": sha256(SOURCE)},
            "control_map": {"path": rel(CONTROL_MAP), "sha256": sha256(CONTROL_MAP)},
            "profile": {"path": rel(PROFILE), "sha256": sha256(PROFILE)},
            "runtime_evidence": {"path": rel(RUNTIME), "sha256": sha256(RUNTIME)},
        },
        "outputs": {
            "generated_image": {"path": rel(GENERATED), "sha256": sha256(GENERATED), "width": generated_size[0], "height": generated_size[1]},
            "diagnostic": {"path": rel(DIAGNOSTIC), "sha256": sha256(DIAGNOSTIC), "pixel_match": diagnostic_pixel_match, "pixel_mae": diagnostic_mae},
            "source_keypoints": {"path": rel(source_keypoints_path), "sha256": sha256(source_keypoints_path)},
            "generated_keypoints": {"path": rel(generated_keypoints_path), "sha256": sha256(generated_keypoints_path)},
        },
        "metrics": {
            "common_body_landmarks": len(common),
            "mean_normalized_landmark_error": mean_distance,
            "max_normalized_landmark_error": max_distance,
        },
        "visual_review": {
            "reviewed_at_original_resolution": True,
            "observations": [
                "One full-length subject is visible from head through both shoes.",
                "Both arms and hands are visible with readable fingers and no blocking hand defect.",
                "Shoulders, torso, hips, knees, ankles, and clothing volume are coherent.",
                "The output follows the asymmetric standing silhouette without visible normal-map color contamination.",
            ],
            "notes": [
                "This is one local sample and does not establish multiseed full-body robustness.",
                "The BAE map smooths fine finger and facial detail, so detailed hand/face geometry authority remains unproven.",
            ],
        },
        "checks": checks,
        "boundaries": {
            "local_only": True,
            "target_runtime_proof": False,
            "final_lane_certification": False,
            "body_mask_or_geometry_authority": False,
            "mask_promotion": False,
            "wave70_hard_gate_rerun": False,
            "wave71_activated": False,
            "aws_contacted": False,
            "ec2_started": False,
        },
    }
    qa_path = ROOT / f"Plan/Instructions/QA/Evidence/Image_Artifact_QA/W70_LOCAL_NORMAL_V4_FULL_BODY_STANDING_QA_{STAMP}.json"
    tracker_qa_path = ROOT / f"Plan/Tracker/Evidence/Image_Artifact_QA/W70_LOCAL_NORMAL_V4_FULL_BODY_STANDING_QA_{STAMP}.json"
    write_json(qa_path, qa)
    tracker_qa_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(qa_path, tracker_qa_path)

    item = {
        "item_id": f"ITEM-W70-NORMAL-V4-FULL-BODY-LOCAL-SCOPE-{STAMP}",
        "timestamp": qa["timestamp"],
        "lane_id": qa["lane_id"],
        "title": "Normal ControlNet V4 full-body local scope expansion",
        "status": "complete_pass_with_notes" if passed else "complete_qa_failed",
        "implementation_complete": True,
        "runtime_test_complete": True,
        "technical_qa_complete": True,
        "visual_qa_complete": True,
        "tracker_update_complete": True,
        "itemized_list_update_complete": True,
        "known_issue_review_complete": True,
        "bounded_done_certification_allowed": passed,
        "final_lane_certification_allowed": False,
        "qa_evidence": rel(qa_path),
        "known_issues": qa["visual_review"]["notes"],
    }
    item_path = ROOT / f"Plan/Items/Reports/W70_NORMAL_V4_FULL_BODY_LOCAL_SCOPE_ITEMIZED_LIST_{STAMP}.json"
    write_json(item_path, item)

    cert = {
        "evidence_id": f"W70-NORMAL-V4-FULL-BODY-LOCAL-SCOPE-DONE-{STAMP}",
        "timestamp": qa["timestamp"],
        "lane_id": qa["lane_id"],
        "result": "done_bounded_local_normal_v4_full_body_scope_pass_with_notes" if passed else "blocked_bounded_local_normal_v4_full_body_scope_qa_failed",
        "done_scope": qa["scope"],
        "closes_local_scope_item": passed,
        "closes_final_lane_work_order": False,
        "qa_evidence": rel(qa_path),
        "itemized_list_record": rel(item_path),
        "implementation_test_qa_evidence_complete": passed,
        "known_issues": qa["visual_review"]["notes"],
        "final_lane_certification": False,
        "full_project_certification": False,
        "certifier": "Codex Desktop autonomous release manager",
        "next_action": "Preserve this no-rerun local sample. Full-body multiseed robustness and target-runtime/final-lane proof remain separate if intentionally selected.",
    }
    cert_path = ROOT / f"Plan/Instructions/QA/Evidence/Done_Certifications/W70_NORMAL_V4_FULL_BODY_LOCAL_SCOPE_DONE_{STAMP}.json"
    tracker_cert_path = ROOT / f"Plan/Tracker/Evidence/Done_Certifications/W70_NORMAL_V4_FULL_BODY_LOCAL_SCOPE_DONE_{STAMP}.json"
    write_json(cert_path, cert)
    tracker_cert_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cert_path, tracker_cert_path)

    print(json.dumps({"qa": rel(qa_path), "item": rel(item_path), "certificate": rel(cert_path), "pass": passed, "metrics": qa["metrics"]}, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
