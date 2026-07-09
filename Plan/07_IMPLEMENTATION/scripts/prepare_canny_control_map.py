#!/usr/bin/env python3
"""Prepare a deterministic local Canny-style control map for ControlNet lanes."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_path(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def threshold(image: Image.Image, cutoff: int) -> Image.Image:
    return image.point(lambda px: 255 if px >= cutoff else 0).convert("L")


def prepare_raw_control(source: Path) -> Image.Image:
    with Image.open(source) as im:
        gray = ImageOps.fit(
            im.convert("L"),
            (1024, 1024),
            method=Image.Resampling.LANCZOS,
        )
    edges = gray.filter(ImageFilter.FIND_EDGES)
    contrasted = ImageOps.autocontrast(edges, cutoff=1)
    return threshold(contrasted, 36)


def prepare_clean_control(raw: Image.Image) -> Image.Image:
    small = raw.resize((512, 512), Image.Resampling.BILINEAR)
    filtered = small.filter(ImageFilter.MedianFilter(size=3))
    filtered = filtered.filter(ImageFilter.MaxFilter(size=3))
    filtered = threshold(filtered, 96)
    filtered = filtered.filter(ImageFilter.MinFilter(size=3))
    return filtered.resize((1024, 1024), Image.Resampling.NEAREST).convert("L")


def image_record(project_root: Path, role: str, path: Path) -> dict:
    with Image.open(path) as im:
        width, height = im.size
        mode = im.mode
    return {
        "role": role,
        "path": repo_path(project_root, path),
        "filename": path.name,
        "width": width,
        "height": height,
        "mode": mode,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=r"C:\Comfy_UI_Main")
    parser.add_argument("--source-image", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--raw-name", default="controlnet_canny_corrected_white_edges_black_bg.png")
    parser.add_argument("--clean-name", default="controlnet_canny_cleaned_eye_safe_v1.png")
    parser.add_argument("--copy-to-comfy-input", action="store_true")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    source = Path(args.source_image)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not source.is_file():
        raise FileNotFoundError(f"Source image not found: {source}")

    raw_path = out_dir / args.raw_name
    clean_path = out_dir / args.clean_name

    raw = prepare_raw_control(source)
    raw.save(raw_path)
    clean = prepare_clean_control(raw)
    clean.save(clean_path)

    copied_to_comfy_input = []
    if args.copy_to_comfy_input:
        input_dir = project_root / "ComfyUI" / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        for path in (raw_path, clean_path):
            destination = input_dir / path.name
            shutil.copy2(path, destination)
            copied_to_comfy_input.append(repo_path(project_root, destination))

    with Image.open(source) as im:
        source_width, source_height = im.size
        source_mode = im.mode

    manifest = {
        "schema_version": "1.0",
        "manifest_id": "W69-CONTROLNET-CANNY-PREPROCESS-MODULE-V1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(project_root),
        "lane_id": "sdxl_realvisxl_controlnet_canny_lane",
        "module_id": "MOD-17-CONTROLNET-CANNY-LANE",
        "source_requirement": "Plan/07_IMPLEMENTATION/COMFYUI_WIRING_REPAIR_LIST.md Priority 2: Create control-map preprocessing module; feed actual control maps into ControlNet.",
        "local_only": True,
        "aws_contacted": False,
        "github_api_contacted": False,
        "civitai_contacted": False,
        "ec2_started": False,
        "generation_executed": False,
        "source_image": {
            "path": repo_path(project_root, source),
            "width": source_width,
            "height": source_height,
            "mode": source_mode,
            "bytes": source.stat().st_size,
            "sha256": sha256_file(source),
        },
        "processing": {
            "raw_control": [
                "convert source to grayscale",
                "fit to 1024x1024 with LANCZOS",
                "Pillow FIND_EDGES",
                "autocontrast cutoff=1",
                "threshold >=36 to white on black",
            ],
            "clean_control": [
                "resize raw control 1024->512 bilinear",
                "median filter size=3",
                "max filter size=3",
                "threshold >=96",
                "min filter size=3",
                "resize cleaned control 512->1024 nearest",
            ],
        },
        "outputs": [
            image_record(project_root, "raw_canny_control_map", raw_path),
            image_record(project_root, "cleaned_eye_safe_canny_control_map", clean_path),
        ],
        "copied_to_comfy_input": copied_to_comfy_input,
        "result": "prepared_local_canny_control_map_module_outputs",
        "next_action": "Use the cleaned eye-safe Canny control map as the ControlNet LoadImage input after lane-level hash/path evidence is recorded.",
    }

    manifest_path = out_dir / "CONTROL_MAP_PREPROCESS_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
