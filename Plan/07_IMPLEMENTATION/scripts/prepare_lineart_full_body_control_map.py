#!/usr/bin/env python3
"""Prepare a fail-closed realistic Lineart control map from one full-body source."""

from __future__ import annotations

import argparse
import hashlib
import json
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
    import torch
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal test envs
    torch = None

try:
    from PIL import Image
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal test envs
    Image = None


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = ROOT / "Ref_Image_1/Full/78b8e4ca10fd769e0752bd21c3599339.jpg"
EXPECTED_SOURCE_SHA256 = "e20a857f0ac23151ae1b8aa47fb4746c975e522a5598896f747ef08a50cc9336"
DEFAULT_OUTPUT_DIR = (
    ROOT
    / "Plan/Instructions/Operations/Prepared_Input_Assets/lineart_full_body_standing_w70_v1"
)
DEFAULT_ACTIVE_INPUT_NAME = "controlnet_lineart_full_body_standing_w70_v1.png"
EXPECTED_LANE = "sdxl_realvisxl_controlnet_lineart_lane"

AUX_SRC = ROOT / "ComfyUI/custom_nodes/comfyui_controlnet_aux/src"
ANNOTATOR_DIR = (
    ROOT
    / "ComfyUI/custom_nodes/comfyui_controlnet_aux/ckpts/lllyasviel/Annotators"
)
REQUIRED_MODELS = ("sk_model.pth", "sk_model2.pth")
EXPECTED_MODEL_SHA256 = {
    "sk_model.pth": "c686ced2a666b4850b4bb6ccf0748031c3eda9f822de73a34b8979970d90f0c6",
    "sk_model2.pth": "30a534781061f34e83bb9406b4335da4ff2616c95d22a585c1245aa8363e74e0",
}


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


def validate_active_input_name(value: str) -> str:
    candidate = Path(value)
    if candidate.name != value or candidate.suffix.lower() != ".png":
        raise ValueError("active input name must be one PNG basename")
    return value


def choose_device(requested: str) -> str:
    if torch is None:
        raise ModuleNotFoundError("torch is required to prepare lineart control maps")
    if requested == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    return requested


def source_selection_checks(source: Path, source_sha256: str) -> dict[str, bool]:
    source_rel = rel(source).lower()
    return {
        "source_is_ref_image_1_full": source_rel.startswith("ref_image_1/full/"),
        "source_outside_excluded_new_folder": "/full/new folder/" not in source_rel,
        "source_sha256_matches_expected": source_sha256 == EXPECTED_SOURCE_SHA256,
    }


