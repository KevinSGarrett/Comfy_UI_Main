#!/usr/bin/env python3
"""Prepare a hash-verifiable Depth Anything control map from one full-body original."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForDepthEstimation


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = ROOT / "Ref_Image_1/Full/7ab4daaba22dba31ae206dbebd4fa8d3.jpg"
DEFAULT_OUTPUT_DIR = (
    ROOT / "Plan/Instructions/Operations/Prepared_Input_Assets/depth_full_body_arms_up_w70_v1"
)
DEFAULT_ACTIVE_INPUT_NAME = "controlnet_depth_anything_full_body_arms_up_w70_v1.png"
DEFAULT_MODEL_SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub/models--LiheYoung--depth-anything-small-hf/snapshots/25216a913fa218ccb7d58cce818d52b728b6c1f6"
)
REQUIRED_MODEL_COMPONENTS = ("config.json", "model.safetensors", "preprocessor_config.json")


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


def list_model_components(snapshot_dir: Path) -> list[dict[str, object]]:
    components: list[dict[str, object]] = []
    for item in sorted(snapshot_dir.rglob("*")):
        if item.is_file():
            components.append(
                {
                    "path": item.relative_to(snapshot_dir).as_posix(),
                    "sha256": sha256(item),
                    "size_bytes": item.stat().st_size,
                }
            )
    if not components:
        raise FileNotFoundError(f"No model component files found in snapshot: {snapshot_dir}")
    return components


def choose_device(requested: str) -> str:
    if requested == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    return requested


def resized_for_detect_resolution(image: Image.Image, detect_resolution: int) -> Image.Image:
    if detect_resolution <= 0:
        raise ValueError("detect_resolution must be > 0")
    width, height = image.size
    longest = max(width, height)
    scale = float(detect_resolution) / float(longest)
    resized_w = max(1, int(round(width * scale)))
    resized_h = max(1, int(round(height * scale)))
    return image.resize((resized_w, resized_h), resample=Image.Resampling.BICUBIC)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--model-snapshot", type=Path, default=DEFAULT_MODEL_SNAPSHOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--detect-resolution", type=int, default=768)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--active-input-name", default=DEFAULT_ACTIVE_INPUT_NAME)
    args = parser.parse_args()

    source = args.source.resolve()
    snapshot_dir = args.model_snapshot.resolve()
    output_dir = args.output_dir.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Required local source missing: {source}")
    if not snapshot_dir.is_dir():
        raise FileNotFoundError(f"Required local model snapshot missing: {snapshot_dir}")
    missing_components = [name for name in REQUIRED_MODEL_COMPONENTS if not (snapshot_dir / name).is_file()]
    if missing_components:
        raise FileNotFoundError(f"Required local model components missing: {missing_components}")

    model_components = list_model_components(snapshot_dir)
    device = choose_device(args.device)
    loader_configuration = {
        "pretrained_source": str(snapshot_dir),
        "source_is_local_directory": snapshot_dir.is_dir(),
        "local_files_only": True,
        "remote_model_id_used": False,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    source_copy = output_dir / "source_original.jpg"
    control_map = output_dir / args.active_input_name
    manifest_path = output_dir / "PREPARATION_MANIFEST.json"

    with Image.open(source) as loaded:
        source_image = loaded.convert("RGB")
        source_w, source_h = source_image.size
        source_image.save(source_copy, format="JPEG", quality=95, subsampling=0)

    prepared_for_inference = resized_for_detect_resolution(source_image, args.detect_resolution)
    infer_w, infer_h = prepared_for_inference.size

    model = None
    try:
        image_processor = AutoImageProcessor.from_pretrained(
            loader_configuration["pretrained_source"],
            local_files_only=loader_configuration["local_files_only"],
        )
        model = AutoModelForDepthEstimation.from_pretrained(
            loader_configuration["pretrained_source"],
            local_files_only=loader_configuration["local_files_only"],
        ).to(device)
        model.eval()

        inputs = image_processor(images=prepared_for_inference, return_tensors="pt")
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.inference_mode():
            predicted_depth = model(**inputs).predicted_depth
        depth = F.interpolate(
            predicted_depth.unsqueeze(1),
            size=(source_h, source_w),
            mode="bicubic",
            align_corners=False,
        ).squeeze(1)
        depth_array = depth.squeeze(0).detach().cpu().numpy().astype(np.float32)
    finally:
        if model is not None:
            del model
        if device == "cuda":
            torch.cuda.empty_cache()

    min_depth = float(depth_array.min())
    max_depth = float(depth_array.max())
    depth_range = max_depth - min_depth
    if depth_range <= 1e-6:
        raise RuntimeError("Depth output is flat; refusing to continue")

    normalized = ((depth_array - min_depth) / depth_range) * 255.0
    depth_u8 = np.clip(normalized, 0.0, 255.0).astype(np.uint8)
    depth_rgb = np.repeat(depth_u8[:, :, None], 3, axis=2)
    rendered = Image.fromarray(depth_rgb, mode="RGB")
    rendered.save(control_map, format="PNG")

    pixels = depth_u8.astype(np.float32)
    output_stats = {
        "min": float(pixels.min()),
        "max": float(pixels.max()),
        "mean": float(pixels.mean()),
        "std": float(pixels.std()),
    }
    checks = {
        "control_map_nonempty": control_map.is_file() and control_map.stat().st_size > 0,
        "portrait_output": rendered.height > rendered.width,
        "depth_map_not_flat": output_stats["std"] >= 3.0,
        "depth_dynamic_range_gte_12": (output_stats["max"] - output_stats["min"]) >= 12.0,
        "source_outside_excluded_new_folder": "new folder" not in str(source).lower(),
        "gold_masks_not_consumed": "gold" not in str(source).lower(),
        "required_model_components_present": not missing_components,
        "local_files_only_enabled": loader_configuration["local_files_only"] is True,
        "network_fallback_disabled": (
            loader_configuration["source_is_local_directory"] is True
            and loader_configuration["remote_model_id_used"] is False
        ),
    }
    passed = all(checks.values())

    manifest = {
        "schema_version": "1.0",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "result": (
            "pass_local_depth_anything_full_body_control_map_prepared"
            if passed
            else "blocked_local_depth_anything_control_map_invalid"
        ),
        "pass": passed,
        "scope": "single_original_full_body_depth_control_map",
        "source": {
            "path": rel(source),
            "sha256": sha256(source),
            "width": source_w,
            "height": source_h,
            "selection_reason": "true full body with head, both hands, both legs, and both bare feet visible in a clean studio pose",
        },
        "model_snapshot": {
            "path": str(snapshot_dir),
            "component_count": len(model_components),
            "components": model_components,
            "device": device,
            "local_only": True,
        },
        "inference": {
            "detect_resolution": args.detect_resolution,
            "inference_width": infer_w,
            "inference_height": infer_h,
            "preserve_aspect_ratio": True,
            "loader_configuration": loader_configuration,
        },
        "outputs": {
            "source_copy": {
                "path": rel(source_copy),
                "sha256": sha256(source_copy),
                "size_bytes": source_copy.stat().st_size,
            },
            "control_map": {
                "path": rel(control_map),
                "sha256": sha256(control_map),
                "size_bytes": control_map.stat().st_size,
                "width": rendered.width,
                "height": rendered.height,
                "min": output_stats["min"],
                "max": output_stats["max"],
                "mean": output_stats["mean"],
                "std": output_stats["std"],
            },
        },
        "checks": checks,
        "local_only_boundaries": [
            "Model loader uses local_files_only=True for processor and model.",
            "Model path is an explicit local snapshot directory, not a remote id.",
            "No network fallback path is configured.",
        ],
        "limitations": [
            "This prepares a local depth control map only.",
            "No gold mask was read, compared, promoted, or treated as truth.",
            "No runtime generation, hard gate, or Wave71+ activation is performed.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))

    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
