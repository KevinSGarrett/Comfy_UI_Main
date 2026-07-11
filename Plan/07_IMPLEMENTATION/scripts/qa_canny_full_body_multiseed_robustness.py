#!/usr/bin/env python3
"""Evaluate three-seed Canny full-body local robustness."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal test envs
    np = None
try:
    from PIL import Image, ImageChops
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal test envs
    Image = None
    ImageChops = None


ROOT = Path(__file__).resolve().parents[3]
EXPECTED_SEEDS = (711570301, 711570302, 711570303)
EXPECTED_LANE = "sdxl_realvisxl_controlnet_canny_lane"
EXPECTED_CONTROL_IMAGE = "controlnet_canny_full_body_standing_w70_v1.png"
EXPECTED_CONTROLNET = "controlnet-canny-sdxl-1.0-small.safetensors"
EXPECTED_MODEL = "realvisxlV50_v50Bakedvae.safetensors"
EXPECTED_DIMENSIONS = (768, 1024)
EXPECTED_CONTROL_STRENGTH = 0.42
EXPECTED_CONTROL_START = 0.0
EXPECTED_CONTROL_END = 0.6
EXPECTED_STEPS = 24
EXPECTED_CFG = 5.5
EXPECTED_SAMPLER = "dpmpp_2m_sde"
EXPECTED_SCHEDULER = "karras"
EXPECTED_DENOISE = 1.0
EXPECTED_SOURCE_SHA256 = "e20a857f0ac23151ae1b8aa47fb4746c975e522a5598896f747ef08a50cc9336"
PREPARATION_MANIFEST = ROOT / (
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    "canny_full_body_standing_w70_v1/PREPARATION_MANIFEST.json"
)
PROFILE_PATHS = {
    711570301: ROOT
    / "PromptProfiles/base_generation/controlnet_canny_w71_local_quality_loop/canny_full_body_standing_seed711570301.json",
    711570302: ROOT
    / "PromptProfiles/base_generation/controlnet_canny_w71_local_quality_loop/canny_full_body_standing_seed711570302.json",
    711570303: ROOT
    / "PromptProfiles/base_generation/controlnet_canny_w71_local_quality_loop/canny_full_body_standing_seed711570303.json",
}
EXPECTED_DWPOSE_MODEL_SHA256 = {
    "yolox_l.onnx": "7860ae79de6c89a3c1eb72ae9a2756c0ccfbe04b7791bb5880afabd97855a411",
    "dw-ll_ucoco_384.onnx": "724f4ff2439ed61afb86fb8a1951ec39c6220682803b4a8bd4f598cd913b1843",
}
VISUAL_CHECKS = (
    "exactly_one_adult",
    "full_body_in_frame",
    "both_hands_visible",
    "both_feet_visible",
    "coherent_limbs",
    "no_canny_edge_leakage_harsh_outlines_or_border_seam",
    "natural_skin_clothing_backdrop_coherence",
)


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


def resolve_project_path(value: str) -> Path:
    candidate = Path(value)
    return candidate.resolve() if candidate.is_absolute() else (ROOT / candidate).resolve()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"JSON object required: {path}")
    return payload


def dwpose_model_records(model_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for filename, expected_sha256 in EXPECTED_DWPOSE_MODEL_SHA256.items():
        path = model_dir / filename
        actual_sha256 = sha256(path) if path.is_file() else None
        records.append(
            {
                "path": rel(path),
                "filename": filename,
                "exists": path.is_file(),
                "sha256": actual_sha256,
                "expected_sha256": expected_sha256,
                "sha256_matches_expected": actual_sha256 == expected_sha256,
                "size_bytes": path.stat().st_size if path.is_file() else None,
            }
        )
    return records


def dwpose_models_trusted(records: list[dict[str, Any]]) -> bool:
    return all(
        record.get("exists") is True
        and record.get("sha256_matches_expected") is True
        for record in records
    )


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def normalize_profile_for_invariance(profile: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(profile)
    normalized.pop("profile_id", None)
    patch = normalized.get("request_patch_values", {})
    if isinstance(patch, dict):
        patch.pop("seed", None)
        patch.pop("save_prefix", None)
    expected = normalized.get("expected_outputs", {})
    if isinstance(expected, dict):
        expected.pop("output_prefix", None)
    return normalized


def nodes_of_type(graph: dict[str, Any], class_type: str) -> list[dict[str, Any]]:
    return [
        node
        for node in graph.values()
        if isinstance(node, dict) and node.get("class_type") == class_type
    ]


def single_node(graph: dict[str, Any], class_type: str) -> dict[str, Any]:
    nodes = nodes_of_type(graph, class_type)
    if len(nodes) != 1:
        raise ValueError(f"Expected one {class_type} node, found {len(nodes)}")
    return nodes[0]


def generated_prompt_path(package_manifest: dict[str, Any]) -> Path:
    records = [
        entry
        for entry in package_manifest.get("generated_files", [])
        if entry.get("purpose", "").startswith("Patched ComfyUI /prompt request")
    ]
    if len(records) != 1:
        raise ValueError("Run package must contain exactly one prompt request record")
    return resolve_project_path(records[0]["path"])


def image_pullback_matches(runtime: dict[str, Any], image_path: Path) -> bool:
    image_relative = rel(image_path)
    image_hash = sha256(image_path)
    return any(
        record.get("local_path") == image_relative and record.get("sha256") == image_hash
        for record in runtime.get("pulled_artifacts", [])
    )


def diagnostic_pullback(runtime: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    records = [
        record
        for record in runtime.get("pulled_artifacts", [])
        if str(record.get("node_id")) == "13"
    ]
    if len(records) != 1:
        raise ValueError(f"Expected one node-13 diagnostic pullback, found {len(records)}")
    path = resolve_project_path(records[0]["local_path"])
    if not path.is_file():
        raise FileNotFoundError(f"Diagnostic pullback missing: {path}")
    return records[0], path


def body_points(payload: dict[str, Any]) -> dict[int, tuple[float, float]]:
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


def framing_points_present(points: dict[int, tuple[float, float]]) -> bool:
    required = (0, 4, 7, 10, 13)
    return all(point in points for point in required)


def points_are_in_frame(points: dict[int, tuple[float, float]]) -> bool:
    required = (0, 4, 7, 10, 13)
    return all(
        0.01 <= points[index][0] <= 0.99 and 0.01 <= points[index][1] <= 0.99
        for index in required
    )


def output_nonblank_checks(image: Image.Image) -> dict[str, Any]:
    if np is None:
        raise ModuleNotFoundError("numpy is required for image nonblank checks")
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


def prompt_binding_checks(
    graph: dict[str, Any], profile: dict[str, Any], seed: int
) -> dict[str, bool]:
    patch = profile["request_patch_values"]
    controlnet = single_node(graph, "ControlNetLoader")["inputs"]
    load_image = single_node(graph, "LoadImage")["inputs"]
    apply_node = single_node(graph, "ControlNetApplyAdvanced")["inputs"]
    sampler = single_node(graph, "KSampler")["inputs"]
    latent = single_node(graph, "EmptyLatentImage")["inputs"]
    checkpoint = single_node(graph, "CheckpointLoaderSimple")["inputs"]
    text_values = {
        node["inputs"].get("text") for node in nodes_of_type(graph, "CLIPTextEncode")
    }
    save_prefixes = {
        node["inputs"].get("filename_prefix")
        for node in nodes_of_type(graph, "SaveImage")
    }
    settings = patch["controlnet_settings"]
    resolution = patch["latent_resolution"]
    sampler_settings = patch["sampler_settings"]
    return {
        "model_asset_bound": checkpoint.get("ckpt_name") == EXPECTED_MODEL,
        "profile_model_asset_expected": patch.get("model_asset") == EXPECTED_MODEL,
        "controlnet_asset_bound": controlnet.get("control_net_name") == EXPECTED_CONTROLNET,
        "profile_controlnet_asset_expected": patch.get("controlnet_asset")
        == EXPECTED_CONTROLNET,
        "control_image_bound": load_image.get("image") == EXPECTED_CONTROL_IMAGE,
        "profile_control_image_expected": patch.get("control_image")
        == EXPECTED_CONTROL_IMAGE,
        "control_strength_bound": float(apply_node.get("strength"))
        == float(EXPECTED_CONTROL_STRENGTH),
        "control_start_bound": float(apply_node.get("start_percent"))
        == float(EXPECTED_CONTROL_START),
        "control_end_bound": float(apply_node.get("end_percent"))
        == float(EXPECTED_CONTROL_END),
        "profile_control_strength_expected": float(settings["strength"])
        == float(EXPECTED_CONTROL_STRENGTH),
        "profile_control_start_expected": float(settings["start_percent"])
        == float(EXPECTED_CONTROL_START),
        "profile_control_end_expected": float(settings["end_percent"])
        == float(EXPECTED_CONTROL_END),
        "seed_bound": int(sampler.get("seed")) == seed,
        "sampler_bound": sampler.get("sampler_name") == EXPECTED_SAMPLER,
        "scheduler_bound": sampler.get("scheduler") == EXPECTED_SCHEDULER,
        "steps_bound": int(sampler.get("steps")) == EXPECTED_STEPS,
        "cfg_bound": float(sampler.get("cfg")) == EXPECTED_CFG,
        "denoise_bound": float(sampler.get("denoise")) == EXPECTED_DENOISE,
        "profile_sampler_expected": sampler_settings.get("sampler_name")
        == EXPECTED_SAMPLER,
        "profile_scheduler_expected": sampler_settings.get("scheduler")
        == EXPECTED_SCHEDULER,
        "profile_steps_expected": int(sampler_settings.get("steps")) == EXPECTED_STEPS,
        "profile_cfg_expected": float(sampler_settings.get("cfg")) == EXPECTED_CFG,
        "profile_denoise_expected": float(sampler_settings.get("denoise"))
        == EXPECTED_DENOISE,
        "latent_width_bound": int(latent.get("width")) == EXPECTED_DIMENSIONS[0],
        "latent_height_bound": int(latent.get("height")) == EXPECTED_DIMENSIONS[1],
        "profile_latent_width_expected": int(resolution["width"]) == EXPECTED_DIMENSIONS[0],
        "profile_latent_height_expected": int(resolution["height"]) == EXPECTED_DIMENSIONS[1],
        "positive_prompt_bound": patch["positive_prompt"] in text_values,
        "negative_prompt_bound": patch["negative_prompt"] in text_values,
        "save_prefix_bound": patch["save_prefix"] in save_prefixes,
    }


def validate_preparation() -> tuple[dict[str, Any], dict[str, bool]]:
    manifest = read_json(PREPARATION_MANIFEST)
    source_record = manifest.get("source", {})
    preprocess = manifest.get("preprocess", {})
    control_record = manifest.get("outputs", {}).get("control_map", {})
    input_record = manifest.get("outputs", {}).get("active_input_copy", {})
    manifest_checks = manifest.get("checks")
    control_path = resolve_project_path(control_record.get("path", ""))
    input_path = resolve_project_path(input_record.get("path", ""))
    checks = {
        "preparation_passed": manifest.get("pass") is True,
        "source_hash_matches_expected": source_record.get("sha256")
        == EXPECTED_SOURCE_SHA256,
        "preprocess_operator_is_opencv_canny": preprocess.get("operator")
        == "opencv_canny",
        "preprocess_gaussian_kernel_exact": preprocess.get("gaussian_kernel")
        == [5, 5],
        "preprocess_gaussian_sigma_exact": preprocess.get("gaussian_sigma") == 1.4,
        "preprocess_canny_low_threshold_exact": preprocess.get("canny_low_threshold")
        == 100,
        "preprocess_canny_high_threshold_exact": preprocess.get(
            "canny_high_threshold"
        )
        == 200,
        "prepared_control_dimensions_exact": (
            control_record.get("width"), control_record.get("height")
        )
        == EXPECTED_DIMENSIONS,
        "all_preparation_manifest_checks_pass": isinstance(manifest_checks, dict)
        and bool(manifest_checks)
        and all(value is True for value in manifest_checks.values()),
        "control_map_exists": control_path.is_file(),
        "active_input_exists": input_path.is_file(),
        "control_map_hash_matches_manifest": control_path.is_file()
        and sha256(control_path) == control_record.get("sha256"),
        "active_input_hash_matches_manifest": input_path.is_file()
        and sha256(input_path) == input_record.get("sha256"),
        "active_input_matches_control_map": control_path.is_file()
        and input_path.is_file()
        and sha256(control_path) == sha256(input_path),
    }
    return manifest, checks


def validate_visual_disposition(
    path: Path | None,
) -> tuple[dict[str, Any] | None, bool | None, bool]:
    if path is None:
        return None, None, True
    payload = read_json(path)
    samples = payload.get("samples")
    expected_keys = {str(seed) for seed in EXPECTED_SEEDS}
    if not isinstance(samples, dict) or set(samples) != expected_keys:
        return payload, False, False
    contract_valid = True
    sample_passes: list[bool] = []
    for seed in EXPECTED_SEEDS:
        sample = samples[str(seed)]
        checks = sample.get("checks") if isinstance(sample, dict) else None
        if not isinstance(checks, dict) or set(checks) != set(VISUAL_CHECKS):
            contract_valid = False
            sample_passes.append(False)
            continue
        passed = all(checks.get(name) is True for name in VISUAL_CHECKS)
        if sample.get("result") != ("pass" if passed else "fail"):
            contract_valid = False
        sample_passes.append(passed)
    visual_pass = all(sample_passes)
    if payload.get("all_samples_pass") is not visual_pass:
        contract_valid = False
    return payload, visual_pass, contract_valid


def qa_exit_code(
    technical_pass: bool,
    visual_supplied: bool,
    visual_pass: bool | None,
    visual_contract_valid: bool,
    technical_only_allowed: bool = False,
) -> int:
    passed = technical_pass and visual_contract_valid
    if not visual_supplied:
        passed = passed and technical_only_allowed
    else:
        passed = passed and visual_pass is True
    return 0 if passed else 2


def run_record(
    seed: int,
    profile_path: Path,
    runtime_path: Path,
    image_path: Path,
    detector,
    source_points: dict[int, tuple[float, float]],
    prepared_control_path: Path,
) -> dict[str, Any]:
    if np is None:
        raise ModuleNotFoundError("numpy is required for Canny robustness QA")
    if Image is None or ImageChops is None:
        raise ModuleNotFoundError("Pillow is required for Canny robustness QA")
    profile = read_json(profile_path)
    runtime = read_json(runtime_path)
    package_path = resolve_project_path(runtime["run_package"]["file"])
    package = read_json(package_path)
    prompt_path = generated_prompt_path(package)
    request = read_json(prompt_path)
    graph = request.get("prompt")
    if not isinstance(graph, dict):
        raise TypeError("Prompt request must contain a prompt graph object")

    with Image.open(image_path) as loaded:
        output_image = loaded.convert("RGB")
        width, height = output_image.size
    output_quality = output_nonblank_checks(output_image)
    _, output_keypoints = detector(
        np.asarray(output_image),
        detect_resolution=768,
        include_body=True,
        include_hand=True,
        output_type="pil",
        image_and_json=True,
    )
    output_points = body_points(output_keypoints)
    common = sorted(set(source_points) & set(output_points))
    distances = [math.dist(source_points[index], output_points[index]) for index in common]
    mean_distance = sum(distances) / len(distances) if distances else None
    max_distance = max(distances) if distances else None
    framing_ok = framing_points_present(output_points) and points_are_in_frame(output_points)

    diagnostic_record, diagnostic_path = diagnostic_pullback(runtime)
    with Image.open(prepared_control_path) as control_loaded, Image.open(
        diagnostic_path
    ) as diagnostic_loaded:
        control_rgba = control_loaded.convert("RGBA")
        diagnostic_rgba = diagnostic_loaded.convert("RGBA")
        diagnostic_pixels_match = (
            control_rgba.size == diagnostic_rgba.size
            and ImageChops.difference(control_rgba, diagnostic_rgba).getbbox() is None
        )

    output_keypoints_path = image_path.parents[1] / "qa_openpose_keypoints.json"
    write_json(output_keypoints_path, output_keypoints)

    package_request_hash = package.get("prompt_request", {}).get("sha256")
    runtime_request = runtime.get("run_package", {}).get("prompt_request", {})
    checks = {
        "runtime_passed": runtime.get("result") == "pass_local_run_package_generation_smoke",
        "generation_executed": runtime.get("generation_executed") is True,
        "request_hash_matched_by_runtime": runtime_request.get("hash_match") is True,
        "request_hash_matches_package": sha256(prompt_path) == package_request_hash,
        "request_hash_matches_runtime": sha256(prompt_path)
        == runtime_request.get("actual_sha256"),
        "server_stopped_and_port_closed": (
            runtime.get("local_comfy", {}).get("stopped_by_helper") is True
            and runtime.get("local_comfy", {}).get("port_closed_after_stop") is True
        ),
        "package_lane_is_canonical_canny": package.get("lane_id") == EXPECTED_LANE,
        "profile_lane_is_canonical_canny": profile.get("target_lane_id") == EXPECTED_LANE,
        "package_profile_matches": package.get("prompt_profile", {}).get("path")
        == rel(profile_path),
        "profile_seed_expected": profile["request_patch_values"].get("seed") == seed,
        "output_is_768x1024": (width, height) == EXPECTED_DIMENSIONS,
        "output_nonblank": output_quality["pass"] is True,
        "image_pullback_hash_bound": image_pullback_matches(runtime, image_path),
        "diagnostic_pullback_hash_bound": sha256(diagnostic_path)
        == diagnostic_record.get("sha256"),
        "diagnostic_control_pixels_match_prepared_input": diagnostic_pixels_match,
        "exactly_one_person_detected": len(output_keypoints.get("people") or []) == 1,
        "all_18_body_landmarks_common": len(common) == 18,
        "mean_normalized_landmark_error_lte_0_10": mean_distance is not None
        and mean_distance <= 0.10,
        "max_normalized_landmark_error_lte_0_20": max_distance is not None
        and max_distance <= 0.20,
        "full_body_framing_preserved": framing_ok,
    }
    checks.update(prompt_binding_checks(graph, profile, seed))
    return {
        "seed": seed,
        "profile": rel(profile_path),
        "runtime_evidence": rel(runtime_path),
        "run_package_manifest": rel(package_path),
        "run_package_manifest_sha256": sha256(package_path),
        "prompt_request": rel(prompt_path),
        "prompt_request_sha256": sha256(prompt_path),
        "image": rel(image_path),
        "image_sha256": sha256(image_path),
        "diagnostic_control_image": rel(diagnostic_path),
        "diagnostic_control_image_sha256": sha256(diagnostic_path),
        "output_dimensions": {"width": width, "height": height},
        "output_nonblank_metrics": {
            "std": output_quality["std"],
            "nonwhite_ratio": output_quality["nonwhite_ratio"],
            "nonblack_ratio": output_quality["nonblack_ratio"],
        },
        "keypoints": {
            "path": rel(output_keypoints_path),
            "sha256": sha256(output_keypoints_path),
        },
        "geometry_metrics": {
            "common_body_landmarks": len(common),
            "mean_normalized_landmark_error": mean_distance,
            "max_normalized_landmark_error": max_distance,
            "framing_points_present": framing_points_present(output_points),
        },
        "checks": checks,
    }


def main() -> int:
    if np is None:
        raise ModuleNotFoundError("numpy is required for Canny robustness QA")
    if Image is None or ImageChops is None:
        raise ModuleNotFoundError("Pillow is required for Canny robustness QA")
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-711570301", type=Path, required=True)
    parser.add_argument("--image-711570301", type=Path, required=True)
    parser.add_argument("--runtime-711570302", type=Path, required=True)
    parser.add_argument("--image-711570302", type=Path, required=True)
    parser.add_argument("--runtime-711570303", type=Path, required=True)
    parser.add_argument("--image-711570303", type=Path, required=True)
    parser.add_argument("--dwpose-dir", type=Path, required=True)
    parser.add_argument("--visual-disposition", type=Path)
    parser.add_argument("--technical-only", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--tracker-out", type=Path)
    args = parser.parse_args()
    if args.technical_only and args.visual_disposition:
        parser.error("--technical-only cannot be combined with --visual-disposition")

    runtime_image_paths = {
        711570301: (
            args.runtime_711570301.resolve(),
            args.image_711570301.resolve(),
        ),
        711570302: (
            args.runtime_711570302.resolve(),
            args.image_711570302.resolve(),
        ),
        711570303: (
            args.runtime_711570303.resolve(),
            args.image_711570303.resolve(),
        ),
    }
    if len(runtime_image_paths) != 3:
        raise ValueError("Exactly three seeds are allowed for this QA scope")

    required = [PREPARATION_MANIFEST, *PROFILE_PATHS.values()]
    dwpose_dir = args.dwpose_dir.resolve()
    detector_model = dwpose_dir / "yolox_l.onnx"
    pose_model = dwpose_dir / "dw-ll_ucoco_384.onnx"
    required.extend((detector_model.resolve(), pose_model.resolve()))
    for runtime_path, image_path in runtime_image_paths.values():
        required.extend((runtime_path, image_path))
    if args.visual_disposition:
        required.append(args.visual_disposition.resolve())
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required Canny robustness QA input missing: {missing}")

    model_records = dwpose_model_records(dwpose_dir)
    if not dwpose_models_trusted(model_records):
        raise ValueError(f"DWPose model authority checks failed: {model_records}")

    profiles = {seed: read_json(path) for seed, path in PROFILE_PATHS.items()}
    profile_invariance = (
        normalize_profile_for_invariance(profiles[711570301])
        == normalize_profile_for_invariance(profiles[711570302])
        == normalize_profile_for_invariance(profiles[711570303])
    )

    preparation_manifest, preparation_checks = validate_preparation()
    prepared_control_path = resolve_project_path(
        preparation_manifest["outputs"]["control_map"]["path"]
    )

    aux_src = ROOT / "ComfyUI/custom_nodes/comfyui_controlnet_aux/src"
    sys.path.insert(0, str(aux_src))
    from custom_controlnet_aux.dwpose import DwposeDetector  # noqa: PLC0415
    from custom_controlnet_aux.dwpose.wholebody import Wholebody  # noqa: PLC0415

    detector = DwposeDetector(
        Wholebody(str(detector_model), str(pose_model), torchscript_device="cpu")
    )

    source_path = resolve_project_path(preparation_manifest["source"]["path"])
    with Image.open(source_path) as loaded:
        source_image = loaded.convert("RGB")
    _, source_keypoints = detector(
        np.asarray(source_image),
        detect_resolution=768,
        include_body=True,
        include_hand=True,
        output_type="pil",
        image_and_json=True,
    )
    source_points = body_points(source_keypoints)

    records = [
        run_record(
            seed=seed,
            profile_path=PROFILE_PATHS[seed],
            runtime_path=runtime_image_paths[seed][0],
            image_path=runtime_image_paths[seed][1],
            detector=detector,
            source_points=source_points,
            prepared_control_path=prepared_control_path,
        )
        for seed in EXPECTED_SEEDS
    ]
    technical_pass = (
        profile_invariance
        and all(preparation_checks.values())
        and all(all(record["checks"].values()) for record in records)
    )

    visual_path = args.visual_disposition.resolve() if args.visual_disposition else None
    visual, visual_pass, visual_contract_valid = validate_visual_disposition(visual_path)
    if not technical_pass:
        result = "fail_local_canny_full_body_multiseed_technical_qa"
    elif visual is None and args.technical_only:
        result = "pass_technical_only_explicitly_allowed_pending_strict_visual_disposition"
    elif visual is None:
        result = "fail_missing_required_strict_visual_disposition"
    elif not visual_contract_valid:
        result = "fail_invalid_strict_visual_disposition_contract"
    elif visual_pass:
        result = "pass_local_canny_full_body_multiseed_strict_visual_qa"
    else:
        result = "fail_local_canny_full_body_multiseed_visual_contract"

    evidence = {
        "schema_version": "1.0",
        "evidence_id": "W70-LOCAL-CANNY-FULL-BODY-MULTISEED-ROBUSTNESS-QA",
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "lane_id": EXPECTED_LANE,
        "result": result,
        "technical_pass": technical_pass,
        "profile_invariance_pass": profile_invariance,
        "profile_invariance_scope": (
            "Profiles are identical except profile_id, seed, save_prefix, and output_prefix."
        ),
        "dwpose_model_authority": {
            "supplied_directory": rel(dwpose_dir),
            "required_files": model_records,
            "all_hashes_trusted": dwpose_models_trusted(model_records),
        },
        "preparation_manifest": rel(PREPARATION_MANIFEST),
        "preparation_manifest_sha256": sha256(PREPARATION_MANIFEST),
        "preparation_checks": preparation_checks,
        "control_binding_contract": {
            "model_asset": EXPECTED_MODEL,
            "controlnet_asset": EXPECTED_CONTROLNET,
            "control_image": EXPECTED_CONTROL_IMAGE,
            "control_strength": EXPECTED_CONTROL_STRENGTH,
            "control_start_percent": EXPECTED_CONTROL_START,
            "control_end_percent": EXPECTED_CONTROL_END,
            "preparation_result": preparation_manifest.get("result"),
            "prepared_control_sha256": preparation_manifest["outputs"]["control_map"][
                "sha256"
            ],
        },
        "records": records,
        "strict_visual_disposition": (
            None
            if visual is None
            else {
                "path": rel(visual_path),
                "sha256": sha256(visual_path),
                "contract_valid": visual_contract_valid,
                "all_samples_pass": visual_pass,
                "payload": visual,
            }
        ),
        "strict_decision": {
            "bounded_sample_count": 3,
            "stop_after_this_three_seed_matrix": True,
            "technical_only_mode": args.technical_only,
            "strict_visual_required_for_scope_clearance": True,
            "full_body_contract_cleared": visual_pass is True,
        },
        "boundaries": {
            "local_only": True,
            "gold_masks_consumed": False,
            "mask_promotion_performed": False,
            "target_runtime_proof": False,
            "final_lane_certification": False,
            "wave70_hard_gate_rerun": False,
            "wave71_activated": False,
        },
    }

    out = args.out.resolve()
    write_json(out, evidence)
    if args.tracker_out:
        tracker_out = args.tracker_out.resolve()
        tracker_out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out, tracker_out)
    print(json.dumps(evidence, indent=2))
    return qa_exit_code(
        technical_pass=technical_pass,
        visual_supplied=visual is not None,
        visual_pass=visual_pass,
        visual_contract_valid=visual_contract_valid,
        technical_only_allowed=args.technical_only,
    )


if __name__ == "__main__":
    raise SystemExit(main())