def list_model_records(model_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for filename in REQUIRED_MODELS:
        path = model_dir / filename
        actual_sha256 = sha256_file(path) if path.is_file() else None
        expected_sha256 = EXPECTED_MODEL_SHA256[filename]
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


def line_pixel_stats(image_rgb: Image.Image) -> dict[str, float]:
    if np is None:
        raise ModuleNotFoundError("numpy is required for line pixel statistics")
    gray = np.asarray(image_rgb.convert("L"), dtype=np.float32)
    bright_contour_mask = gray > 24.0
    high_confidence_contour_mask = gray > 96.0
    dark_background_mask = gray < 16.0
    return {
        "min": float(gray.min()),
        "max": float(gray.max()),
        "mean": float(gray.mean()),
        "std": float(gray.std()),
        "bright_contour_pixel_ratio": float(bright_contour_mask.mean()),
        "high_confidence_contour_pixel_ratio": float(
            high_confidence_contour_mask.mean()
        ),
        "dark_background_pixel_ratio": float(dark_background_mask.mean()),
    }


def run_fail_closed_checks(
    source_size: tuple[int, int],
    control_size: tuple[int, int],
    control_bytes: int,
    source_checks: dict[str, bool],
    model_records: list[dict[str, Any]],
    stats: dict[str, float],
) -> dict[str, bool]:
    models_trusted = all(
        record["exists"] and record.get("sha256_matches_expected") is True
        for record in model_records
    )
    source_aspect = source_size[0] / source_size[1]
    control_aspect = control_size[0] / control_size[1]
    return {
        "control_map_nonempty": control_bytes > 0,
        "control_map_aspect_ratio_matches_source": abs(source_aspect - control_aspect)
        <= 0.002,
        "portrait_orientation_preserved": control_size[1] > control_size[0],
        "line_map_not_blank_by_std": stats["std"] >= 5.0,
        "bright_contour_ratio_gte_0_01": stats["bright_contour_pixel_ratio"]
        >= 0.01,
        "high_confidence_contour_ratio_gte_0_002": stats[
            "high_confidence_contour_pixel_ratio"
        ]
        >= 0.002,
        "dark_background_ratio_gte_0_85": stats["dark_background_pixel_ratio"]
        >= 0.85,
        "required_lineart_models_hash_trusted": models_trusted,
        "source_selection_boundary_pass": all(source_checks.values()),
    }


def load_lineart_detector(allow_model_download: bool, device: str):
    sys.path.insert(0, str(AUX_SRC))
    from custom_controlnet_aux.lineart import LineartDetector  # noqa: PLC0415

    missing_before = [name for name in REQUIRED_MODELS if not (ANNOTATOR_DIR / name).is_file()]
    bootstrap_downloaded = False
    if missing_before and not allow_model_download:
        raise FileNotFoundError(
            "Required local Lineart models missing and download is disabled: "
            f"{missing_before}. Re-run with --allow-model-download for one bootstrap."
        )

    existing_records = list_model_records(ANNOTATOR_DIR)
    mismatched_before = [
        record["filename"]
        for record in existing_records
        if record["exists"] and not record["sha256_matches_expected"]
    ]
    if mismatched_before:
        raise ValueError(
            "Existing Lineart model hashes do not match the pinned authority: "
            f"{mismatched_before}"
        )

    detector = LineartDetector.from_pretrained("lllyasviel/Annotators").to(device)
    bootstrap_downloaded = bool(missing_before)
    missing_after = [name for name in REQUIRED_MODELS if not (ANNOTATOR_DIR / name).is_file()]
    if missing_after:
        raise FileNotFoundError(
            f"Lineart model bootstrap did not provide required files: {missing_after}"
        )
    mismatched_after = [
        record["filename"]
        for record in list_model_records(ANNOTATOR_DIR)
        if not record["sha256_matches_expected"]
    ]
    if mismatched_after:
        raise ValueError(
            "Lineart model bootstrap hashes do not match the pinned authority: "
            f"{mismatched_after}"
        )
    return detector, bootstrap_downloaded


def main() -> int:
    if np is None:
        raise ModuleNotFoundError("numpy is required to prepare lineart control maps")
    if torch is None:
        raise ModuleNotFoundError("torch is required to prepare lineart control maps")
    if Image is None:
        raise ModuleNotFoundError("Pillow is required to prepare lineart control maps")
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--active-input-name", default=DEFAULT_ACTIVE_INPUT_NAME)
    parser.add_argument("--detect-resolution", type=int, default=1024)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--allow-model-download", action="store_true")
    args = parser.parse_args()

    source = args.source.resolve()
    output_dir = args.output_dir.resolve()
    active_input_name = validate_active_input_name(args.active_input_name)
    if not source.is_file():
        raise FileNotFoundError(f"Required local source missing: {source}")

    source_sha256 = sha256_file(source)
    source_checks = source_selection_checks(source, source_sha256)
    if not all(source_checks.values()):
        raise ValueError(f"Source authority checks failed: {source_checks}")

    device = choose_device(args.device)
    detector, bootstrap_downloaded = load_lineart_detector(
        allow_model_download=args.allow_model_download,
        device=device,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    source_copy = output_dir / "source_original.jpg"
    control_map = output_dir / active_input_name
    manifest_path = output_dir / "PREPARATION_MANIFEST.json"
    active_input_path = ROOT / "ComfyUI/input" / active_input_name

    with Image.open(source) as loaded:
        source_rgb = loaded.convert("RGB")
        source_size = source_rgb.size
    shutil.copy2(source, source_copy)

    rendered = detector(
        np.asarray(source_rgb),
        coarse=False,
        detect_resolution=args.detect_resolution,
        output_type="pil",
    ).convert("RGB")
    rendered.save(control_map, format="PNG")

    model_records = list_model_records(ANNOTATOR_DIR)
    stats = line_pixel_stats(rendered)
    checks = run_fail_closed_checks(
        source_size=source_size,
        control_size=rendered.size,
        control_bytes=control_map.stat().st_size,
        source_checks=source_checks,
        model_records=model_records,
        stats=stats,
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
        "manifest_id": "W70-LOCAL-LINEART-FULL-BODY-STANDING-CONTROL-MAP-V1",
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "pass": passed,
        "result": (
            "pass_local_lineart_full_body_control_map_prepared"
            if passed
            else "blocked_local_lineart_full_body_control_map_invalid"
        ),
        "target_lane_id": EXPECTED_LANE,
        "scope": "single_original_full_body_lineart_control_map",
        "source": {
            "path": rel(source),
            "sha256": source_sha256,
            "expected_sha256": EXPECTED_SOURCE_SHA256,
            "width": source_size[0],
            "height": source_size[1],
            "selection_boundary": (
                "Ref_Image_1/Full source only; excludes Ref_Image_1/Full/New folder; "
                "requires head, both hands, both legs, and both feet visible."
            ),
            "selection_reason": (
                "True full-body standing source visually verified with head, both hands, "
                "both legs, and both bare feet inside the frame."
            ),
            "selection_checks": source_checks,
        },
        "models": {
            "provider": "comfyui_controlnet_aux LineartDetector",
            "checkpoint_root": rel(ANNOTATOR_DIR),
            "required_files": model_records,
            "bootstrap_download_allowed": args.allow_model_download,
            "bootstrap_download_performed": bootstrap_downloaded,
            "network_contacted_for_model_bootstrap": bootstrap_downloaded,
            "device": device,
        },
        "inference": {
            "detector_variant": "lineart_realistic",
            "coarse": False,
            "detect_resolution": args.detect_resolution,
        },
        "outputs": {
            "source_copy": {
                "path": rel(source_copy),
                "sha256": sha256_file(source_copy),
                "size_bytes": source_copy.stat().st_size,
            },
            "control_map": {
                "path": rel(control_map),
                "sha256": sha256_file(control_map),
                "size_bytes": control_map.stat().st_size,
                "width": rendered.width,
                "height": rendered.height,
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

    del detector
    if device == "cuda":
        torch.cuda.empty_cache()
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
