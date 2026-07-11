#!/usr/bin/env python3
"""Prepare a hash-verifiable BAE normal map from one full-body original."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = ROOT / "Ref_Image_1/Full/78b8e4ca10fd769e0752bd21c3599339.jpg"
DEFAULT_MODEL = ROOT / "ComfyUI/custom_nodes/comfyui_controlnet_aux/ckpts/lllyasviel/Annotators/scannet.pt"
DEFAULT_OUTPUT_DIR = ROOT / "Plan/Instructions/Operations/Prepared_Input_Assets/normal_full_body_standing_w70_v1"


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--resolution", type=int, default=768)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--active-input-name", default="controlnet_normal_bae_full_body_standing_w70_v1.png")
    args = parser.parse_args()

    source = args.source.resolve()
    model_path = args.model.resolve()
    output_dir = args.output_dir.resolve()
    missing = [str(path) for path in (source, model_path) if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required local input missing: {missing}")

    aux_src = ROOT / "ComfyUI/custom_nodes/comfyui_controlnet_aux/src"
    sys.path.insert(0, str(aux_src))
    from custom_controlnet_aux.normalbae import NormalBaeDetector  # noqa: PLC0415

    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")

    output_dir.mkdir(parents=True, exist_ok=True)
    source_copy = output_dir / "source_original.jpg"
    control_map = output_dir / args.active_input_name
    manifest_path = output_dir / "PREPARATION_MANIFEST.json"

    with Image.open(source) as loaded:
        source_image = loaded.convert("RGB")
        source_size = source_image.size
        source_image.save(source_copy, format="JPEG", quality=95, subsampling=0)

    detector = NormalBaeDetector.from_pretrained().to(device)
    rendered = detector(
        np.asarray(source_image),
        detect_resolution=args.resolution,
        output_type="pil",
    )
    rendered.save(control_map, format="PNG")
    pixels = np.asarray(rendered, dtype=np.float32)
    channel_std = pixels.reshape(-1, 3).std(axis=0).tolist()
    global_std = float(pixels.std())
    non_black_ratio = float(np.mean(np.max(pixels, axis=2) > 8.0))
    checks = {
        "control_map_nonempty": control_map.stat().st_size > 0,
        "portrait_output": rendered.height > rendered.width,
        "normal_map_not_flat": global_std >= 10.0,
        "all_color_channels_vary": all(value >= 5.0 for value in channel_std),
        "non_black_pixel_ratio_gte_0_50": non_black_ratio >= 0.5,
        "source_outside_excluded_new_folder": "new folder" not in str(source).lower(),
        "gold_masks_not_consumed": True,
    }
    passed = all(checks.values())
    manifest = {
        "schema_version": "1.0",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "result": "pass_local_bae_normal_full_body_control_map_prepared" if passed else "blocked_local_bae_normal_control_map_invalid",
        "pass": passed,
        "scope": "single_original_full_body_normal_control_map",
        "source": {
            "path": rel(source),
            "sha256": sha256(source),
            "width": source_size[0],
            "height": source_size[1],
            "selection_reason": "true full body with head, both hands, both legs, and both feet visible against a clean studio background",
        },
        "model": {
            "path": rel(model_path),
            "sha256": sha256(model_path),
            "size_bytes": model_path.stat().st_size,
            "device": device,
        },
        "outputs": {
            "source_copy": {"path": rel(source_copy), "sha256": sha256(source_copy)},
            "control_map": {
                "path": rel(control_map),
                "sha256": sha256(control_map),
                "width": rendered.width,
                "height": rendered.height,
                "global_std": global_std,
                "channel_std": channel_std,
                "non_black_pixel_ratio": non_black_ratio,
            },
        },
        "checks": checks,
        "limitations": [
            "This is local control-map preparation, not body-mask or geometry authority.",
            "One BAE map does not certify full-body Normal ControlNet output or target-runtime behavior.",
            "No gold mask was read, compared, promoted, or treated as truth.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    del detector
    if device == "cuda":
        torch.cuda.empty_cache()
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
