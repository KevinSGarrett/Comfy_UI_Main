#!/usr/bin/env python3
"""Bind a localized FLUX.2 repair packet to the proven SDXL inpaint lane."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image

from materialize_base_generation_smoke_prompts import patch_prompt, verify_applied


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_under(root: Path, value: Path) -> Path:
    path = value if value.is_absolute() else root / value
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"path escapes project root: {value}")
    return resolved


def project_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def require_hash(path: Path, expected: str, label: str) -> str:
    actual = sha256_file(path)
    if actual != expected.lower():
        raise ValueError(f"{label} hash mismatch")
    return actual


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--repair-packet", type=Path, required=True)
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--patch-points", type=Path, required=True)
    parser.add_argument("--runtime-requirements", type=Path, required=True)
    parser.add_argument("--structural-profile", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--positive-prompt", required=True)
    parser.add_argument("--negative-prompt", required=True)
    parser.add_argument("--save-prefix", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    packet_path = resolve_under(root, args.repair_packet)
    workflow_path = resolve_under(root, args.workflow)
    patch_path = resolve_under(root, args.patch_points)
    requirements_path = resolve_under(root, args.runtime_requirements)
    profile_path = resolve_under(root, args.structural_profile)
    output_dir = resolve_under(root, args.output_dir)

    packet = read_json(packet_path)
    if packet.get("classification") != "LOCALIZED_ANATOMY_REPAIR_PACKET_READY_GENERATION_NOT_EXECUTED":
        raise ValueError("repair packet is not ready for generation binding")
    if packet.get("runtime", {}).get("generation_executed") is not False:
        raise ValueError("repair packet already claims generation execution")
    if packet.get("boundaries", {}).get("production_promotion_allowed") is not False:
        raise ValueError("repair packet does not preserve the promotion boundary")

    source_path = resolve_under(root, Path(packet["source"]["path"]))
    mask_path = resolve_under(root, Path(packet["operational_mask"]["path"]))
    source_hash = require_hash(source_path, packet["source"]["sha256"], "source image")
    mask_hash = require_hash(mask_path, packet["operational_mask"]["sha256"], "operational mask")
    if packet["operational_mask"].get("classification") != "non_gold_operational_repair_region":
        raise ValueError("operational mask classification is not allowed for this binding")
    if packet["operational_mask"].get("consumed_as_evaluation_truth") is not False:
        raise ValueError("operational mask cannot be consumed as evaluation truth")
    with Image.open(mask_path) as mask_image:
        mask_mode = mask_image.mode
        if mask_mode != "L":
            raise ValueError("operational repair mask must be single-channel grayscale")
        if mask_image.getbbox() is None:
            raise ValueError("operational repair mask is empty")
        mask_dimensions = list(mask_image.size)
    expected_mask_dimensions = [packet["source"]["width"], packet["source"]["height"]]
    if mask_dimensions != expected_mask_dimensions:
        raise ValueError("operational repair mask dimensions do not match source")
    mask_channel_verification = {
        "source_mode": mask_mode,
        "selected_channel": "red",
        "grayscale_to_red_equivalent_after_rgb_conversion": True,
        "mask_nonempty": True,
        "dimensions_match_source": True,
    }

    workflow = read_json(workflow_path)
    patch_points = read_json(patch_path)
    requirements = read_json(requirements_path)
    profile = read_json(profile_path)
    lane_id = "sdxl_realvisxl_inpaint_detail_lane"
    for label, payload in (
        ("patch points", patch_points),
        ("runtime requirements", requirements),
    ):
        if payload.get("lane_id") != lane_id:
            raise ValueError(f"{label} lane mismatch")

    required_models = requirements.get("required_models", [])
    matching_models = [
        model
        for model in required_models
        if model.get("role") == "checkpoint"
        and model.get("filename") == "realvisxlV50_v50Bakedvae.safetensors"
        and model.get("sha256") == "6a35a7855770ae9820a3c931d4964c3817b6d9e3c6f9c4dabb5b3a94e5643b80"
    ]
    if len(matching_models) != 1:
        raise ValueError("exact RealVisXL checkpoint requirement is missing")
    if profile.get("status") != "planned_one_attempt_unproven":
        raise ValueError("structural repair profile is not an unproven one-attempt pilot")
    profile_lane = profile.get("lane", {})
    if profile_lane.get("lane_id") != lane_id:
        raise ValueError("structural repair profile lane mismatch")
    if profile_lane.get("checkpoint_sha256") != matching_models[0]["sha256"]:
        raise ValueError("structural repair profile checkpoint hash mismatch")
    if profile.get("runtime", {}).get("execution_allowed") is not False:
        raise ValueError("structural repair profile must remain execution-blocked")
    if profile.get("boundaries", {}).get("production_promotion_allowed") is not False:
        raise ValueError("structural repair profile does not preserve the promotion boundary")
    hypothesis = profile.get("repair_hypothesis", {})
    sampler_profile = hypothesis.get("sampler_settings", {})
    denoise_bounds = sampler_profile.get("denoise_bounds", {})
    selected_denoise = sampler_profile.get("selected_denoise")
    if not isinstance(selected_denoise, (int, float)) or isinstance(selected_denoise, bool):
        raise ValueError("structural repair profile selected denoise is invalid")
    if not float(denoise_bounds.get("minimum", 1.0)) <= float(selected_denoise) <= float(denoise_bounds.get("maximum", 0.0)):
        raise ValueError("structural repair profile selected denoise is outside declared bounds")
    measured_delta = profile.get("measured_delta_contract", {}).get("repair", {})
    required_delta_fields = {
        "minimum_inside_mask_mae",
        "maximum_outside_mask_mae",
        "minimum_outside_mask_ssim",
        "minimum_whole_image_ssim",
    }
    if not required_delta_fields.issubset(measured_delta):
        raise ValueError("structural repair measured-delta contract is incomplete")

    source_input_name = f"flux2_seed{packet['prompt_request']['seed']}_source.png"
    mask_input_name = f"flux2_seed{packet['prompt_request']['seed']}_operational_repair_mask.png"
    patch_values = {
        "positive_prompt": args.positive_prompt,
        "negative_prompt": args.negative_prompt,
        "source_image": source_input_name,
        "mask_image": mask_input_name,
        "mask_channel": "red",
        "seed": args.seed,
        "sampler_settings": {
            "steps": sampler_profile["steps"],
            "cfg": sampler_profile["cfg"],
            "sampler_name": sampler_profile["sampler_name"],
            "scheduler": sampler_profile["scheduler"],
            "denoise": selected_denoise,
        },
        "model_asset": "realvisxlV50_v50Bakedvae.safetensors",
        "save_prefix": args.save_prefix,
    }
    patched, patch_errors, applied = patch_prompt(workflow, patch_points, patch_values)
    patch_errors.extend(verify_applied(patched, applied))
    if patch_errors:
        raise ValueError(f"workflow patch contract failed: {patch_errors}")

    topology_checks = {
        "source_is_composite_destination": patched.get("14", {}).get("inputs", {}).get("destination") == ["5", 0],
        "decoded_candidate_is_composite_source": patched.get("14", {}).get("inputs", {}).get("source") == ["10", 0],
        "feathered_mask_drives_composite": patched.get("14", {}).get("inputs", {}).get("mask") == ["13", 0],
        "feathered_mask_drives_latent_noise": patched.get("12", {}).get("inputs", {}).get("mask") == ["13", 0],
        "feather_pixels_remain_certified_value": all(
            patched.get("13", {}).get("inputs", {}).get(side) == 24
            for side in ("left", "top", "right", "bottom")
        ),
        "diagnostic_mask_preview_present": patched.get("16", {}).get("class_type") == "SaveImage",
    }
    if not all(topology_checks.values()):
        raise ValueError(f"inpaint topology validation failed: {topology_checks}")

    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = output_dir / "prompt_request.json"
    prompt_payload = {
        "client_id": f"flux2-seed{packet['prompt_request']['seed']}-localized-repair-dry-run",
        "prompt": patched,
        "extra_data": {
            "lane_id": lane_id,
            "source_repair_packet": project_path(root, packet_path),
            "execution_allowed": False,
            "one_candidate_only": True,
        },
    }
    write_json(prompt_path, prompt_payload)

    manifest = {
        "schema_version": "1.0",
        "artifact_type": "flux2_repair_packet_sdxl_inpaint_binding",
        "binding_id": output_dir.name,
        "classification": "SDXL_REALVISXL_STRUCTURAL_REMOVAL_PILOT_STATIC_PASS_EXECUTION_BLOCKED",
        "result": "unproven_structural_profile_static_binding_pass_runtime_not_executed",
        "source_repair_packet": {
            "path": project_path(root, packet_path),
            "sha256": sha256_file(packet_path),
        },
        "lane": {
            "lane_id": lane_id,
            "workflow_path": project_path(root, workflow_path),
            "workflow_sha256": sha256_file(workflow_path),
            "patch_points_path": project_path(root, patch_path),
            "patch_points_sha256": sha256_file(patch_path),
            "runtime_requirements_path": project_path(root, requirements_path),
            "runtime_requirements_sha256": sha256_file(requirements_path),
            "checkpoint": matching_models[0],
            "existing_face_texture_certification_inherited": False,
            "existing_body_hand_contact_authority_inherited": False,
        },
        "structural_repair_profile": {
            "path": project_path(root, profile_path),
            "sha256": sha256_file(profile_path),
            "status": profile["status"],
            "calibration_status": sampler_profile["calibration_status"],
            "attempt_budget": hypothesis["attempt_budget"],
            "measured_delta_contract": measured_delta,
        },
        "input_provisioning": [
            {
                "role": "source_image",
                "source_path": project_path(root, source_path),
                "source_sha256": source_hash,
                "comfyui_input_name": source_input_name,
            },
            {
                "role": "operational_repair_mask",
                "source_path": project_path(root, mask_path),
                "source_sha256": mask_hash,
                "comfyui_input_name": mask_input_name,
                "classification": "non_gold_operational_repair_region",
                "consumed_as_evaluation_truth": False,
                "channel_verification": mask_channel_verification,
            },
        ],
        "prompt_request": {
            "path": project_path(root, prompt_path),
            "sha256": sha256_file(prompt_path),
            "patch_count": len(applied),
            "applied_patches": applied,
        },
        "sampler_settings": patch_values["sampler_settings"],
        "topology_checks": topology_checks,
        "runtime": {
            "execution_allowed": False,
            "comfyui_contacted": False,
            "ec2_started": False,
            "generation_executed": False,
            "candidate_count_allowed": 1,
            "source_preserving_composite_required": True,
            "direct_whole_image_visual_qa_required": True,
        },
        "exact_blockers": [
            "The source image and operational mask have not been provisioned to an active ComfyUI input directory for this binding.",
            "The exact RealVisXL checkpoint hash and required node surface have not been reverified inside a new guarded runtime window.",
            "The selected structural-removal denoise is an unproven one-attempt pilot and inherits no face, body, hand, or contact certification.",
            "No repair candidate, source-preserving composite, or direct whole-image visual QA exists for this binding.",
        ],
        "boundaries": {
            "cross_engine_transfer": "decoded_source_image_and_operational_mask_only",
            "cross_family_latent_transfer_allowed": False,
            "gold_mask_used": False,
            "operational_mask_promotable": False,
            "seed_loop_allowed": False,
            "production_promotion_allowed": False,
        },
        "next_action": (
            "Package this exact prompt plus the two hash-bound inputs for one guarded target-runtime candidate, "
            "then run the canonical source-preserving compositor and direct whole-image visual QA."
        ),
    }
    manifest_path = output_dir / "binding_manifest.json"
    write_json(manifest_path, manifest)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
