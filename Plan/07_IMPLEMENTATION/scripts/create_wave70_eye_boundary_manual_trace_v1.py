#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
RUN_STAMP = "20260707T233500-0500"
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_eye_boundary_manual_trace_v1" / RUN_STAMP
QA_EVIDENCE = PROJECT_ROOT / (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    f"W70_EYE_BOUNDARY_MANUAL_TRACE_V1_{RUN_STAMP}.json"
)
TRACKER_EVIDENCE = PROJECT_ROOT / (
    "Plan/Tracker/Evidence/"
    f"W70_EYE_BOUNDARY_MANUAL_TRACE_V1_{RUN_STAMP}.json"
)

FACE_CROP = (205, 250, 535, 370)
LEFT_EYE_CROP = (235, 268, 360, 355)
RIGHT_EYE_CROP = (380, 270, 505, 355)

# Coordinates are absolute 768x768 source pixels, manually traced from high-zoom
# source/canny panels. These are boundary-source evidence only, not mask approval.
MANUAL_TRACE: dict[str, Any] = {
    "viewer_left_visible_eye_aperture": {
        "semantic_side": "image-left / viewer-left visible eye, partly hair-occluded",
        "trace_type": "closed_polygon",
        "points": [(280, 320), (292, 313), (313, 312), (329, 319), (325, 329), (300, 334), (282, 328)],
    },
    "viewer_right_visible_eye_aperture": {
        "semantic_side": "image-right / viewer-right visible eye, unobstructed",
        "trace_type": "closed_polygon",
        "points": [(402, 322), (417, 313), (445, 312), (467, 320), (461, 332), (433, 336), (410, 330)],
    },
    "viewer_left_visible_brow_hair": {
        "semantic_side": "image-left brow hair visible outside hair occlusion; occluded far-left brow is intentionally excluded",
        "trace_type": "closed_polygon",
        "points": [(273, 278), (312, 280), (339, 292), (334, 302), (292, 293), (274, 293)],
    },
    "viewer_right_visible_brow_hair": {
        "semantic_side": "image-right brow hair visible",
        "trace_type": "closed_polygon",
        "points": [(386, 292), (412, 281), (454, 281), (486, 293), (480, 303), (438, 294), (394, 302)],
    },
    "viewer_left_upper_lid_fold": {
        "semantic_side": "image-left upper eyelid fold",
        "trace_type": "polyline",
        "points": [(280, 314), (294, 307), (315, 307), (333, 315)],
    },
    "viewer_right_upper_lid_fold": {
        "semantic_side": "image-right upper eyelid fold",
        "trace_type": "polyline",
        "points": [(401, 314), (419, 306), (448, 306), (470, 316)],
    },
    "viewer_left_lower_lid_fold": {
        "semantic_side": "image-left lower eyelid fold",
        "trace_type": "polyline",
        "points": [(282, 333), (301, 339), (323, 334)],
    },
    "viewer_right_lower_lid_fold": {
        "semantic_side": "image-right lower eyelid fold",
        "trace_type": "polyline",
        "points": [(407, 335), (432, 342), (459, 337)],
    },
    "viewer_left_hair_occlusion_boundary": {
        "semantic_side": "hair boundary crossing image-left eye/brow region",
        "trace_type": "polyline",
        "points": [(253, 260), (263, 276), (270, 294), (276, 314), (271, 336), (260, 355)],
    },
}

