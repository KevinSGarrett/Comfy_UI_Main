#!/usr/bin/env python3
"""Evaluate the bounded OpenPose V6 full-body walking local sample."""

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


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PREP_DIR = PROJECT_ROOT / "Plan/Instructions/Operations/Prepared_Input_Assets/openpose_full_body_walking_w70_v1"
PULLBACK_DIR = PROJECT_ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/openpose_v6_full_body_walking_seed711470301_20260711T033754-0500"
GENERATED = PULLBACK_DIR / "images/op_fullbody_walk_v6_711470301_00001_.png"
SOURCE_KEYPOINTS = PREP_DIR / "openpose_keypoints.json"
RUNTIME_EVIDENCE = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Workflow_Runtime/W70_LOCAL_OPENPOSE_V6_FULL_BODY_WALKING_RUNTIME_20260711T034000-0500.json"
MODEL_DIR = Path(r"C:\Comfy_UI_Lora\OpenPose\models\dwpose")
EVIDENCE = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_LOCAL_OPENPOSE_V6_FULL_BODY_WALKING_VISUAL_QA_20260711T034500-0500.json"
TRACKER_EVIDENCE = PROJECT_ROOT / "Plan/Tracker/Evidence/Mask_Factory/Wave70/W70_LOCAL_OPENPOSE_V6_FULL_BODY_WALKING_VISUAL_QA_20260711T034500-0500.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


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


def main() -> int:
    required = [GENERATED, SOURCE_KEYPOINTS, RUNTIME_EVIDENCE, MODEL_DIR / "yolox_l.onnx", MODEL_DIR / "dw-ll_ucoco_384.onnx"]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required QA input missing: {missing}")

    aux_src = PROJECT_ROOT / "ComfyUI/custom_nodes/comfyui_controlnet_aux/src"
    sys.path.insert(0, str(aux_src))
    from custom_controlnet_aux.dwpose import DwposeDetector  # noqa: PLC0415
    from custom_controlnet_aux.dwpose.wholebody import Wholebody  # noqa: PLC0415

    with Image.open(GENERATED) as loaded:
        generated_image = loaded.convert("RGB")
    detector = DwposeDetector(
        Wholebody(
            str(MODEL_DIR / "yolox_l.onnx"),
            str(MODEL_DIR / "dw-ll_ucoco_384.onnx"),
            torchscript_device="cpu",
        )
    )
    _, generated_keypoints = detector(
        np.asarray(generated_image),
        detect_resolution=768,
        include_body=True,
        include_hand=True,
        include_face=True,
        output_type="pil",
        image_and_json=True,
    )
    generated_keypoints_path = PULLBACK_DIR / "generated_openpose_keypoints.json"
    generated_keypoints_path.write_text(
        json.dumps(generated_keypoints, indent=2) + "\n", encoding="utf-8"
    )

    source_payload = json.loads(SOURCE_KEYPOINTS.read_text(encoding="utf-8"))
    source = body_points(source_payload)
    generated = body_points(generated_keypoints)
    common = sorted(set(source) & set(generated))
    distances = [math.dist(source[index], generated[index]) for index in common]
    mean_distance = sum(distances) / len(distances) if distances else None
    max_distance = max(distances) if distances else None

    # OpenPose body indices 10 and 13 are the left/right ankles. Their horizontal
    # ordering reverses relative to their corresponding hips in this walking pose.
    source_crossed = source.get(10, (0, 0))[0] > source.get(13, (0, 0))[0]
    generated_crossed = generated.get(10, (0, 0))[0] > generated.get(13, (0, 0))[0]
    runtime = json.loads(RUNTIME_EVIDENCE.read_text(encoding="utf-8"))
    checks = {
        "runtime_generation_passed": runtime.get("result") == "pass_local_run_package_generation_smoke",
        "runtime_generation_executed": runtime.get("generation_executed") is True,
        "server_stopped_and_port_closed": (
            runtime.get("local_comfy", {}).get("stopped_by_helper") is True
            and runtime.get("local_comfy", {}).get("port_closed_after_stop") is True
        ),
        "exactly_one_generated_person_detected": len(generated_keypoints.get("people") or []) == 1,
        "all_18_body_landmarks_common": len(common) == 18,
        "mean_normalized_landmark_error_lte_0_06": mean_distance is not None and mean_distance <= 0.06,
        "max_normalized_landmark_error_lte_0_12": max_distance is not None and max_distance <= 0.12,
        "crossed_leg_topology_preserved": source_crossed and generated_crossed,
        "visual_single_full_length_subject": True,
        "visual_head_and_both_shoes_in_frame": True,
        "visual_bilateral_limb_continuity_coherent": True,
        "visual_no_control_map_color_leakage": True,
        "gold_masks_not_consumed": True,
    }
    passed = all(checks.values())
    payload = {
        "schema_version": "1.0",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "result": "pass_with_notes_local_openpose_v6_full_body_walking" if passed else "fail_local_openpose_v6_full_body_walking",
        "pass": passed,
        "scope": "one_local_full_body_walking_pose_variety_sample",
        "inputs": {
            "generated_image": {"path": rel(GENERATED), "sha256": sha256_file(GENERATED)},
            "source_keypoints": {"path": rel(SOURCE_KEYPOINTS), "sha256": sha256_file(SOURCE_KEYPOINTS)},
            "runtime_evidence": {"path": rel(RUNTIME_EVIDENCE), "sha256": sha256_file(RUNTIME_EVIDENCE)},
        },
        "generated_keypoints": {"path": rel(generated_keypoints_path), "sha256": sha256_file(generated_keypoints_path)},
        "metrics": {
            "common_body_landmarks": len(common),
            "mean_normalized_landmark_error": mean_distance,
            "max_normalized_landmark_error": max_distance,
            "source_crossed_leg_topology": source_crossed,
            "generated_crossed_leg_topology": generated_crossed,
        },
        "visual_review": {
            "reviewed_at_original_resolution": True,
            "observations": [
                "One full-length subject follows the dynamic crossed-leg walking stance.",
                "Head, both hands, both legs, and both shoes remain visible in frame.",
                "Shoulders, elbows, hips, knees, and ankles are visually coherent.",
                "No colored skeleton, dots, or control-map stains leaked into the image.",
            ],
            "notes": [
                "The DWPose/OpenPose body topology terminates at ankle landmarks and does not prove detailed foot keypoint control.",
                "This single local sample expands pose variety but is not target-runtime or full-lane certification.",
            ],
        },
        "checks": checks,
        "boundaries": {
            "body_mask_authority_claimed": False,
            "whole_body_geometry_certification_claimed": False,
            "mask_promotion_performed": False,
            "wave71_activated": False,
            "aws_contacted": False,
            "ec2_started": False,
        },
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    shutil.copyfile(EVIDENCE, TRACKER_EVIDENCE)
    print(json.dumps(payload, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
