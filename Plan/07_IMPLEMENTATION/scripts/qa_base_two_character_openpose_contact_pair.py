#!/usr/bin/env python3
"""Record technical and optional strict visual QA for one bounded pose pair."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[3]
PROFILE_PATHS = {
    7152026253: ROOT / (
        "PromptProfiles/base_generation/realvisxl_multisample_certification/"
        "realvisxl_two_character_openpose_contact_robustness_seed7152026253.json"
    ),
    7152026254: ROOT / (
        "PromptProfiles/base_generation/realvisxl_multisample_certification/"
        "realvisxl_two_character_openpose_contact_robustness_seed7152026254.json"
    ),
}
PREPARATION_MANIFEST = ROOT / (
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    "base_two_character_openpose_contact_w70_v1/PREPARATION_MANIFEST.json"
)
EXPECTED_LANE = "sdxl_realvisxl_controlnet_openpose_lane"
EXPECTED_CONTROL_IMAGE = "controlnet_openpose_two_character_contact_w70_v1.png"
EXPECTED_CONTROLNET = "OpenPoseXL2.safetensors"
EXPECTED_SEEDS = (7152026253, 7152026254)
VISUAL_CHECKS = (
    "exactly_two_distinct_adults",
    "woman_left_contact_owner",
    "open_hand_on_upper_arm_sleeve",
    "man_hands_away_from_contact",
    "no_mutual_clasp_or_handshake",
    "whole_image_coherent",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def resolve_project_path(value: str) -> Path:
    candidate = Path(value)
    return candidate.resolve() if candidate.is_absolute() else (ROOT / candidate).resolve()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"JSON object required: {path}")
    return payload


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
        record.get("local_path") == image_relative
        and record.get("sha256") == image_hash
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


def prompt_binding_checks(
    graph: dict[str, Any], profile: dict[str, Any], seed: int
) -> dict[str, bool]:
    patch = profile["request_patch_values"]
    controlnet = single_node(graph, "ControlNetLoader")["inputs"]
    load_image = single_node(graph, "LoadImage")["inputs"]
    apply_node = single_node(graph, "ControlNetApplyAdvanced")["inputs"]
    sampler = single_node(graph, "KSampler")["inputs"]
    latent = single_node(graph, "EmptyLatentImage")["inputs"]
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
        "controlnet_asset_bound": controlnet.get("control_net_name") == EXPECTED_CONTROLNET,
        "control_image_bound": load_image.get("image") == EXPECTED_CONTROL_IMAGE,
        "control_strength_bound": float(apply_node.get("strength"))
        == float(settings["strength"]),
        "control_start_bound": float(apply_node.get("start_percent"))
        == float(settings["start_percent"]),
        "control_end_bound": float(apply_node.get("end_percent"))
        == float(settings["end_percent"]),
        "seed_bound": int(sampler.get("seed")) == seed,
        "sampler_bound": sampler.get("sampler_name") == sampler_settings["sampler_name"],
        "scheduler_bound": sampler.get("scheduler") == sampler_settings["scheduler"],
        "steps_bound": int(sampler.get("steps")) == int(sampler_settings["steps"]),
        "cfg_bound": float(sampler.get("cfg")) == float(sampler_settings["cfg"]),
        "latent_width_bound": int(latent.get("width")) == int(resolution["width"]),
        "latent_height_bound": int(latent.get("height")) == int(resolution["height"]),
        "positive_prompt_bound": patch["positive_prompt"] in text_values,
        "negative_prompt_bound": patch["negative_prompt"] in text_values,
        "save_prefix_bound": patch["save_prefix"] in save_prefixes,
    }


def run_record(
    seed: int, profile_path: Path, runtime_path: Path, image_path: Path
) -> dict[str, Any]:
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
        width, height = loaded.size

    preparation = read_json(PREPARATION_MANIFEST)
    control_path = resolve_project_path(preparation["outputs"]["control_map"]["path"])
    diagnostic_record, diagnostic_path = diagnostic_pullback(runtime)
    with Image.open(control_path) as control_loaded, Image.open(
        diagnostic_path
    ) as diagnostic_loaded:
        control_rgba = control_loaded.convert("RGBA")
        diagnostic_rgba = diagnostic_loaded.convert("RGBA")
        diagnostic_pixels_match = (
            control_rgba.size == diagnostic_rgba.size
            and ImageChops.difference(control_rgba, diagnostic_rgba).getbbox() is None
        )

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
        "package_lane_is_canonical_openpose": package.get("lane_id") == EXPECTED_LANE,
        "profile_lane_is_canonical_openpose": profile.get("target_lane_id") == EXPECTED_LANE,
        "package_profile_matches": package.get("prompt_profile", {}).get("path")
        == rel(profile_path),
        "profile_seed_expected": profile["request_patch_values"].get("seed") == seed,
        "image_is_square_1024": (width, height) == (1024, 1024),
        "image_pullback_hash_bound": image_pullback_matches(runtime, image_path),
        "diagnostic_pullback_hash_bound": sha256(diagnostic_path)
        == diagnostic_record.get("sha256"),
        "diagnostic_control_pixels_match_prepared_input": diagnostic_pixels_match,
    }
    checks.update(prompt_binding_checks(graph, profile, seed))
    return {
        "seed": seed,
        "profile": rel(profile_path),
        "runtime_evidence": rel(runtime_path),
        "run_package_manifest": rel(package_path),
        "prompt_request": rel(prompt_path),
        "prompt_request_sha256": sha256(prompt_path),
        "image": rel(image_path),
        "image_sha256": sha256(image_path),
        "diagnostic_control_image": rel(diagnostic_path),
        "diagnostic_control_image_sha256": sha256(diagnostic_path),
        "width": width,
        "height": height,
        "checks": checks,
    }


def validate_preparation() -> tuple[dict[str, Any], dict[str, bool]]:
    manifest = read_json(PREPARATION_MANIFEST)
    control_record = manifest.get("outputs", {}).get("control_map", {})
    input_record = manifest.get("outputs", {}).get("active_input_copy", {})
    control_path = resolve_project_path(control_record.get("path", ""))
    input_path = resolve_project_path(input_record.get("path", ""))
    checks = {
        "preparation_passed": manifest.get("pass") is True,
        "two_people_detected": manifest.get("detections", {}).get("people_count") == 2,
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
    if not isinstance(samples, dict) or set(samples) != {str(seed) for seed in EXPECTED_SEEDS}:
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
) -> int:
    passed = (
        technical_pass
        and visual_contract_valid
        and (not visual_supplied or visual_pass is True)
    )
    return 0 if passed else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-6253", type=Path, required=True)
    parser.add_argument("--image-6253", type=Path, required=True)
    parser.add_argument("--runtime-6254", type=Path, required=True)
    parser.add_argument("--image-6254", type=Path, required=True)
    parser.add_argument("--visual-disposition", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--tracker-out", type=Path)
    args = parser.parse_args()

    paths = {
        7152026253: (args.runtime_6253.resolve(), args.image_6253.resolve()),
        7152026254: (args.runtime_6254.resolve(), args.image_6254.resolve()),
    }
    required = [PREPARATION_MANIFEST, *PROFILE_PATHS.values()]
    for runtime_path, image_path in paths.values():
        required.extend((runtime_path, image_path))
    if args.visual_disposition:
        required.append(args.visual_disposition.resolve())
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required QA input missing: {missing}")

    profiles = {seed: read_json(path) for seed, path in PROFILE_PATHS.items()}
    profile_invariance = (
        normalize_profile_for_invariance(profiles[7152026253])
        == normalize_profile_for_invariance(profiles[7152026254])
    )
    preparation, preparation_checks = validate_preparation()
    records = [
        run_record(seed, PROFILE_PATHS[seed], *paths[seed]) for seed in EXPECTED_SEEDS
    ]
    technical_pass = (
        profile_invariance
        and all(preparation_checks.values())
        and all(all(record["checks"].values()) for record in records)
    )

    visual_path = args.visual_disposition.resolve() if args.visual_disposition else None
    visual, visual_pass, visual_contract_valid = validate_visual_disposition(visual_path)
    if not technical_pass:
        result = "fail_local_base_remediation_openpose_pair_technical_qa"
    elif visual is None:
        result = "pass_technical_pending_strict_visual_disposition"
    elif not visual_contract_valid:
        result = "fail_invalid_strict_visual_disposition_contract"
    elif visual_pass:
        result = "pass_local_base_remediation_openpose_pair_strict_visual_qa"
    else:
        result = "fail_local_base_remediation_openpose_pair_interaction_contract"

    evidence = {
        "schema_version": "1.0",
        "evidence_id": "W70-LOCAL-BASE-REMEDIATION-OPENPOSE-CONTACT-PAIR-QA",
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "lane_id": EXPECTED_LANE,
        "remediates_lane_id": "sdxl_realvisxl_base_lane",
        "result": result,
        "technical_pass": technical_pass,
        "profile_invariance_pass": profile_invariance,
        "preparation_manifest": rel(PREPARATION_MANIFEST),
        "preparation_manifest_sha256": sha256(PREPARATION_MANIFEST),
        "preparation_checks": preparation_checks,
        "profile_invariance_scope": (
            "Profiles are identical except profile_id, seed, save_prefix, and output_prefix."
        ),
        "control_binding_contract": {
            "controlnet_asset": EXPECTED_CONTROLNET,
            "control_image": EXPECTED_CONTROL_IMAGE,
            "preparation_result": preparation.get("result"),
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
            "bounded_sample_count": 2,
            "stop_after_this_pair": True,
            "materially_different_composition_control_available": visual_pass is True,
            "base_canonical_robustness_failure_cleared": False,
            "base_final_certification_allowed": False,
            "openpose_final_certification_allowed": False,
            "target_runtime_proof_added": False,
        },
        "boundaries": {
            "local_only": True,
            "aws_contacted": False,
            "ec2_started": False,
            "gold_masks_consumed": False,
            "mask_promotion_performed": False,
            "wave70_hard_gate_rerun": False,
            "wave71_activated": False,
        },
    }
    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
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
    )


if __name__ == "__main__":
    raise SystemExit(main())
