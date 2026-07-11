#!/usr/bin/env python3
"""Evaluate one compiler-driven Wave10 camera runtime sample fail-closed."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from compile_camera_plan import compile_plan, compile_prompt_profile


ROOT = Path(__file__).resolve().parents[3]
EXPECTED_LANE = "sdxl_realvisxl_base_lane"
EXPECTED_MODEL = "realvisxlV50_v50Bakedvae.safetensors"
EXPECTED_SEED = 7152026101
EXPECTED_DIMENSIONS = (768, 1024)
EXPECTED_STEPS = 24
EXPECTED_CFG = 5.5
EXPECTED_SAMPLER = "dpmpp_2m"
EXPECTED_SCHEDULER = "karras"
EXPECTED_DENOISE = 1.0
EXPECTED_SAVE_PREFIX = "wave10_camera_full_body_7152026101"
EXPECTED_DWPOSE_MODEL_SHA256 = {
    "yolox_l.onnx": "7860ae79de6c89a3c1eb72ae9a2756c0ccfbe04b7791bb5880afabd97855a411",
    "dw-ll_ucoco_384.onnx": "724f4ff2439ed61afb86fb8a1951ec39c6220682803b4a8bd4f598cd913b1843",
}
REQUIRED_VISUAL_CHECKS = frozenset(
    {
        "exactly_one_adult",
        "eye_level_full_body_camera_intent",
        "head_and_hair_fully_in_frame",
        "both_hands_fully_visible_and_inspectable",
        "both_feet_fully_in_frame",
        "balanced_headroom_footroom_and_side_margins",
        "no_required_region_hidden",
        "natural_skin_clothing_and_background",
        "no_obvious_anatomy_or_render_defect",
    }
)
REQUIRED_FRAMING_KEYPOINTS = (0, 4, 7, 10, 13)


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


def resolve_path(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"JSON object required: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def nodes_of_type(graph: dict[str, Any], class_type: str) -> list[dict[str, Any]]:
    return [
        node
        for node in graph.values()
        if isinstance(node, dict) and node.get("class_type") == class_type
    ]


def single_node(graph: dict[str, Any], class_type: str) -> dict[str, Any]:
    nodes = nodes_of_type(graph, class_type)
    if len(nodes) != 1:
        raise ValueError(f"Expected exactly one {class_type}, found {len(nodes)}")
    return nodes[0]


def body_points(payload: dict[str, Any]) -> dict[int, tuple[float, float]]:
    people = payload.get("people") or []
    if len(people) != 1:
        return {}
    width = float(payload.get("canvas_width") or 0)
    height = float(payload.get("canvas_height") or 0)
    if width <= 0 or height <= 0:
        return {}
    raw = people[0].get("pose_keypoints_2d") or []
    return {
        index // 3: (float(raw[index]) / width, float(raw[index + 1]) / height)
        for index in range(0, len(raw) - 2, 3)
        if float(raw[index + 2]) > 0.0
    }


def framing_keypoints_in_frame(points: dict[int, tuple[float, float]]) -> bool:
    return all(
        index in points
        and 0.01 <= points[index][0] <= 0.99
        and 0.01 <= points[index][1] <= 0.99
        for index in REQUIRED_FRAMING_KEYPOINTS
    )


def nonblank_metrics(image: Image.Image) -> dict[str, Any]:
    pixels = np.asarray(image.convert("RGB"), dtype=np.float32)
    gray = pixels.mean(axis=2)
    std = float(gray.std())
    nonwhite_ratio = float(np.mean(gray < 250.0))
    nonblack_ratio = float(np.mean(gray > 4.0))
    return {
        "std": std,
        "nonwhite_ratio": nonwhite_ratio,
        "nonblack_ratio": nonblack_ratio,
        "pass": std >= 3.0 and nonwhite_ratio >= 0.02 and nonblack_ratio >= 0.9,
    }


def validate_visual_disposition(payload: dict[str, Any], expected_image_sha256: str) -> tuple[bool, bool, list[str]]:
    issues: list[str] = []
    checks = payload.get("checks")
    if not isinstance(checks, dict) or set(checks) != REQUIRED_VISUAL_CHECKS:
        issues.append("visual_disposition_check_set_mismatch")
        return False, False, issues
    if payload.get("image_sha256") != expected_image_sha256:
        issues.append("visual_disposition_image_hash_mismatch")
    if payload.get("original_resolution_review") is not True:
        issues.append("visual_disposition_not_original_resolution")
    computed_pass = all(checks.get(name) is True for name in REQUIRED_VISUAL_CHECKS)
    expected_result = "pass" if computed_pass else "fail"
    if payload.get("result") != expected_result:
        issues.append("visual_disposition_result_mismatch")
    return not issues, computed_pass, issues


def final_result(technical_pass: bool, visual_contract_valid: bool, visual_pass: bool) -> tuple[str, str]:
    if technical_pass and visual_contract_valid and visual_pass:
        return "pass_wave10_camera_compiler_runtime_qa", "Complete"
    if technical_pass and visual_contract_valid and not visual_pass:
        return "fail_visual_runtime_composition_mismatch", "Blocked_Visual_Runtime_Composition_Mismatch"
    return "fail_wave10_camera_compiler_technical_or_contract_qa", "Blocked_Technical_QA_Failure"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--dwpose-dir", type=Path, required=True)
    parser.add_argument("--visual-disposition", type=Path, required=True)
    parser.add_argument("--unit-test-log", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    resolved = {
        name: resolve_path(getattr(args, name))
        for name in ("request", "plan", "profile", "package", "runtime", "image", "visual_disposition")
    }
    resolved["unit_test_log"] = resolve_path(args.unit_test_log)
    dwpose_dir = resolve_path(args.dwpose_dir)
    required_files = list(resolved.values()) + [dwpose_dir / name for name in EXPECTED_DWPOSE_MODEL_SHA256]
    missing = [str(path) for path in required_files if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required QA files missing: {missing}")

    request = read_json(resolved["request"])
    plan = read_json(resolved["plan"])
    profile = read_json(resolved["profile"])
    package = read_json(resolved["package"])
    runtime = read_json(resolved["runtime"])
    visual = read_json(resolved["visual_disposition"])
    recompiled_plan = compile_plan(request)
    recompiled_profile = compile_prompt_profile(request, recompiled_plan)

    generated_prompt_records = [
        record
        for record in package.get("generated_files", [])
        if str(record.get("path", "")).endswith("/prompt_request.json")
    ]
    if len(generated_prompt_records) != 1:
        raise ValueError("Package must identify exactly one prompt_request.json")
    prompt_path = resolve_path(Path(generated_prompt_records[0]["path"]))
    prompt_request = read_json(prompt_path)
    graph = prompt_request.get("prompt")
    if not isinstance(graph, dict):
        raise TypeError("Prompt request must contain a graph object")

    checkpoint = single_node(graph, "CheckpointLoaderSimple")["inputs"]
    sampler = single_node(graph, "KSampler")["inputs"]
    latent = single_node(graph, "EmptyLatentImage")["inputs"]
    save = single_node(graph, "SaveImage")["inputs"]
    prompt_texts = {node["inputs"].get("text") for node in nodes_of_type(graph, "CLIPTextEncode")}
    patch = profile["request_patch_values"]

    image_hash = sha256(resolved["image"])
    with Image.open(resolved["image"]) as loaded:
        image = loaded.convert("RGB")
        dimensions = image.size
    image_metrics = nonblank_metrics(image)

    model_records = []
    for filename, expected_hash in EXPECTED_DWPOSE_MODEL_SHA256.items():
        model_path = dwpose_dir / filename
        actual_hash = sha256(model_path)
        model_records.append(
            {
                "path": str(model_path),
                "filename": filename,
                "sha256": actual_hash,
                "expected_sha256": expected_hash,
                "sha256_matches_expected": actual_hash == expected_hash,
                "size_bytes": model_path.stat().st_size,
            }
        )

    aux_src = ROOT / "ComfyUI/custom_nodes/comfyui_controlnet_aux/src"
    sys.path.insert(0, str(aux_src))
    from custom_controlnet_aux.dwpose import DwposeDetector  # noqa: PLC0415
    from custom_controlnet_aux.dwpose.wholebody import Wholebody  # noqa: PLC0415

    detector = DwposeDetector(
        Wholebody(
            str(dwpose_dir / "yolox_l.onnx"),
            str(dwpose_dir / "dw-ll_ucoco_384.onnx"),
            torchscript_device="cpu",
        )
    )
    _, keypoints = detector(
        np.asarray(image),
        detect_resolution=768,
        include_body=True,
        include_hand=True,
        output_type="pil",
        image_and_json=True,
    )
    keypoints_path = resolved["image"].parents[1] / "qa_openpose_keypoints.json"
    write_json(keypoints_path, keypoints)
    points = body_points(keypoints)

    pulled_records = [
        record
        for record in runtime.get("pulled_artifacts", [])
        if record.get("local_path") == rel(resolved["image"])
    ]
    test_log = read_json(resolved["unit_test_log"])
    checks = {
        "request_recompiles_to_committed_plan": recompiled_plan == plan,
        "request_and_plan_recompile_to_committed_profile": recompiled_profile == profile,
        "profile_camera_plan_binding_matches": profile.get("camera_plan_binding", {}).get("sha256")
        == canonical_sha256(plan),
        "package_result_pass_local_only": package.get("result") == "pass_local_only",
        "package_profile_applied": package.get("prompt_profile", {}).get("applied") is True,
        "package_profile_path_matches": package.get("prompt_profile", {}).get("path") == rel(resolved["profile"]),
        "package_has_no_live_side_effects": all(
            package.get(field) is False
            for field in ("aws_contacted", "github_api_contacted", "civitai_contacted", "comfyui_contacted", "ec2_started", "generation_executed")
        ),
        "prompt_request_hash_matches_package": sha256(prompt_path) == package.get("prompt_request", {}).get("sha256"),
        "runtime_passed": runtime.get("result") == "pass_local_run_package_generation_smoke",
        "runtime_is_local_and_aws_free": runtime.get("local_only") is True
        and runtime.get("aws_contacted") is False
        and runtime.get("ec2_started") is False,
        "runtime_generated_exactly_one_output": runtime.get("generation_executed") is True
        and len(runtime.get("pulled_artifacts", [])) == 1,
        "runtime_stopped_server_and_closed_port": runtime.get("local_comfy", {}).get("stopped_by_helper") is True
        and runtime.get("local_comfy", {}).get("port_closed_after_stop") is True,
        "runtime_prompt_hash_matches_package": runtime.get("run_package", {}).get("prompt_request", {}).get("actual_sha256")
        == package.get("prompt_request", {}).get("sha256"),
        "image_pullback_hash_bound": len(pulled_records) == 1 and pulled_records[0].get("sha256") == image_hash,
        "output_dimensions_exact": dimensions == EXPECTED_DIMENSIONS,
        "output_nonblank": image_metrics["pass"] is True,
        "model_asset_bound": checkpoint.get("ckpt_name") == EXPECTED_MODEL == patch.get("model_asset"),
        "seed_bound": int(sampler.get("seed")) == EXPECTED_SEED == int(patch.get("seed")),
        "steps_bound": int(sampler.get("steps")) == EXPECTED_STEPS == int(patch["sampler_settings"]["steps"]),
        "cfg_bound": float(sampler.get("cfg")) == EXPECTED_CFG == float(patch["sampler_settings"]["cfg"]),
        "sampler_bound": sampler.get("sampler_name") == EXPECTED_SAMPLER == patch["sampler_settings"]["sampler_name"],
        "scheduler_bound": sampler.get("scheduler") == EXPECTED_SCHEDULER == patch["sampler_settings"]["scheduler"],
        "denoise_bound": float(sampler.get("denoise")) == EXPECTED_DENOISE == float(patch["sampler_settings"]["denoise"]),
        "latent_width_bound": int(latent.get("width")) == EXPECTED_DIMENSIONS[0] == int(patch["latent_resolution"]["width"]),
        "latent_height_bound": int(latent.get("height")) == EXPECTED_DIMENSIONS[1] == int(patch["latent_resolution"]["height"]),
        "latent_batch_bound": int(latent.get("batch_size")) == 1 == int(patch["latent_resolution"]["batch_size"]),
        "positive_prompt_bound": patch.get("positive_prompt") in prompt_texts,
        "negative_prompt_bound": patch.get("negative_prompt") in prompt_texts,
        "save_prefix_bound": save.get("filename_prefix") == EXPECTED_SAVE_PREFIX == patch.get("save_prefix"),
        "dwpose_models_hash_trusted": all(record["sha256_matches_expected"] for record in model_records),
        "exactly_one_person_detected": len(keypoints.get("people") or []) == 1,
        "all_18_body_landmarks_detected": len(points) == 18,
        "head_wrists_and_ankles_in_frame": framing_keypoints_in_frame(points),
        "unit_tests_passed": test_log.get("result") == "pass"
        and int(test_log.get("exit_code", -1)) == 0
        and int(test_log.get("failures", -1)) == 0
        and int(test_log.get("errors", -1)) == 0
        and int(test_log.get("tests_run", 0)) > 0,
    }
    technical_pass = all(checks.values())
    visual_contract_valid, visual_pass, visual_issues = validate_visual_disposition(visual, image_hash)
    result, status_decision = final_result(technical_pass, visual_contract_valid, visual_pass)
    overall_pass = result == "pass_wave10_camera_compiler_runtime_qa"

    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    evidence = {
        "schema_version": "1.0",
        "evidence_id": "W64-IMAGE-CAMERA-COMPOSITION",
        "timestamp": timestamp,
        "tracker_id": "TRK-W64-011",
        "item_id": "ITEM-W64-011",
        "lane_id": EXPECTED_LANE,
        "source_citation": "Plan/03_IMAGE_SYSTEM/WAVE10_IMAGE_CAMERA_PLAN_COMPILER.md",
        "compiler": {
            "request": rel(resolved["request"]),
            "request_sha256": sha256(resolved["request"]),
            "plan": rel(resolved["plan"]),
            "plan_sha256": sha256(resolved["plan"]),
            "canonical_plan_sha256": canonical_sha256(plan),
            "profile": rel(resolved["profile"]),
            "profile_sha256": sha256(resolved["profile"]),
        },
        "runtime": {
            "package": rel(resolved["package"]),
            "package_sha256": sha256(resolved["package"]),
            "prompt_request": rel(prompt_path),
            "prompt_request_sha256": sha256(prompt_path),
            "execution_evidence": rel(resolved["runtime"]),
            "execution_evidence_sha256": sha256(resolved["runtime"]),
            "image": rel(resolved["image"]),
            "image_sha256": image_hash,
            "dimensions": {"width": dimensions[0], "height": dimensions[1]},
            "nonblank_metrics": image_metrics,
        },
        "dwpose": {
            "models": model_records,
            "keypoints": rel(keypoints_path),
            "keypoints_sha256": sha256(keypoints_path),
            "person_count": len(keypoints.get("people") or []),
            "detected_body_landmark_count": len(points),
            "normalized_framing_points": {
                str(index): {"x": points[index][0], "y": points[index][1]}
                for index in REQUIRED_FRAMING_KEYPOINTS
                if index in points
            },
        },
        "unit_test_log": (
            {
                "path": rel(resolved["unit_test_log"]),
                "sha256": sha256(resolved["unit_test_log"]),
                "result": test_log.get("result"),
                "tests_run": test_log.get("tests_run"),
            }
            if test_log is not None
            else None
        ),
        "technical_checks": checks,
        "technical_pass": technical_pass,
        "strict_visual_disposition": {
            "path": rel(resolved["visual_disposition"]),
            "sha256": sha256(resolved["visual_disposition"]),
            "contract_valid": visual_contract_valid,
            "visual_pass": visual_pass,
            "issues": visual_issues,
            "checks": visual.get("checks"),
            "notes": visual.get("notes"),
        },
        "acceptance_gates": {
            "camera_spec_check": checks["request_recompiles_to_committed_plan"]
            and checks["model_asset_bound"]
            and checks["seed_bound"]
            and checks["positive_prompt_bound"],
            "crop_boundary_check": checks["head_wrists_and_ankles_in_frame"]
            and visual.get("checks", {}).get("head_and_hair_fully_in_frame") is True
            and visual.get("checks", {}).get("both_hands_fully_visible_and_inspectable") is True
            and visual.get("checks", {}).get("both_feet_fully_in_frame") is True
            and visual.get("checks", {}).get("no_required_region_hidden") is True,
            "composition_score": 100 if technical_pass else 0,
            "visual_runtime_ready": visual_pass,
        },
        "result": result,
        "overall_pass": overall_pass,
        "status_decision": status_decision,
        "strict_decision": {
            "row_complete": overall_pass,
            "retry_performed": False,
            "retry_allowed_by_this_evidence": False,
            "reason": (
                "The compiler, package, graph, runtime, image, and pose checks pass, but both hands are partly hidden in trouser pockets rather than fully open and inspectable as requested."
                if result == "fail_visual_runtime_composition_mismatch"
                else "See technical and visual checks."
            ),
            "target_runtime_or_lane_certification_claimed": False,
            "mask_or_geometry_authority_claimed": False,
        },
    }
    write_json(resolve_path(args.out), evidence)
    print(json.dumps(evidence, indent=2))
    return 0 if overall_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
