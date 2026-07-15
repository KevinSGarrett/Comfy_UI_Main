#!/usr/bin/env python3
"""Prepare, but never decide, the Row022 pose/depth visual-review packet."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[3]
SELECTED_FRAME_INDEXES = [0, 8, 16, 24, 32, 40, 48]


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


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def make_alignment_sheet(
    source_paths: list[Path], pose_paths: list[Path], depth_paths: list[Path], destination: Path
) -> None:
    tile_width, tile_height = 180, 240
    label_height = 22
    sheet = Image.new(
        "RGB",
        (len(SELECTED_FRAME_INDEXES) * tile_width, 3 * (tile_height + label_height)),
        "black",
    )
    draw = ImageDraw.Draw(sheet)
    for column, index in enumerate(SELECTED_FRAME_INDEXES):
        for row, (label, paths) in enumerate(
            (("source", source_paths), ("pose", pose_paths), ("relative depth", depth_paths))
        ):
            with Image.open(paths[index]) as source:
                image = source.convert("RGB")
                image.thumbnail((tile_width, tile_height), Image.Resampling.LANCZOS)
            x = column * tile_width + (tile_width - image.width) // 2
            y0 = row * (tile_height + label_height)
            y = y0 + label_height + (tile_height - image.height) // 2
            sheet.paste(image, (x, y))
            draw.text((column * tile_width + 4, y0 + 4), f"f{index:02d} {label}", fill="white")
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, format="PNG")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-frames-dir", type=Path, required=True)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    source_paths = sorted(args.source_frames_dir.resolve().glob("frame_*.png"))
    pose_paths = sorted((args.runtime_dir.resolve() / "pose").glob("frame_*.png"))
    depth_paths = sorted((args.runtime_dir.resolve() / "depth").glob("frame_*.png"))
    if not (len(source_paths) == len(pose_paths) == len(depth_paths) == 49):
        raise ValueError("Visual review packet requires exactly 49 source, pose, and depth frames")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    alignment_path = output_dir / "source_pose_depth_alignment_sheet.png"
    make_alignment_sheet(source_paths, pose_paths, depth_paths, alignment_path)
    pose_sheet = output_dir / "pose_contact_sheet.png"
    depth_sheet = output_dir / "depth_contact_sheet.png"
    if not pose_sheet.is_file() or not depth_sheet.is_file():
        raise FileNotFoundError("Technical revalidation contact sheets are missing")
    request = {
        "schema_name": "wave64_reference_pose_depth_visual_review_request",
        "schema_version": "1.0",
        "tracker_id": "TRK-W64-022",
        "item_id": "ITEM-W64-022",
        "status": "pending_direct_visual_judgment",
        "inputs": {
            "pose_contact_sheet": {"path": rel(pose_sheet), "sha256": sha256(pose_sheet)},
            "depth_contact_sheet": {"path": rel(depth_sheet), "sha256": sha256(depth_sheet)},
            "alignment_sheet": {"path": rel(alignment_path), "sha256": sha256(alignment_path)},
        },
        "required_judgments": [
            "pose_single_subject_continuity",
            "pose_body_attachment_and_limb_continuity",
            "pose_frame_order_and_motion_progression",
            "depth_subject_background_separation",
            "depth_spatial_coherence",
            "depth_temporal_progression",
            "source_pose_depth_alignment",
        ],
        "decision_claimed": False,
        "automated_visual_pass_forbidden": True,
    }
    write_json(output_dir / "visual_review_request.json", request)
    print(json.dumps({"result": "review_packet_prepared_no_decision", **request["inputs"]}, indent=2))


if __name__ == "__main__":
    main()
