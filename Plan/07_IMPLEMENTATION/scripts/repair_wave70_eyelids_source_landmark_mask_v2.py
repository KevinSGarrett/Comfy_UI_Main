#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
RUN_STAMP = "20260707T235500-0500"
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
OUT_DIR = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    f"wave70_mf70_eyelids_source_landmark_v2_{RUN_STAMP}"
)
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_mf70_eyelids/source_landmark_repair_v2" / RUN_STAMP
COMFYUI_INPUT = PROJECT_ROOT / "ComfyUI/input/wave70_mf70_eyelids_mask.png"
QA_EVIDENCE = PROJECT_ROOT / (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    f"W70_MF70_EYELIDS_SOURCE_LANDMARK_REPAIR_V2_{RUN_STAMP}.json"
)
TRACKER_EVIDENCE = PROJECT_ROOT / (
    "Plan/Tracker/Evidence/"
    f"W70_MF70_EYELIDS_SOURCE_LANDMARK_REPAIR_V2_{RUN_STAMP}.json"
)


ALLOWED_BBOX = [245, 292, 515, 350]
BOUNDARY_POLYGONS = {
    "allowed_eyelid_bands": [
        [(276, 305), (303, 305), (326, 311), (321, 316), (286, 313), (276, 311)],
        [(276, 337), (287, 344), (316, 341), (326, 336), (321, 348), (286, 351), (276, 344)],
        [(426, 305), (454, 303), (485, 304), (508, 311), (501, 316), (464, 313), (429, 315)],
        [(428, 337), (459, 345), (490, 342), (506, 336), (500, 348), (462, 351), (429, 344)],
    ],
    "viewer_left_eye_aperture": [
        [(247, 318), (261, 309), (292, 308), (322, 316), (328, 324), (313, 335), (281, 335), (257, 329)],
    ],
    "viewer_right_eye_aperture": [
        [(424, 318), (449, 309), (483, 309), (505, 316), (511, 324), (491, 335), (456, 335), (429, 329)],
    ],
    "viewer_left_brow": [
        [(213, 286), (247, 274), (310, 275), (337, 289), (323, 298), (267, 292), (222, 299)],
    ],
    "viewer_right_brow": [
        [(406, 284), (454, 272), (515, 278), (548, 294), (529, 302), (465, 293), (416, 296)],
    ],
    "viewer_left_hair_occlusion": [
        [(190, 252), (236, 264), (268, 297), (279, 342), (254, 374), (208, 379), (178, 340), (170, 286)],
    ],
    "nose_bridge": [
        [(346, 284), (410, 284), (424, 430), (338, 430)],
    ],
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


def count_nonzero(mask: Image.Image) -> int:
    return sum(1 for value in mask.getdata() if value > 0)


def scale_points(points: list[tuple[int, int]], scale: int) -> list[tuple[int, int]]:
    return [(x * scale, y * scale) for x, y in points]


def create_mask(size: tuple[int, int]) -> Image.Image:
    scale = 4
    hi = Image.new("L", (size[0] * scale, size[1] * scale), 0)
    draw = ImageDraw.Draw(hi)

    # Viewer-left eye, partly hair-shadowed. Bands hug lid folds and avoid eye aperture.
    polygons = [
        # viewer-left upper lid
        [(282, 309), (304, 306), (324, 311), (319, 314), (288, 313), (282, 312)],
        # viewer-left lower lid
        [(282, 341), (309, 342), (323, 337), (319, 344), (289, 350), (282, 346)],
        # viewer-right upper lid
        [(428, 309), (452, 306), (483, 306), (504, 311), (499, 314), (464, 313), (430, 314)],
        # viewer-right lower lid
        [(430, 341), (459, 345), (488, 342), (502, 337), (498, 344), (462, 350), (430, 346)],
    ]
    for polygon in polygons:
        draw.polygon(scale_points(polygon, scale), fill=255)

    # Carve protected source-shaped eye apertures and hair occlusion exactly.
    for name in ("viewer_left_eye_aperture", "viewer_right_eye_aperture", "viewer_left_hair_occlusion", "nose_bridge"):
        for polygon in BOUNDARY_POLYGONS[name]:
            draw.polygon(scale_points(polygon, scale), fill=0)

    # Keep a thin safety carve below brows without using a broad visual-review box.
    draw.rectangle([215 * scale, 270 * scale, 542 * scale, 304 * scale], fill=0)

    return hi.resize(size, Image.Resampling.LANCZOS).point(lambda value: 255 if value > 24 else 0)


def make_overlay(source: Image.Image, mask: Image.Image) -> Image.Image:
    rgba = source.convert("RGBA")
    fill = Image.new("RGBA", source.size, (255, 0, 0, 0))
    fill.putalpha(mask.point(lambda value: 128 if value > 8 else 0))
    return Image.alpha_composite(rgba, fill).convert("RGB")


def draw_boundary_overlay(source: Image.Image, mask: Image.Image) -> Image.Image:
    out = make_overlay(source, mask)
    draw = ImageDraw.Draw(out)
    for polygon in BOUNDARY_POLYGONS["allowed_eyelid_bands"]:
        draw.line(polygon + [polygon[0]], fill=(0, 255, 0), width=4)
    for name, polygons in BOUNDARY_POLYGONS.items():
        if name == "allowed_eyelid_bands":
            continue
        for polygon in polygons:
            draw.line(polygon + [polygon[0]], fill=(255, 200, 0), width=3)
    return out


def label_tile(image: Image.Image, label: str, size: int = 360) -> Image.Image:
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    tile = Image.new("RGB", (size, size + 34), (18, 18, 18))
    tile.paste(image.convert("RGB").resize((size, size), Image.Resampling.LANCZOS), (0, 34))
    draw = ImageDraw.Draw(tile)
    draw.text((8, 9), label, fill=(245, 245, 245), font=font)
    return tile


def count_rect(mask: Image.Image, rect: list[int]) -> int:
    return count_nonzero(mask.crop(tuple(rect)))


def count_polygon_zone(mask: Image.Image, polygons: list[list[tuple[int, int]]]) -> int:
    zone = Image.new("L", mask.size, 0)
    draw = ImageDraw.Draw(zone)
    for polygon in polygons:
        draw.polygon(polygon, fill=255)
    return count_nonzero(Image.composite(mask, Image.new("L", mask.size, 0), zone))


def make_panel(source: Image.Image, mask: Image.Image, panel_path: Path) -> None:
    crop = (210, 245, 540, 385)
    mask_rgb = Image.merge("RGB", (mask, mask, mask))
    tiles = [
        label_tile(source.crop(crop), "source crop"),
        label_tile(mask_rgb.crop(crop), "mask only"),
        label_tile(make_overlay(source, mask).crop(crop), "source + mask"),
        label_tile(draw_boundary_overlay(source, mask).crop(crop), "green allowed / amber protected"),
    ]
    panel = Image.new("RGB", (len(tiles) * tiles[0].width, tiles[0].height), (0, 0, 0))
    for index, tile in enumerate(tiles):
        panel.paste(tile, (index * tile.width, 0))
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(panel_path)


def main() -> int:
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    mask = create_mask(source.size)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    mask_path = OUT_DIR / "wave70_mf70_eyelids_mask.png"
    overlay_path = OUT_DIR / "wave70_mf70_eyelids_overlay.png"
    panel_path = RUNTIME_DIR / "mf70_eyelids_v2_source_landmark_panel.png"
    manifest_path = RUNTIME_DIR / "mf70_eyelids_v2_source_landmarks.json"

    mask.save(mask_path)
    make_overlay(source, mask).save(overlay_path)
    make_panel(source, mask, panel_path)
    shutil.copy2(mask_path, COMFYUI_INPUT)

    total = count_nonzero(mask)
    allowed = count_rect(mask, ALLOWED_BBOX)
    protected_hits = {
        name: count_polygon_zone(mask, polygons)
        for name, polygons in BOUNDARY_POLYGONS.items()
        if name != "allowed_eyelid_bands"
    }
    protected_hits = {name: value for name, value in protected_hits.items() if value}
    coverage_percent = round(total / (source.width * source.height) * 100, 4)

    payload = {
        "schema_version": "1.0",
        "evidence_id": f"W70_MF70_EYELIDS_SOURCE_LANDMARK_REPAIR_V2_{RUN_STAMP}",
        "timestamp_local": RUN_STAMP,
        "mask_type_id": "mf70_eyelids",
        "tracker_id": "TRK-W70-0013",
        "item_id": "ITEM-W70-0013",
        "project_root": str(PROJECT_ROOT),
        "source_image": rel(SOURCE_IMAGE),
        "source_sha256": sha256_file(SOURCE_IMAGE),
        "target_definition": "thin upper and lower eyelid bands following visible lid folds; excludes eye apertures, brows, nose bridge, broad orbital skin, lashes, and cheeks",
        "status": "repair_evidence_only_not_promoted",
        "result": "mf70_eyelids_v2_source_landmark_repair_created_pending_source_alignment_validation",
        "promotion_decision": "blocked_no_wave70_mask_promotion_row_gate_pass_true",
        "mask": rel(mask_path),
        "mask_sha256": sha256_file(mask_path),
        "active_comfyui_input_copy": rel(COMFYUI_INPUT),
        "active_comfyui_input_sha256": sha256_file(COMFYUI_INPUT),
        "overlay": rel(overlay_path),
        "overlay_sha256": sha256_file(overlay_path),
        "panel": rel(panel_path),
        "panel_sha256": sha256_file(panel_path),
        "landmark_manifest": rel(manifest_path),
        "allowed_bbox": ALLOWED_BBOX,
        "boundary_polygons": BOUNDARY_POLYGONS,
        "mask_pixels": total,
        "allowed_bbox_pixels": allowed,
        "outside_allowed_pixels": max(0, total - allowed),
        "coverage_percent": coverage_percent,
        "protected_zone_hits": protected_hits,
        "geometry_notes": [
            "Old chunky orbital patches are replaced with four narrow upper/lower lid bands.",
            "Eye aperture cores are carved out after drawing, so iris/sclera/pupil regions are protected.",
            "Brow band and nose bridge guardrails are carved to prevent broad orbital or bridge coverage.",
        ],
        "generated_output_executed": False,
        "target_runtime_proof_present": False,
        "reference_image_matrix_pass": False,
        "completion_allowed": False,
    }
    write_json(manifest_path, payload)
    write_json(QA_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)
    print(QA_EVIDENCE)
    print(TRACKER_EVIDENCE)
    print(panel_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
