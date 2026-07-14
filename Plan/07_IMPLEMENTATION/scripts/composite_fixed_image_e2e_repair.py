#!/usr/bin/env python3
"""Recover a source-preserving repair image from a masked ComfyUI output."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageFilter
from skimage.metrics import structural_similarity


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8)


def load_mask(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("L"), dtype=np.uint8)


def masked_mae(left: np.ndarray, right: np.ndarray, mask: np.ndarray) -> float:
    if not np.any(mask):
        return 0.0
    delta = np.abs(left.astype(np.float32) - right.astype(np.float32))
    return float(delta[mask].mean())


def source_preserving_composite(
    source: np.ndarray,
    generated: np.ndarray,
    mask: np.ndarray,
    blur_radius: float,
) -> tuple[np.ndarray, np.ndarray]:
    if source.shape != generated.shape:
        raise ValueError("source and generated dimensions differ")
    if source.shape[:2] != mask.shape:
        raise ValueError("mask dimensions differ from source")

    hard_mask = mask > 0
    hard_composite = source.copy()
    hard_composite[hard_mask] = generated[hard_mask]

    soft = Image.fromarray(mask, mode="L")
    if blur_radius > 0:
        soft = soft.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    alpha = np.asarray(soft, dtype=np.float32)[..., None] / 255.0
    result = (
        source.astype(np.float32) * (1.0 - alpha)
        + hard_composite.astype(np.float32) * alpha
    )
    return np.clip(np.rint(result), 0, 255).astype(np.uint8), hard_mask


def evaluate(
    source: np.ndarray,
    generated: np.ndarray,
    repaired: np.ndarray,
    hard_mask: np.ndarray,
    thresholds: dict[str, Any],
) -> dict[str, Any]:
    outside_mask = ~hard_mask
    outside_only = repaired.copy()
    outside_only[hard_mask] = source[hard_mask]

    inside_mae = masked_mae(source, repaired, hard_mask)
    outside_mae = masked_mae(source, repaired, outside_mask)
    whole_ssim = float(
        structural_similarity(source, repaired, channel_axis=2, data_range=255)
    )
    outside_ssim = float(
        structural_similarity(source, outside_only, channel_axis=2, data_range=255)
    )
    raw_outside = generated[outside_mask]
    raw_black_pixel_ratio = float(
        np.mean(np.all(raw_outside <= 1, axis=1)) if raw_outside.size else 0.0
    )

    checks = {
        "minimum_inside_mask_mae": inside_mae
        >= float(thresholds["minimum_inside_mask_mae"]),
        "maximum_outside_mask_mae": outside_mae
        <= float(thresholds["maximum_outside_mask_mae"]),
        "minimum_outside_mask_ssim": outside_ssim
        >= float(thresholds["minimum_outside_mask_ssim"]),
        "minimum_whole_image_ssim": whole_ssim
        >= float(thresholds["minimum_whole_image_ssim"]),
    }
    return {
        "inside_mask_mae": inside_mae,
        "outside_mask_mae": outside_mae,
        "outside_mask_ssim": outside_ssim,
        "whole_image_ssim": whole_ssim,
        "raw_generated_outside_mask_black_pixel_ratio": raw_black_pixel_ratio,
        "checks": checks,
        "technical_pass": all(checks.values()),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--generated", type=Path, required=True)
    parser.add_argument("--mask", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--expected-source-sha256")
    parser.add_argument("--expected-generated-sha256")
    parser.add_argument("--expected-mask-sha256")
    parser.add_argument("--blur-radius", type=float, default=8.0)
    return parser.parse_args()


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    registry_path = resolve(root, args.registry).resolve()
    paths = {
        "source": resolve(root, args.source).resolve(),
        "generated": resolve(root, args.generated).resolve(),
        "mask": resolve(root, args.mask).resolve(),
        "output": resolve(root, args.output).resolve(),
        "evidence": resolve(root, args.evidence).resolve(),
    }
    registry = json.loads(registry_path.read_text(encoding="utf-8"))

    expected_hashes = {
        "source": args.expected_source_sha256,
        "generated": args.expected_generated_sha256,
        "mask": args.expected_mask_sha256,
    }
    actual_hashes = {
        name: sha256_file(paths[name]) for name in ("source", "generated", "mask")
    }
    hash_checks = {
        name: expected is None or actual_hashes[name] == expected.lower()
        for name, expected in expected_hashes.items()
    }
    if not all(hash_checks.values()):
        raise ValueError(f"input hash mismatch: {hash_checks}")

    source = load_rgb(paths["source"])
    generated = load_rgb(paths["generated"])
    mask = load_mask(paths["mask"])
    repaired, hard_mask = source_preserving_composite(
        source, generated, mask, args.blur_radius
    )
    metrics = evaluate(
        source,
        generated,
        repaired,
        hard_mask,
        registry["measured_delta_contract"]["repair"],
    )

    paths["output"].parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(repaired, mode="RGB").save(paths["output"], format="PNG")
    output_hash = sha256_file(paths["output"])

    evidence = {
        "schema_version": "1.0",
        "evidence_id": "W64-FIXED-IMAGE-E2E-REPAIR-SOURCE-PRESERVING-COMPOSITE",
        "generated_at": datetime.now().astimezone().isoformat(),
        "classification": (
            "FIXED_IMAGE_E2E_REPAIR_TECHNICAL_PASS_VISUAL_REVIEW_REQUIRED"
            if metrics["technical_pass"]
            else "FIXED_IMAGE_E2E_REPAIR_TECHNICAL_FAIL"
        ),
        "chain_sample_id": registry["chain_sample_id"],
        "inputs": {
            name: {"path": str(paths[name]), "sha256": actual_hashes[name]}
            for name in ("source", "generated", "mask")
        },
        "input_hash_checks": hash_checks,
        "output": {"path": str(paths["output"]), "sha256": output_hash},
        "blur_radius": args.blur_radius,
        "metrics": metrics,
        "normalization": "source_preserving_operational_mask_composite",
        "runtime_defect_recovered": None,
        "mask_boundary": {
            "classification": "non_gold_operational_repair_region",
            "consumed_as_evaluation_truth": False,
            "mask_promotion_allowed": False,
        },
        "visual_review_required": True,
        "final_certification_implied": False,
    }
    paths["evidence"].parent.mkdir(parents=True, exist_ok=True)
    paths["evidence"].write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(evidence, indent=2))
    return 0 if metrics["technical_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
