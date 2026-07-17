#!/usr/bin/env python3
"""Build a hash-bound, fail-closed localized anatomy repair packet."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


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


def parse_point(value: str) -> tuple[int, int]:
    try:
        x_text, y_text = value.split(",", 1)
        return int(x_text), int(y_text)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("points must use x,y integer syntax") from exc


def validate_region(
    bbox: tuple[int, int, int, int],
    polygon: list[tuple[int, int]],
    dimensions: tuple[int, int],
) -> None:
    x, y, width, height = bbox
    image_width, image_height = dimensions
    if width <= 0 or height <= 0:
        raise ValueError("defect bbox width and height must be positive")
    if x < 0 or y < 0 or x + width > image_width or y + height > image_height:
        raise ValueError("defect bbox exceeds source image dimensions")
    if len(polygon) < 3:
        raise ValueError("defect polygon requires at least three points")
    for point_x, point_y in polygon:
        if not (x <= point_x <= x + width and y <= point_y <= y + height):
            raise ValueError("defect polygon point falls outside defect bbox")


def run_checked(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stdout}{result.stderr}"
        )
    return result.stdout.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--qualification-evidence", type=Path, required=True)
    parser.add_argument("--prompt-request", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--defect-region-id", required=True)
    parser.add_argument("--defect-description", required=True)
    parser.add_argument("--bbox", type=int, nargs=4, metavar=("X", "Y", "W", "H"), required=True)
    parser.add_argument("--polygon", type=parse_point, nargs="+", required=True)
    parser.add_argument("--context-margin", type=int, default=96)
    parser.add_argument("--character-id", default="unknown_single_adult")
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    evidence_path = resolve_under(root, args.qualification_evidence)
    prompt_path = resolve_under(root, args.prompt_request)
    output_dir = resolve_under(root, args.output_dir)

    qualification = json.loads(evidence_path.read_text(encoding="utf-8"))
    samples = qualification.get("visual_qa", {}).get("samples", [])
    matching = [sample for sample in samples if sample.get("seed") == args.seed]
    if len(matching) != 1:
        raise ValueError(f"expected one qualification sample for seed {args.seed}")
    sample = matching[0]
    if not str(sample.get("result", "")).startswith("fail_"):
        raise ValueError("localized repair packets require a failed visual-QA sample")

    source_path = resolve_under(root, Path(sample["artifact"]))
    source_hash = sha256_file(source_path)
    if source_hash != str(sample.get("sha256", "")).lower():
        raise ValueError("qualification source image hash mismatch")
    with Image.open(source_path) as source_image:
        dimensions = source_image.size

    prompt = json.loads(prompt_path.read_text(encoding="utf-8"))
    prompt_seeds = [
        node.get("inputs", {}).get("noise_seed")
        for node in prompt.get("prompt", {}).values()
        if isinstance(node, dict) and "noise_seed" in node.get("inputs", {})
    ]
    if prompt_seeds != [args.seed]:
        raise ValueError("prompt request seed does not match repair seed")

    bbox = tuple(args.bbox)
    polygon = list(args.polygon)
    validate_region(bbox, polygon, dimensions)
    if args.context_margin < 0:
        raise ValueError("context margin cannot be negative")
    x, y, width, height = bbox
    image_width, image_height = dimensions
    crop_left = max(0, x - args.context_margin)
    crop_top = max(0, y - args.context_margin)
    crop_right = min(image_width, x + width + args.context_margin)
    crop_bottom = min(image_height, y + height + args.context_margin)
    context_crop = [crop_left, crop_top, crop_right - crop_left, crop_bottom - crop_top]

    output_dir.mkdir(parents=True, exist_ok=True)
    mask_path = output_dir / "operational_repair_mask.png"
    mask = Image.new("L", dimensions, 0)
    ImageDraw.Draw(mask).polygon(polygon, fill=255)
    mask.save(mask_path, format="PNG")
    if mask.getbbox() is None:
        raise ValueError("operational repair mask is empty")

    evidence_ref = project_path(root, evidence_path)
    request = {
        "source_image_id": sample["run_id"],
        "character_id": args.character_id,
        "repair_regions": [args.defect_region_id],
        "crop_plans": [
            {
                "crop_id": f"crop_{args.defect_region_id}",
                "region_id": args.defect_region_id,
                "bbox_xywh": list(bbox),
                "polygon_xy": [list(point) for point in polygon],
                "context_crop_xywh": context_crop,
                "context_margin_px": args.context_margin,
                "mask_classification": "non_gold_operational_repair_region",
            }
        ],
        "qa_goals": [
            "remove_detached_extra_anatomy",
            "restore_background_surface_continuity",
            "preserve_subject_identity_pose_and_existing_anatomy",
            "pass_whole_image_visual_review",
        ],
        "global_preservation_goals": [
            "identity",
            "pose",
            "body_proportions",
            "frame_integrity",
            "contact_continuity",
            "ceramics_studio_composition",
        ],
        "anatomy_scorecard": {
            "status": "fail",
            "evidence_paths": [evidence_ref],
            "blockers": ["detached_extra_hand_and_forearm"],
            "local_score": 0.0,
            "global_score": 0.0,
            "regional_checks": [
                {
                    "region_id": args.defect_region_id,
                    "status": "fail",
                    "description": args.defect_description,
                }
            ],
        },
        "hands_feet_check": {
            "status": "fail",
            "evidence_paths": [evidence_ref],
            "blockers": ["extra_hand_count_and_ownership_failure"],
            "hands": {"status": "fail", "inspectable": True},
            "feet": {"status": "pass", "inspectable": True},
        },
        "face_teeth_eye_check": {
            "status": "pass",
            "evidence_paths": [evidence_ref],
            "blockers": [],
            "face": {"status": "pass", "inspectable": True},
            "eyes": {"status": "pass", "inspectable": True},
            "teeth": {"status": "not_applicable", "inspectable": False},
        },
        "hard_reject_on_deformation": {
            "enabled": True,
            "triggered": True,
            "reasons": ["detached_extra_hand_and_forearm"],
            "promotion_allowed": False,
        },
    }
    request_path = output_dir / "hard_anatomy_repair_request.json"
    contract_path = output_dir / "hard_anatomy_repair_contract.json"
    request_path.write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")

    script_dir = Path(__file__).resolve().parent
    compiler_path = script_dir / "compile_hard_anatomy_repair_contract.py"
    validator_path = script_dir / "validate_hard_anatomy_repair_contract.py"
    run_checked(
        [
            sys.executable,
            str(compiler_path),
            "--input",
            str(request_path),
            "--output",
            str(contract_path),
        ]
    )
    validator_stdout = run_checked(
        [sys.executable, str(validator_path), "--input", str(contract_path)]
    )
    if validator_stdout != "PASS":
        raise RuntimeError(f"unexpected hard-anatomy validator output: {validator_stdout}")

    packet = {
        "schema_version": "1.0",
        "artifact_type": "flux2_localized_anatomy_repair_packet",
        "packet_id": output_dir.name,
        "classification": "LOCALIZED_ANATOMY_REPAIR_PACKET_READY_GENERATION_NOT_EXECUTED",
        "result": "diagnosis_and_operational_mask_pass_runtime_repair_not_run",
        "source": {
            "path": project_path(root, source_path),
            "sha256": source_hash,
            "width": image_width,
            "height": image_height,
        },
        "prompt_request": {
            "path": project_path(root, prompt_path),
            "sha256": sha256_file(prompt_path),
            "seed": args.seed,
        },
        "qualification_evidence": {
            "path": evidence_ref,
            "sha256": sha256_file(evidence_path),
            "sample_result": sample["result"],
        },
        "defect": {
            "region_id": args.defect_region_id,
            "description": args.defect_description,
            "bbox_xywh": list(bbox),
            "polygon_xy": [list(point) for point in polygon],
            "context_crop_xywh": context_crop,
        },
        "operational_mask": {
            "path": project_path(root, mask_path),
            "sha256": sha256_file(mask_path),
            "classification": "non_gold_operational_repair_region",
            "consumed_as_evaluation_truth": False,
            "mask_promotion_allowed": False,
        },
        "hard_anatomy_contract": {
            "request_path": project_path(root, request_path),
            "request_sha256": sha256_file(request_path),
            "contract_path": project_path(root, contract_path),
            "contract_sha256": sha256_file(contract_path),
            "canonical_validator_result": validator_stdout,
            "promotion_allowed": False,
        },
        "runtime": {
            "generation_executed": False,
            "repair_candidate_generated": False,
            "source_preserving_composite_executed": False,
            "post_repair_visual_qa_complete": False,
            "runtime_execution_allowed": False,
        },
        "exact_blockers": [
            "An exact inpaint/edit workflow and model bundle are not bound to this packet.",
            "No localized repair candidate has been generated.",
            "No source-preserving composite or post-repair whole-image visual QA has run.",
        ],
        "boundaries": {
            "gold_mask_used": False,
            "candidate_mask_used_as_truth": False,
            "production_promotion_allowed": False,
            "seed_loop_allowed": False,
            "ec2_started": False,
        },
        "next_action": (
            "Bind one exact certified or qualification-eligible inpaint/edit workflow to the "
            "hash-locked source and operational mask, run one candidate, composite it with the "
            "source-preserving repair path, and perform direct whole-image visual QA."
        ),
    }
    packet_path = output_dir / "repair_packet.json"
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    print(packet_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
