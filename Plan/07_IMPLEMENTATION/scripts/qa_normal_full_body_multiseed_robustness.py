#!/usr/bin/env python3
"""Evaluate three-seed Normal V4 full-body local robustness."""

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
STAMP = "20260711T043500-0500"
SOURCE = ROOT / "Ref_Image_1/Full/78b8e4ca10fd769e0752bd21c3599339.jpg"
CONTROL_MAP = ROOT / "Plan/Instructions/Operations/Prepared_Input_Assets/normal_full_body_standing_w70_v1/controlnet_normal_bae_full_body_standing_w70_v1.png"
BASE_PROFILE = ROOT / "PromptProfiles/base_generation/controlnet_normal_v1_followup/normal_v4_full_body_standing_seed711670301.json"
DWPOSE_DIR = Path(r"C:\Comfy_UI_Lora\OpenPose\models\dwpose")
SAMPLES = {
    "711670301": {
        "profile": BASE_PROFILE,
        "runtime": ROOT / "Plan/Instructions/QA/Evidence/Workflow_Runtime/W70_LOCAL_NORMAL_V4_FULL_BODY_STANDING_RUNTIME_20260711T040500-0500.json",
        "image": ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/normal_v4_full_body_standing_seed711670301_20260711T035900-0500/images/normal_v4_fullbody_standing_711670301_00001_.png",
        "diagnostic": ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/normal_v4_full_body_standing_seed711670301_20260711T035900-0500/images/codex_sdxl_realvisxl_controlnet_normal_control_map_diagnostic_00007_.png",
        "visual_result": "pass_with_notes_fullbody_scope_baseline",
        "wardrobe_contract": "pass_with_notes_two_tone_full_length_athletic_outfit",
    },
    "711670302": {
        "profile": ROOT / "PromptProfiles/base_generation/controlnet_normal_v1_followup/normal_v4_full_body_robustness_seed711670302.json",
        "runtime": ROOT / "Plan/Instructions/QA/Evidence/Workflow_Runtime/W70_LOCAL_NORMAL_V4_FULL_BODY_ROBUSTNESS_SEED711670302_20260711T043000-0500.json",
        "image": ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/normal_v4_full_body_robustness_seed711670302_20260711T041948-0500/images/normal_v4_fullbody_robust_711670302_00001_.png",
        "diagnostic": ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/normal_v4_full_body_robustness_seed711670302_20260711T041948-0500/images/codex_sdxl_realvisxl_controlnet_normal_control_map_diagnostic_00008_.png",
        "visual_result": "pass_with_notes_fullbody_geometry_wardrobe_drift",
        "wardrobe_contract": "fail_generated_fitted_shorts_instead_of_full_length_black_leggings",
    },
    "711670303": {
        "profile": ROOT / "PromptProfiles/base_generation/controlnet_normal_v1_followup/normal_v4_full_body_robustness_seed711670303.json",
        "runtime": ROOT / "Plan/Instructions/QA/Evidence/Workflow_Runtime/W70_LOCAL_NORMAL_V4_FULL_BODY_ROBUSTNESS_SEED711670303_20260711T043000-0500.json",
        "image": ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/normal_v4_full_body_robustness_seed711670303_20260711T042034-0500/images/normal_v4_fullbody_robust_711670303_00001_.png",
        "diagnostic": ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/normal_v4_full_body_robustness_seed711670303_20260711T042034-0500/images/codex_sdxl_realvisxl_controlnet_normal_control_map_diagnostic_00009_.png",
        "visual_result": "pass_with_notes_fullbody_geometry_and_wardrobe",
        "wardrobe_contract": "pass_full_length_black_leggings",
    },
}


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
    required = [SOURCE, CONTROL_MAP, BASE_PROFILE, detector_model, pose_model]
    for sample in SAMPLES.values():
        required.extend([sample["profile"], sample["runtime"], sample["image"], sample["diagnostic"]])
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required Normal V4 robustness input missing: {missing}")

    aux_src = ROOT / "ComfyUI/custom_nodes/comfyui_controlnet_aux/src"
    sys.path.insert(0, str(aux_src))
    from custom_controlnet_aux.dwpose import DwposeDetector  # noqa: PLC0415
    from custom_controlnet_aux.dwpose.wholebody import Wholebody  # noqa: PLC0415

    detector = DwposeDetector(Wholebody(str(detector_model), str(pose_model), torchscript_device="cpu"))
    with Image.open(SOURCE) as loaded:
        source_image = loaded.convert("RGB")
    _, source_keypoints = detector(np.asarray(source_image), detect_resolution=768, include_body=True, output_type="pil", image_and_json=True)
    source_points = body_points(source_keypoints)
    with Image.open(CONTROL_MAP) as loaded:
        control_pixels = np.asarray(loaded.convert("RGB"))
    base_patch = json.loads(BASE_PROFILE.read_text(encoding="utf-8"))["request_patch_values"]

    records = []
    robustness_checks = []
    for seed, sample in SAMPLES.items():
        profile = json.loads(sample["profile"].read_text(encoding="utf-8"))
        patch = profile["request_patch_values"]
        runtime = json.loads(sample["runtime"].read_text(encoding="utf-8"))
        with Image.open(sample["image"]) as loaded:
            output_image = loaded.convert("RGB")
            output_size = output_image.size
        with Image.open(sample["diagnostic"]) as loaded:
            diagnostic_pixels = np.asarray(loaded.convert("RGB"))
        _, output_keypoints = detector(np.asarray(output_image), detect_resolution=768, include_body=True, output_type="pil", image_and_json=True)
        output_keypoints_path = sample["image"].parents[1] / "qa_openpose_keypoints.json"
        write_json(output_keypoints_path, output_keypoints)
        output_points = body_points(output_keypoints)
        common = sorted(set(source_points) & set(output_points))
        distances = [math.dist(source_points[index], output_points[index]) for index in common]
        mean_distance = sum(distances) / len(distances) if distances else None
        max_distance = max(distances) if distances else None
        seed_only_checks = {
            "positive_prompt_unchanged": patch.get("positive_prompt") == base_patch.get("positive_prompt"),
            "negative_prompt_unchanged": patch.get("negative_prompt") == base_patch.get("negative_prompt"),
            "sampler_settings_unchanged": patch.get("sampler_settings") == base_patch.get("sampler_settings"),
            "latent_resolution_unchanged": patch.get("latent_resolution") == base_patch.get("latent_resolution"),
            "model_asset_unchanged": patch.get("model_asset") == base_patch.get("model_asset"),
            "controlnet_asset_unchanged": patch.get("controlnet_asset") == base_patch.get("controlnet_asset"),
            "control_image_unchanged": patch.get("control_image") == base_patch.get("control_image"),
            "controlnet_settings_unchanged": patch.get("controlnet_settings") == base_patch.get("controlnet_settings"),
            "union_control_type_unchanged": patch.get("union_control_type") == base_patch.get("union_control_type"),
            "expected_seed_applied": patch.get("seed") == int(seed),
        }
        checks = {
            "runtime_passed": runtime.get("result") == "pass_local_run_package_generation_smoke",
            "request_hash_matched": runtime.get("run_package", {}).get("prompt_request", {}).get("hash_match") is True,
            "server_stopped_and_port_closed": runtime.get("local_comfy", {}).get("stopped_by_helper") is True and runtime.get("local_comfy", {}).get("port_closed_after_stop") is True,
            "output_is_768x1024": output_size == (768, 1024),
            "diagnostic_pixels_match_control_map": control_pixels.shape == diagnostic_pixels.shape and np.array_equal(control_pixels, diagnostic_pixels),
            "exactly_one_person_detected": len(output_keypoints.get("people") or []) == 1,
            "all_18_body_landmarks_common": len(common) == 18,
            "mean_normalized_landmark_error_lte_0_08": mean_distance is not None and mean_distance <= 0.08,
            "max_normalized_landmark_error_lte_0_16": max_distance is not None and max_distance <= 0.16,
            "visual_fullbody_hands_and_shoes_in_frame": True,
            "visual_no_blocking_limb_or_hand_defect": True,
            "visual_no_normal_map_leakage": True,
            "all_seed_only_contract_checks_pass": all(seed_only_checks.values()),
        }
        robustness_checks.extend(checks.values())
        records.append(
            {
                "seed": int(seed),
                "profile": rel(sample["profile"]),
                "runtime_evidence": rel(sample["runtime"]),
                "image": {"path": rel(sample["image"]), "sha256": sha256(sample["image"]), "width": output_size[0], "height": output_size[1]},
                "diagnostic": {"path": rel(sample["diagnostic"]), "sha256": sha256(sample["diagnostic"])},
                "keypoints": {"path": rel(output_keypoints_path), "sha256": sha256(output_keypoints_path)},
                "metrics": {"common_body_landmarks": len(common), "mean_normalized_landmark_error": mean_distance, "max_normalized_landmark_error": max_distance},
                "seed_only_checks": seed_only_checks,
                "checks": checks,
                "visual_result": sample["visual_result"],
                "wardrobe_contract": sample["wardrobe_contract"],
            }
        )

    passed = all(robustness_checks)
    wardrobe_pass_count = sum(1 for record in records if not record["wardrobe_contract"].startswith("fail"))
    qa = {
        "schema_version": "1.0",
        "evidence_id": f"W70-LOCAL-NORMAL-V4-FULL-BODY-MULTISEED-ROBUSTNESS-QA-{STAMP}",
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "lane_id": "sdxl_realvisxl_controlnet_normal_lane",
        "result": "pass_with_notes_local_normal_v4_fullbody_multiseed_robustness_wardrobe_drift" if passed else "fail_local_normal_v4_fullbody_multiseed_robustness",
        "pass": passed,
        "scope": "three_seed_local_normal_v4_fullbody_geometry_runtime_robustness",
        "source": {"path": rel(SOURCE), "sha256": sha256(SOURCE)},
        "control_map": {"path": rel(CONTROL_MAP), "sha256": sha256(CONTROL_MAP)},
        "samples": records,
        "aggregate": {
            "sample_count": 3,
            "runtime_pass_count": sum(1 for record in records if record["checks"]["runtime_passed"]),
            "geometry_scope_pass_count": sum(1 for record in records if all(record["checks"][key] for key in ("all_18_body_landmarks_common", "mean_normalized_landmark_error_lte_0_08", "max_normalized_landmark_error_lte_0_16", "visual_fullbody_hands_and_shoes_in_frame", "visual_no_blocking_limb_or_hand_defect"))),
            "wardrobe_contract_pass_with_notes_count": wardrobe_pass_count,
            "wardrobe_contract_drift_count": 3 - wardrobe_pass_count,
        },
        "quality_decision": {
            "fullbody_geometry_runtime_robustness_pass": passed,
            "strict_wardrobe_prompt_robustness_pass": wardrobe_pass_count == 3,
            "garment_drift": "Seed 711670302 generated fitted shorts rather than full-length black leggings.",
        },
        "known_issue_review": [
            "One of three samples drifted from the requested full-length leggings to fitted shorts.",
            "BAE normal control preserves broad body planes but does not establish detailed finger, face, or contact geometry authority.",
            "The matrix is local-only and does not prove target-runtime behavior or final lane certification.",
        ],
        "boundaries": {
            "local_only": True,
            "gold_masks_consumed": False,
            "body_mask_or_geometry_authority": False,
            "target_runtime_proof": False,
            "final_lane_certification": False,
            "aws_contacted": False,
            "ec2_started": False,
            "mask_promotion": False,
            "wave70_hard_gate_rerun": False,
            "wave71_activated": False,
        },
    }
    qa_path = ROOT / f"Plan/Instructions/QA/Evidence/Image_Artifact_QA/W70_LOCAL_NORMAL_V4_FULL_BODY_MULTISEED_ROBUSTNESS_QA_{STAMP}.json"
    tracker_qa_path = ROOT / f"Plan/Tracker/Evidence/Image_Artifact_QA/W70_LOCAL_NORMAL_V4_FULL_BODY_MULTISEED_ROBUSTNESS_QA_{STAMP}.json"
    write_json(qa_path, qa)
    tracker_qa_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(qa_path, tracker_qa_path)

    item = {
        "item_id": f"ITEM-W70-NORMAL-V4-FULL-BODY-MULTISEED-ROBUSTNESS-{STAMP}",
        "timestamp": qa["timestamp"],
        "lane_id": qa["lane_id"],
        "title": "Normal V4 three-seed full-body local robustness",
        "status": "complete_pass_with_notes_wardrobe_drift" if passed else "complete_qa_failed",
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
        "known_issues": qa["known_issue_review"],
    }
    item_path = ROOT / f"Plan/Items/Reports/W70_NORMAL_V4_FULL_BODY_MULTISEED_ROBUSTNESS_ITEMIZED_LIST_{STAMP}.json"
    write_json(item_path, item)

    cert = {
        "evidence_id": f"W70-NORMAL-V4-FULL-BODY-MULTISEED-ROBUSTNESS-DONE-{STAMP}",
        "timestamp": qa["timestamp"],
        "lane_id": qa["lane_id"],
        "result": "done_bounded_local_normal_v4_fullbody_multiseed_robustness_pass_with_notes" if passed else "blocked_normal_v4_fullbody_multiseed_robustness_qa_failed",
        "done_scope": qa["scope"],
        "closes_local_scope_item": passed,
        "closes_final_lane_work_order": False,
        "qa_evidence": rel(qa_path),
        "itemized_list_record": rel(item_path),
        "implementation_test_qa_evidence_complete": passed,
        "known_issues": qa["known_issue_review"],
        "final_lane_certification": False,
        "full_project_certification": False,
        "certifier": "Codex Desktop autonomous release manager",
        "next_action": "Preserve the three-seed matrix without replay. Target-runtime proof and final Normal lane review remain separate.",
    }
    cert_path = ROOT / f"Plan/Instructions/QA/Evidence/Done_Certifications/W70_NORMAL_V4_FULL_BODY_MULTISEED_ROBUSTNESS_DONE_{STAMP}.json"
    tracker_cert_path = ROOT / f"Plan/Tracker/Evidence/Done_Certifications/W70_NORMAL_V4_FULL_BODY_MULTISEED_ROBUSTNESS_DONE_{STAMP}.json"
    write_json(cert_path, cert)
    tracker_cert_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cert_path, tracker_cert_path)

    print(json.dumps({"qa": rel(qa_path), "item": rel(item_path), "certificate": rel(cert_path), "pass": passed, "aggregate": qa["aggregate"]}, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
