#!/usr/bin/env python3
"""Package the bounded Wave64 fluid-state runtime and direct visual-review chain."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from PIL import Image, ImageChops, ImageOps, ImageStat


TZ = ZoneInfo("America/Chicago")
BINDINGS = {
    "pair_manifest": "4778cf192c2ebbcec48ef54c332dac6d204bb427f555ca3ab639789062df45a4",
    "baseline": "acfc3598b059979a0c43af40a91e9305ffc86015af030f4543bb15c6798e881f",
    "txt2img_state": "6c4520f96a6c13bb386ccdb4b8207c9436c0a32e08554434587a778a529deeef",
    "img2img_manifest": "d104a562d18b966d7e36861967f4fdf96b03b4ec2b9e19e90c907df967847b1d",
    "img2img_state": "5b92c2a02a78b3f11ed3d6fe0c37a5475b45dfda56c175b9dba2c7f8901027c3",
    "masked_manifest": "4d009182692f6451a39950c6113cade8f8261d19adc0c8b2d3c9dc0e7ca51c02",
    "edit_mask": "27a2f999307a2be4785e86a5b987bfb650058f49983282fa5ac112de045182b5",
    "masked_state": "bb338a378c89d15eb000195d3e81f819283890736ac3cbeb55b57308deb8d74f",
    "pair_runner": "09b7091f22d4138fa104db536df83a914bb24e7e9342633e5ebb339a2d209271",
    "img2img_runner": "1faa95713a47c86c870874a5bdfb06d3375aac0d21b089b628604b19a28bf34a",
    "masked_runner": "abac84f789b432333a20c7d2a880e8853374c7b9a5534d6aa61401e1b4b4c1b8",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_hash(path: Path, expected: str, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"{label} missing: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"{label} hash drift: expected {expected}, got {actual}")
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": actual}


def require_normalized_text_hash(path: Path, expected: str, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"{label} missing: {path}")
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    actual = hashlib.sha256(normalized).hexdigest()
    if actual != expected:
        raise ValueError(f"{label} normalized hash drift: expected {expected}, got {actual}")
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": actual,
        "hash_basis": "git_normalized_lf",
    }


def load_bound_json(path: Path, expected: str, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    binding = require_hash(path, expected, label)
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return binding, payload


def verify_manifests(pair: dict[str, Any], img2img: dict[str, Any], masked: dict[str, Any]) -> None:
    if pair.get("status") != "PASS_TECHNICAL_PAIR_PENDING_DIRECT_VISUAL_REVIEW":
        raise ValueError("pair manifest status drift")
    if pair.get("runtime", {}).get("actual_generation_count") != 2:
        raise ValueError("pair generation count drift")
    if pair.get("runtime", {}).get("retry_count") != 0:
        raise ValueError("pair retry drift")
    if img2img.get("status") != "PASS_IMG2IMG_TECHNICAL_PENDING_DIRECT_VISUAL_REVIEW":
        raise ValueError("img2img manifest status drift")
    if img2img.get("runtime", {}).get("actual_candidate_count") != 1:
        raise ValueError("img2img candidate count drift")
    if img2img.get("runtime", {}).get("retry_count") != 0:
        raise ValueError("img2img retry drift")
    if masked.get("status") != "PASS_MASKED_INPAINT_TECHNICAL_PENDING_DIRECT_VISUAL_REVIEW":
        raise ValueError("masked manifest status drift")
    if masked.get("runtime", {}).get("actual_candidate_count") != 1:
        raise ValueError("masked candidate count drift")
    if masked.get("runtime", {}).get("retry_count") != 0:
        raise ValueError("masked retry drift")
    for payload in (pair, img2img, masked):
        boundaries = payload.get("boundaries", {})
        if boundaries.get("ec2_started") is not False or boundaries.get("aws_contacted") is not False:
            raise ValueError("local-only execution boundary drift")
        if boundaries.get("content_based_suppression") is not False:
            raise ValueError("content-based suppression boundary drift")
        if payload.get("gates", {}).get("production_certification_pass") is not False:
            raise ValueError("production certification must remain false")
        if payload.get("gates", {}).get("row_complete") is not False:
            raise ValueError("row completion must remain false")
    if masked.get("boundaries", {}).get("edit_region_mask_is_not_truth") is not True:
        raise ValueError("edit-mask truth boundary drift")
    if masked.get("boundaries", {}).get("mask_promotion") is not False:
        raise ValueError("mask promotion boundary drift")


def regional_difference(baseline: Path, candidate: Path, mask_path: Path) -> dict[str, Any]:
    with Image.open(baseline) as baseline_image, Image.open(candidate) as candidate_image, Image.open(mask_path) as mask_image:
        baseline_rgb = baseline_image.convert("RGB")
        candidate_rgb = candidate_image.convert("RGB")
        mask = mask_image.convert("L")
        if baseline_rgb.size != candidate_rgb.size or baseline_rgb.size != mask.size:
            raise ValueError("regional comparison dimension mismatch")
        difference = ImageChops.difference(baseline_rgb, candidate_rgb).convert("L")
        outside_mask = ImageOps.invert(mask)
        inside_mean = ImageStat.Stat(difference, mask=mask).mean[0] / 255.0
        outside_mean = ImageStat.Stat(difference, mask=outside_mask).mean[0] / 255.0
        return {
            "width": baseline_rgb.width,
            "height": baseline_rgb.height,
            "inside_edit_region_normalized_mean_absolute_difference": round(inside_mean, 8),
            "outside_edit_region_normalized_mean_absolute_difference": round(outside_mean, 8),
            "outside_region_byte_preservation_claimed": False,
            "metric_is_supporting_not_visual_authority": True,
        }


def copy_exact(source: Path, destination: Path, expected: str, label: str) -> dict[str, Any]:
    require_hash(source, expected, label)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or sha256_file(destination) != expected:
        temporary = destination.with_name(f".{destination.name}.tmp")
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination)
    return require_hash(destination, expected, f"durable {label}")


def write_exact(payload: dict[str, Any], outputs: list[Path]) -> str:
    encoded = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_bytes(encoded)
        os.replace(temporary, path)
    digest = hashlib.sha256(encoded).hexdigest()
    if any(sha256_file(path) != digest for path in outputs):
        raise ValueError("evidence mirrors diverged")
    return digest


def package(args: argparse.Namespace) -> dict[str, Any]:
    paths = {name: Path(getattr(args, name)).resolve() for name in BINDINGS}
    pair_binding, pair_manifest = load_bound_json(paths["pair_manifest"], BINDINGS["pair_manifest"], "pair manifest")
    img2img_binding, img2img_manifest = load_bound_json(
        paths["img2img_manifest"], BINDINGS["img2img_manifest"], "img2img manifest"
    )
    masked_binding, masked_manifest = load_bound_json(
        paths["masked_manifest"], BINDINGS["masked_manifest"], "masked manifest"
    )
    verify_manifests(pair_manifest, img2img_manifest, masked_manifest)
    bindings = {
        "pair_manifest": pair_binding,
        "baseline": require_hash(paths["baseline"], BINDINGS["baseline"], "baseline image"),
        "txt2img_state": require_hash(paths["txt2img_state"], BINDINGS["txt2img_state"], "txt2img state"),
        "img2img_manifest": img2img_binding,
        "img2img_state": require_hash(paths["img2img_state"], BINDINGS["img2img_state"], "img2img state"),
        "masked_manifest": masked_binding,
        "edit_mask": require_hash(paths["edit_mask"], BINDINGS["edit_mask"], "edit-region mask"),
        "masked_state": require_hash(paths["masked_state"], BINDINGS["masked_state"], "masked state"),
        "pair_runner": require_normalized_text_hash(paths["pair_runner"], BINDINGS["pair_runner"], "pair runner"),
        "img2img_runner": require_normalized_text_hash(
            paths["img2img_runner"], BINDINGS["img2img_runner"], "img2img runner"
        ),
        "masked_runner": require_normalized_text_hash(
            paths["masked_runner"], BINDINGS["masked_runner"], "masked-inpaint runner"
        ),
    }
    artifact_dir = Path(args.artifact_dir).resolve()
    durable_names = {
        "pair_manifest": "txt2img_pair_runtime_manifest.json",
        "baseline": "baseline_dry_state.png",
        "txt2img_state": "txt2img_tears_state.png",
        "img2img_manifest": "img2img_state_v2_runtime_manifest.json",
        "img2img_state": "img2img_tears_state_v2.png",
        "masked_manifest": "masked_inpaint_state_v3_runtime_manifest.json",
        "edit_mask": "under_eye_edit_region_mask.png",
        "masked_state": "masked_inpaint_tears_state_v3.png",
    }
    durable = {
        name: copy_exact(paths[name], artifact_dir / filename, BINDINGS[name], name)
        for name, filename in durable_names.items()
    }
    regional_metrics = regional_difference(paths["baseline"], paths["masked_state"], paths["edit_mask"])
    return {
        "schema_version": "1.0",
        "evidence_id": "W64_FLUID_BODY_STATE_CONTINUITY_DIRECT_RUNTIME_REVIEW_20260715T100719-0500",
        "created_iso": datetime.now(TZ).replace(microsecond=0).isoformat(),
        "tracker_id": "TRK-W64-056",
        "item_id": "ITEM-W64-056",
        "system_id": "fluid_body_state_continuity",
        "status": "BLOCKED_FLUID_STATE_SHOT_CONTINUITY_IDENTITY_DRIFT",
        "classification": "DIRECT_RUNTIME_REVIEW_EXECUTED_NO_ROUTE_PASSED_BOTH_STATE_AND_CONTINUITY",
        "artifact_bindings": bindings,
        "durable_artifacts": durable,
        "runtime_chain": {
            "legacy_dry_run_reused_as_design_input_only": True,
            "local_runtime_generation_count": 4,
            "route_count": 3,
            "candidate_retry_count": 0,
            "ec2_started": False,
            "aws_contacted": False,
        },
        "direct_visual_reviews": [
            {
                "route": "same_seed_txt2img_pair",
                "baseline_sha256": BINDINGS["baseline"],
                "candidate_sha256": BINDINGS["txt2img_state"],
                "planned_generated_state_match": True,
                "same_character_identity_continuity": False,
                "hair_continuity": False,
                "wardrobe_continuity": False,
                "camera_continuity": True,
                "background_continuity": True,
                "lighting_continuity": True,
                "decision": "fail_shot_continuity",
                "findings": [
                    "Bilateral running mascara and tear tracks are clear.",
                    "The generated woman is a different identity with changed face proportions and iris appearance.",
                    "The hairstyle changes from a high bun to pulled-back hair and the black V-neck changes to a crew neck."
                ],
            },
            {
                "route": "baseline_anchored_low_denoise_img2img",
                "baseline_sha256": BINDINGS["baseline"],
                "candidate_sha256": BINDINGS["img2img_state"],
                "planned_generated_state_match": False,
                "same_character_identity_continuity": True,
                "hair_continuity": True,
                "wardrobe_continuity": True,
                "camera_continuity": True,
                "background_continuity": True,
                "lighting_continuity": True,
                "decision": "fail_planned_state_missing",
                "findings": [
                    "Face identity, bun, V-neck, framing, background, and lighting are preserved.",
                    "The intended running mascara and bilateral wet tear tracks are not visibly established."
                ],
            },
            {
                "route": "deterministic_under_eye_masked_inpaint",
                "baseline_sha256": BINDINGS["baseline"],
                "candidate_sha256": BINDINGS["masked_state"],
                "edit_mask_sha256": BINDINGS["edit_mask"],
                "planned_generated_state_match": True,
                "same_character_identity_continuity": False,
                "hair_continuity": True,
                "wardrobe_continuity": True,
                "camera_continuity": True,
                "background_continuity": True,
                "lighting_continuity": True,
                "outside_edit_region_visual_continuity": True,
                "decision": "fail_identity_critical_eye_region_drift",
                "findings": [
                    "Bilateral mascara runoff and light tear-track cues are visible within the intended edit region.",
                    "The hair, V-neck, framing, background, lighting, and gross face structure remain visually stable.",
                    "Both irises change from brown to gray-blue and eye/brow detail changes inside the edit region, which is an identity-critical continuity defect."
                ],
            },
        ],
        "regional_difference_metrics": regional_metrics,
        "gates": {
            "model_or_runtime_capability_proof_present": True,
            "required_before_after_visual_evidence_present": True,
            "planned_state_achieved_by_at_least_one_route": True,
            "shot_continuity_achieved_by_at_least_one_route": True,
            "single_route_achieved_state_and_continuity": False,
            "bounded_direct_runtime_proof_pass": False,
            "production_certification_pass": False,
            "row_complete": False,
        },
        "remaining_blockers": [
            "No tested route simultaneously preserves identity-critical eye appearance and establishes the planned bilateral tear state.",
            "The txt2img route changes global identity, hair, and wardrobe.",
            "The low-denoise img2img route preserves continuity but does not establish the planned fluid state.",
            "The masked-inpaint route establishes fluid cues but changes iris color and eye/brow detail.",
            "Production robustness and multi-sample continuity remain untested because this bounded chain stopped after the architecture-level corrections."
        ],
        "boundaries": {
            "edit_region_mask_is_not_geometry_or_segmentation_truth": True,
            "mask_promotion": False,
            "body_or_contact_authority_claimed": False,
            "content_based_suppression": False,
            "adult_or_nsfw_asset_visibility_restricted": False,
            "no_additional_generation_authorized_from_this_evidence": True,
            "wave70_hard_gates_rerun": False,
            "wave71_activated": False,
            "jira_mutated": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in BINDINGS:
        parser.add_argument(f"--{name.replace('_', '-')}", dest=name, required=True)
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--qa-output", required=True)
    parser.add_argument("--tracker-output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = package(args)
    digest = write_exact(
        payload, [Path(args.qa_output).resolve(), Path(args.tracker_output).resolve()]
    )
    print(json.dumps({"classification": payload["classification"], "sha256": digest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
