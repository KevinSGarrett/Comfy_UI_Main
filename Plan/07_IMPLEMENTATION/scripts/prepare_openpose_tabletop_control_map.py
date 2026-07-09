#!/usr/bin/env python3
"""Create a deterministic OpenPose tabletop-hands control source and map.

This local utility prepares an explicit upper-body seated/tabletop pose target
for the OpenPose ControlNet lane. It writes:
- a human-readable source guide showing the tabletop and hands
- a black-background OpenPose-style control map for ComfyUI LoadImage
- a manifest with hashes, dimensions, and intended use boundaries
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw


WIDTH = 768
HEIGHT = 1024


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def draw_line(draw: ImageDraw.ImageDraw, a: tuple[int, int], b: tuple[int, int], color: tuple[int, int, int], width: int = 9) -> None:
    draw.line([a, b], fill=color, width=width)


def draw_joint(draw: ImageDraw.ImageDraw, p: tuple[int, int], r: int = 7, color: tuple[int, int, int] = (255, 255, 255)) -> None:
    x, y = p
    draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def draw_hand(draw: ImageDraw.ImageDraw, wrist: tuple[int, int], side: str) -> None:
    """Draw simple separated OpenPose-like hand rays and fingertips."""
    x, y = wrist
    direction = -1 if side == "left" else 1
    finger_color = (255, 255, 255)
    palm_color = (255, 210, 120)

    knuckles = [
        (x + direction * 18, y - 8),
        (x + direction * 22, y + 2),
        (x + direction * 18, y + 12),
        (x + direction * 10, y + 20),
        (x + direction * 2, y + 22),
    ]
    tips = [
        (x + direction * 47, y - 20),
        (x + direction * 56, y - 4),
        (x + direction * 50, y + 15),
        (x + direction * 33, y + 35),
        (x + direction * 12, y + 39),
    ]
    for knuckle, tip in zip(knuckles, tips):
        draw.line([wrist, knuckle, tip], fill=palm_color, width=4)
        draw_joint(draw, knuckle, r=4, color=finger_color)
        draw_joint(draw, tip, r=4, color=finger_color)
    draw_joint(draw, wrist, r=8, color=finger_color)


def build_source_guide(path: Path) -> None:
    img = Image.new("RGB", (WIDTH, HEIGHT), (32, 34, 34))
    d = ImageDraw.Draw(img)

    table_y = 742
    # Quiet composition guide: table plane, shoulders, arms, hands.
    d.rectangle([0, table_y, WIDTH, HEIGHT], fill=(82, 71, 60))
    d.line([(64, table_y), (WIDTH - 64, table_y)], fill=(176, 154, 126), width=8)
    d.ellipse([300, 118, 468, 300], outline=(214, 214, 204), width=8)
    d.line([(384, 300), (384, 500)], fill=(190, 190, 180), width=12)
    d.line([(258, 372), (510, 372)], fill=(190, 190, 180), width=12)
    d.line([(258, 372), (212, 545), (210, table_y - 14)], fill=(220, 210, 190), width=18)
    d.line([(510, 372), (556, 545), (558, table_y - 14)], fill=(220, 210, 190), width=18)
    d.ellipse([162, table_y - 42, 258, table_y + 14], outline=(245, 226, 190), width=8)
    d.ellipse([510, table_y - 42, 606, table_y + 14], outline=(245, 226, 190), width=8)
    d.rectangle([246, 384, 522, 706], outline=(92, 122, 156), width=8)
    d.text((64, 58), "OpenPose tabletop source guide: both hands separated on table", fill=(232, 232, 220))
    img.save(path)


def build_openpose_map(path: Path) -> None:
    img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    d = ImageDraw.Draw(img)

    # Body keypoints arranged for a seated upper-body composition.
    nose = (384, 170)
    neck = (384, 320)
    left_eye = (350, 153)
    right_eye = (418, 153)
    left_ear = (312, 174)
    right_ear = (456, 174)
    left_shoulder = (258, 372)
    right_shoulder = (510, 372)
    left_elbow = (212, 545)
    right_elbow = (556, 545)
    left_wrist = (210, 724)
    right_wrist = (558, 724)
    mid_hip = (384, 690)
    left_hip = (326, 690)
    right_hip = (442, 690)

    # OpenPose-like limb colors. Exact palette is less important than clear,
    # separated joints and no non-pose background contamination.
    draw_line(d, nose, neck, (255, 0, 85), 8)
    draw_line(d, neck, left_shoulder, (255, 85, 0), 9)
    draw_line(d, neck, right_shoulder, (255, 170, 0), 9)
    draw_line(d, left_shoulder, left_elbow, (170, 255, 0), 9)
    draw_line(d, left_elbow, left_wrist, (85, 255, 0), 9)
    draw_line(d, right_shoulder, right_elbow, (0, 255, 85), 9)
    draw_line(d, right_elbow, right_wrist, (0, 255, 170), 9)
    draw_line(d, neck, mid_hip, (0, 170, 255), 9)
    draw_line(d, mid_hip, left_hip, (0, 85, 255), 8)
    draw_line(d, mid_hip, right_hip, (85, 0, 255), 8)
    draw_line(d, nose, left_eye, (255, 255, 255), 4)
    draw_line(d, nose, right_eye, (255, 255, 255), 4)
    draw_line(d, left_eye, left_ear, (255, 255, 255), 4)
    draw_line(d, right_eye, right_ear, (255, 255, 255), 4)

    for point in [
        nose,
        neck,
        left_eye,
        right_eye,
        left_ear,
        right_ear,
        left_shoulder,
        right_shoulder,
        left_elbow,
        right_elbow,
        left_wrist,
        right_wrist,
        mid_hip,
        left_hip,
        right_hip,
    ]:
        draw_joint(d, point)

    draw_hand(d, left_wrist, "left")
    draw_hand(d, right_wrist, "right")
    img.save(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default="C:/Comfy_UI_Main")
    ap.add_argument("--out-dir", default="Plan/Instructions/Operations/Prepared_Input_Assets/openpose_hands_tabletop_w69_v1")
    ap.add_argument("--active-input-name", default="controlnet_openpose_hands_tabletop_w69_v1.png")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    out_dir = (root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    source_path = out_dir / "openpose_hands_tabletop_source_guide_w69_v1.png"
    map_path = out_dir / args.active_input_name
    input_path = root / "ComfyUI" / "input" / args.active_input_name
    input_path.parent.mkdir(parents=True, exist_ok=True)

    build_source_guide(source_path)
    build_openpose_map(map_path)
    input_path.write_bytes(map_path.read_bytes())

    assets = []
    for role, path in [
        ("source_guide", source_path),
        ("openpose_control_map", map_path),
        ("active_comfyui_input_copy", input_path),
    ]:
        with Image.open(path) as im:
            width, height = im.size
        assets.append(
            {
                "role": role,
                "path": rel(root, path),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "width": width,
                "height": height,
            }
        )

    manifest = {
        "schema_version": "1.0",
        "manifest_id": "W69-LOCAL-OPENPOSE-HANDS-TABLETOP-CONTROL-SOURCE-V1",
        "timestamp": "2026-07-07T07:18:00-05:00",
        "project_root": str(root),
        "lane_id": "sdxl_realvisxl_controlnet_openpose_lane",
        "module_id": "MOD-20-CONTROLNET-OPENPOSE-LANE",
        "local_only": True,
        "ec2_started": False,
        "aws_contacted": False,
        "github_api_contacted": False,
        "civitai_contacted": False,
        "purpose": "Prepare a new OpenPose control source/map with both hands separated on a tabletop contact line before rerunning OpenPose hands/tabletop robustness.",
        "assets": assets,
        "intended_next_use": "Patch or profile the OpenPose lane to use ComfyUI/input/controlnet_openpose_hands_tabletop_w69_v1.png for a bounded local hands/tabletop generation retry.",
        "promotion_boundary": "Prepared local input/control-map artifact only; not a generation pass, not hands/tabletop certification, and not target-runtime proof.",
        "result": "pass_local_openpose_hands_tabletop_control_source_prepared",
    }
    manifest_path = out_dir / "OPENPOSE_HANDS_TABLETOP_CONTROL_SOURCE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