COLORS = {
    "viewer_left_visible_eye_aperture": (0, 255, 255),
    "viewer_right_visible_eye_aperture": (0, 255, 255),
    "viewer_left_visible_brow_hair": (0, 255, 80),
    "viewer_right_visible_brow_hair": (0, 255, 80),
    "viewer_left_upper_lid_fold": (255, 140, 0),
    "viewer_right_upper_lid_fold": (255, 140, 0),
    "viewer_left_lower_lid_fold": (255, 180, 80),
    "viewer_right_lower_lid_fold": (255, 180, 80),
    "viewer_left_hair_occlusion_boundary": (255, 220, 0),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def font(size: int = 15) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def to_jsonable_trace() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in MANUAL_TRACE.items():
        out[key] = {
            **{k: v for k, v in value.items() if k != "points"},
            "points": [[int(x), int(y)] for x, y in value["points"]],
        }
    return out


def draw_trace(source: Image.Image, crop: tuple[int, int, int, int], scale: int, show_grid: bool) -> Image.Image:
    region = source.crop(crop).resize(((crop[2] - crop[0]) * scale, (crop[3] - crop[1]) * scale), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(region)
    x0, y0, x1, y1 = crop
    if show_grid:
        grid_font = font(10)
        for x in range(((x0 + 10 - 1) // 10) * 10, x1 + 1, 10):
            lx = (x - x0) * scale
            draw.line([(lx, 0), (lx, region.height)], fill=(90, 90, 90), width=1)
            if x % 20 == 0:
                draw.text((lx + 2, 2), str(x), fill=(255, 255, 0), font=grid_font)
        for y in range(((y0 + 10 - 1) // 10) * 10, y1 + 1, 10):
            ly = (y - y0) * scale
            draw.line([(0, ly), (region.width, ly)], fill=(90, 90, 90), width=1)
            if y % 20 == 0:
                draw.text((2, ly + 2), str(y), fill=(0, 255, 170), font=grid_font)
    label_font = font(13)
    for key, value in MANUAL_TRACE.items():
        pts = [((x - x0) * scale, (y - y0) * scale) for x, y in value["points"]]
        if all((-40 <= x <= region.width + 40 and -40 <= y <= region.height + 40) for x, y in pts):
            color = COLORS[key]
            if value["trace_type"] == "closed_polygon":
                draw.line(pts + [pts[0]], fill=color, width=max(2, scale))
                for point in pts:
                    r = max(3, scale)
                    draw.ellipse([point[0] - r, point[1] - r, point[0] + r, point[1] + r], outline=color, width=2)
            else:
                draw.line(pts, fill=color, width=max(2, scale))
                for point in pts:
                    r = max(3, scale)
                    draw.rectangle([point[0] - r, point[1] - r, point[0] + r, point[1] + r], outline=color, width=2)
            draw.text((pts[0][0] + 5, pts[0][1] + 5), key.replace("viewer_", "").replace("_", " "), fill=color, font=label_font)
    return region


def canny_trace(source: Image.Image, crop: tuple[int, int, int, int], scale: int) -> Image.Image:
    arr = np.array(source.crop(crop).convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    gray = cv2.equalizeHist(gray)
    edges = cv2.Canny(gray, 45, 120)
    edge_rgb = arr.copy()
    edge_rgb[edges > 0] = [0, 255, 0]
    return draw_trace(Image.fromarray(edge_rgb), (0, 0, crop[2] - crop[0], crop[3] - crop[1]), scale, False)


def label_tile(image: Image.Image, label: str) -> Image.Image:
    tile = Image.new("RGB", (image.width, image.height + 34), (16, 16, 16))
    tile.paste(image.convert("RGB"), (0, 34))
    ImageDraw.Draw(tile).text((8, 9), label, fill=(245, 245, 245), font=font(16))
    return tile


def make_panel(source: Image.Image, panel_path: Path) -> None:
    tiles = [
        label_tile(draw_trace(source, FACE_CROP, 3, True), "manual trace v1 over high-zoom source with 10px grid"),
        label_tile(draw_trace(source, LEFT_EYE_CROP, 5, True), "viewer-left eye/brow/hair occlusion trace crop"),
        label_tile(draw_trace(source, RIGHT_EYE_CROP, 5, True), "viewer-right eye/brow trace crop"),
    ]
    width = max(tile.width for tile in tiles)
    height = sum(tile.height for tile in tiles)
    panel = Image.new("RGB", (width, height), (0, 0, 0))
    y = 0
    for tile in tiles:
        panel.paste(tile, (0, y))
        y += tile.height
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(panel_path)


def main() -> int:
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    trace_path = RUNTIME_DIR / "wave70_eye_boundary_manual_trace_v1.json"
    panel_path = RUNTIME_DIR / "wave70_eye_boundary_manual_trace_v1_panel.png"
    make_panel(source, panel_path)

    trace_payload = {
        "schema_version": "1.0",
        "created_local": RUN_STAMP,
        "source_image": rel(SOURCE_IMAGE),
        "source_sha256": sha256_file(SOURCE_IMAGE),
        "coordinate_system": "absolute source-image pixels, origin upper-left, image size 768x768",
        "trace_method": "manual high-zoom visual trace from source image and Canny-assisted diagnostic panels",
        "promotion_boundary": "boundary_trace_only_not_a_mask_not_row_promotion",
        "manual_trace": to_jsonable_trace(),
    }
    write_json(trace_path, trace_payload)

    evidence_payload = {
        "schema_version": "1.0",
        "evidence_id": f"W70_EYE_BOUNDARY_MANUAL_TRACE_V1_{RUN_STAMP}",
        "created_local": RUN_STAMP,
        "task": "Wave70 eye-family high-zoom manual boundary trace v1 after user dispute",
        "source_image": rel(SOURCE_IMAGE),
        "source_sha256": sha256_file(SOURCE_IMAGE),
        "result": "manual_trace_v1_created_boundary_evidence_only_not_promoted",
        "promotion_decision": "no_eye_family_mask_promoted_no_W70_MASK_PROMOTION_ROW_GATE_PASS_TRUE",
        "affected_mask_type_ids": [
            "mf70_left_eye",
            "mf70_right_eye",
            "mf70_pupils_iris_sclera",
            "mf70_eyelids",
            "mf70_eyelashes",
            "mf70_eyebrows",
        ],
        "artifacts": {
            "manual_trace_json": rel(trace_path),
            "manual_trace_panel": rel(panel_path),
        },
        "trace_summary": {
            "viewer_left": "eye/brow are represented as smaller visible regions with an explicit hair-occlusion boundary; no extension into hair mass",
            "viewer_right": "eye/brow are represented as unobstructed visible aperture and brow hair boundaries",
        },
        "next_step": "Use this boundary trace to derive candidate masks only after another high-zoom panel review; keep rows blocked until exact row-level hard-gate evidence exists.",
        "forbidden": "Do not treat this trace as mask acceptance, generated-output proof, target-runtime proof, or certification.",
    }
    write_json(QA_EVIDENCE, evidence_payload)
    shutil.copy2(QA_EVIDENCE, TRACKER_EVIDENCE)
    print(json.dumps({"evidence": str(QA_EVIDENCE), "tracker_evidence": str(TRACKER_EVIDENCE), "panel": str(panel_path), "trace": str(trace_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
