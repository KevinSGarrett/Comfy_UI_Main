#!/usr/bin/env python3
"""Prepare a fail-closed Canny full-body control map from one source image."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import cv2
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal test envs
    cv2 = None
try:
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal test envs
    np = None


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = ROOT / "Ref_Image_1/Full/78b8e4ca10fd769e0752bd21c3599339.jpg"
EXPECTED_SOURCE_SHA256 = "e20a857f0ac23151ae1b8aa47fb4746c975e522a5598896f747ef08a50cc9336"
DEFAULT_OUTPUT_DIR = (
    ROOT / "Plan/Instructions/Operations/Prepared_Input_Assets/canny_full_body_standing_w70_v1"
)
ACTIVE_INPUT_NAME = "controlnet_canny_full_body_standing_w70_v1.png"
EXPECTED_LANE = "sdxl_realvisxl_controlnet_canny_lane"

TARGET_WIDTH = 768
TARGET_HEIGHT = 1024
GAUSSIAN_KERNEL = (5, 5)
GAUSSIAN_SIGMA = 1.4
CANNY_LOW = 100
CANNY_HIGH = 200
MIN_EDGE_DENSITY = 0.005


def sha256_file(path: Path) -> str:
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


def source_selection_checks(source: Path, source_sha256: str) -> dict[str, bool]:
    source_rel = rel(source).lower()
    return {
        "source_is_ref_image_1_full": source_rel.startswith("ref_image_1/full/"),
        "source_outside_excluded_new_folder": "/full/new folder/" not in source_rel,
        "source_sha256_matches_expected": source_sha256 == EXPECTED_SOURCE_SHA256,
    }


def validate_canny_parameters(
    kernel: tuple[int, int], sigma: float, low: int, high: int
) -> None:
    if kernel != GAUSSIAN_KERNEL:
        raise ValueError(f"Gaussian kernel must be {GAUSSIAN_KERNEL}, got {kernel}")
    if abs(sigma - GAUSSIAN_SIGMA) > 1e-6:
        raise ValueError(f"Gaussian sigma must be {GAUSSIAN_SIGMA}, got {sigma}")
    if low != CANNY_LOW or high != CANNY_HIGH:
        raise ValueError(
            f"Canny thresholds must be low/high={CANNY_LOW}/{CANNY_HIGH}, got {low}/{high}"
        )


def edge_pixel_stats(canny: np.ndarray) -> dict[str, Any]:
    white_mask = canny > 0
    edge_density = float(white_mask.mean())
    return {
        "min": float(canny.min()),
        "max": float(canny.max()),
        "mean": float(canny.mean()),
        "std": float(canny.std()),
        "edge_density": edge_density,
        "white_pixel_ratio": edge_density,
        "black_pixel_ratio": float((canny == 0).mean()),
        "unique_values": [int(value) for value in np.unique(canny)],
    }


def run_fail_closed_checks(
    source_size: tuple[int, int],
    control_size: tuple[int, int],
    control_bytes: int,
    source_checks: dict[str, bool],
    stats: dict[str, Any],
    source_sha256: str,
    source_copy_sha256: str,
) -> dict[str, bool]:
    source_aspect = source_size[0] / source_size[1]
    control_aspect = control_size[0] / control_size[1]
    unique_values = set(stats.get("unique_values", []))
    return {
        "control_map_nonempty": control_bytes > 0,
        "control_map_is_exact_768x1024": control_size == (TARGET_WIDTH, TARGET_HEIGHT),
        "control_map_aspect_ratio_matches_source": abs(source_aspect - control_aspect)
        <= 0.01,
        "control_map_binary_uint8_0_255_only": bool(unique_values)
        and unique_values.issubset({0, 255}),
        "control_map_contains_black_and_white": unique_values == {0, 255},
        "edge_map_not_blank_by_std": stats["std"] >= 5.0,
        "edge_density_gte_0_005": stats["edge_density"] >= MIN_EDGE_DENSITY,
        "edge_density_lte_0_35": stats["edge_density"] <= 0.35,
        "black_background_ratio_gte_0_65": stats["black_pixel_ratio"] >= 0.65,
        "source_selection_boundary_pass": all(source_checks.values()),
        "source_copy_hash_matches_source": source_copy_sha256 == source_sha256,
    }


def main() -> int:
    if cv2 is None:
        raise ModuleNotFoundError("opencv-python is required for Canny preparation")
    if np is None:
        raise ModuleNotFoundError("numpy is required for Canny preparation")
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--active-input-name", default=ACTIVE_INPUT_NAME)
    args = parser.parse_args()

    if args.active_input_name != ACTIVE_INPUT_NAME:
        raise ValueError(f"active input name must be exactly {ACTIVE_INPUT_NAME}")

    source = args.source.resolve()
    output_dir = args.output_dir.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Required local source missing: {source}")

    source_sha256 = sha256_file(source)
    source_checks = source_selection_checks(source, source_sha256)
    if not all(source_checks.values()):
        raise ValueError(f"Source authority checks failed: {source_checks}")

    validate_canny_parameters(
        kernel=GAUSSIAN_KERNEL,
        sigma=GAUSSIAN_SIGMA,
        low=CANNY_LOW,
        high=CANNY_HIGH,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    source_copy = output_dir / "source_original.jpg"
    control_map = output_dir / ACTIVE_INPUT_NAME
    manifest_path = output_dir / "PREPARATION_MANIFEST.json"
    active_input_path = ROOT / "ComfyUI/input" / ACTIVE_INPUT_NAME
    source_copy.write_bytes(source.read_bytes())
    source_copy_sha256 = sha256_file(source_copy)

    source_bgr = cv2.imread(str(source), cv2.IMREAD_COLOR)
    if source_bgr is None:
        raise ValueError(f"Unable to read source image for Canny: {source}")
    source_rgb = cv2.cvtColor(source_bgr, cv2.COLOR_BGR2RGB)
    source_height, source_width = source_rgb.shape[:2]
    resized = cv2.resize(
        source_rgb, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_AREA
    )
    gray = cv2.cvtColor(resized, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, GAUSSIAN_KERNEL, sigmaX=GAUSSIAN_SIGMA)
    edges = cv2.Canny(blurred, threshold1=CANNY_LOW, threshold2=CANNY_HIGH)
    if edges.dtype != np.uint8:
        raise ValueError(f"Canny output must be uint8, got {edges.dtype}")
    if not cv2.imwrite(str(control_map), edges) or not control_map.is_file():
        raise OSError(f"OpenCV failed to write Canny control map: {control_map}")

    stats = edge_pixel_stats(edges)
    checks = run_fail_closed_checks(
        source_size=(source_width, source_height),
        control_size=(TARGET_WIDTH, TARGET_HEIGHT),
        control_bytes=control_map.stat().st_size,
        source_checks=source_checks,
        stats=stats,
        source_sha256=source_sha256,
        source_copy_sha256=source_copy_sha256,
    )
    passed = all(checks.values())

    active_written = False
    active_sha256 = None
    if passed:
        active_input_path.parent.mkdir(parents=True, exist_ok=True)
        partial = active_input_path.with_name(active_input_path.name + ".partial")
        partial.write_bytes(control_map.read_bytes())
        partial.replace(active_input_path)
        active_written = True
        active_sha256 = sha256_file(active_input_path)

    manifest = {
        "schema_version": "1.0",
        "manifest_id": "W70-LOCAL-CANNY-FULL-BODY-STANDING-CONTROL-MAP-V1",
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "pass": passed,
        "result": (
            "pass_local_canny_full_body_control_map_prepared"
            if passed
            else "blocked_local_canny_full_body_control_map_invalid"
        ),
        "target_lane_id": EXPECTED_LANE,
        "scope": "single_original_full_body_canny_control_map",
        "source": {
            "path": rel(source),
            "sha256": source_sha256,
            "expected_sha256": EXPECTED_SOURCE_SHA256,
            "width": source_width,
            "height": source_height,
            "selection_boundary": (
                "Ref_Image_1/Full source only; excludes Ref_Image_1/Full/New folder."
            ),
            "selection_checks": source_checks,
        },
        "preprocess": {
            "operator": "opencv_canny",
            "opencv_version": cv2.__version__,
            "gaussian_kernel": [5, 5],
            "gaussian_sigma": 1.4,
            "canny_low_threshold": 100,
            "canny_high_threshold": 200,
            "note": "Pillow FIND_EDGES is never used.",
        },
        "outputs": {
            "source_copy": {
                "path": rel(source_copy),
                "sha256": source_copy_sha256,
                "size_bytes": source_copy.stat().st_size,
            },
            "control_map": {
                "path": rel(control_map),
                "sha256": sha256_file(control_map),
                "size_bytes": control_map.stat().st_size,
                "width": TARGET_WIDTH,
                "height": TARGET_HEIGHT,
                "pixel_stats": stats,
            },
            "active_input_copy": {
                "path": rel(active_input_path),
                "written": active_written,
                "sha256": active_sha256,
            },
        },
        "checks": checks,
        "boundaries": {
            "local_only": True,
            "generation_executed": False,
            "gold_masks_consumed": False,
            "mask_promotion_performed": False,
            "target_runtime_proof": False,
            "final_lane_certification": False,
            "aws_contacted": False,
            "ec2_started": False,
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
