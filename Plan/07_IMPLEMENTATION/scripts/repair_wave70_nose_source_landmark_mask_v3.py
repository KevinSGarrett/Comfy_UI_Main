#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
RUN_STAMP = "20260707T225500-0500"
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
OUT_DIR = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    f"wave70_mf70_nose_source_landmark_v3_{RUN_STAMP}"
)
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_mf70_nose/source_landmark_repair_v3" / RUN_STAMP
COMFYUI_INPUT = PROJECT_ROOT / "ComfyUI/input/wave70_mf70_nose_mask.png"
QA_EVIDENCE = PROJECT_ROOT / (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    f"W70_MF70_NOSE_SOURCE_LANDMARK_REPAIR_V3_{RUN_STAMP}.json"
)
TRACKER_EVIDENCE = PROJECT_ROOT / (
    "Plan/Tracker/Evidence/"
    f"W70_MF70_NOSE_SOURCE_LANDMARK_REPAIR_V3_{RUN_STAMP}.json"
)


ALLOWED_BBOX = [330, 270, 455, 430]
PROTECTED_ZONES = {
    "viewer_left_eye_aperture": [245, 306, 333, 337],
    "viewer_right_eye_aperture": [420, 306, 515, 337],
    "mouth_lips": [290, 430, 455, 488],
    "upper_lip_philtrum": [315, 418, 430, 458],
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


def draw_scaled_polygon(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], scale: int, fill: int) -> None:
    draw.polygon([(x * scale, y * scale) for x, y in points], fill=fill)


def create_mask(size: tuple[int, int]) -> Image.Image:
    scale = 4
    hi = Image.new("L", (size[0] * scale, size[1] * scale), 0)
    draw = ImageDraw.Draw(hi)

    # Bridge and sidewall taper, kept inside the visible central nose planes.
    bridge = [
        (368, 298),
        (395, 298),
        (402, 334),
        (404, 358),
        (395, 373),
        (372, 373),
        (362, 358),
        (363, 334),
    ]
    draw_scaled_polygon(draw, bridge, scale, 255)

    # Tip, alae, and nostril base. Bottom is intentionally above philtrum/lip guardrail.
    lower = [
        (356, 365),
        (370, 352),
        (397, 353),
        (415, 369),
        (422, 390),
        (411, 404),
        (389, 409),
        (361, 405),
        (346, 392),
        (348, 376),
    ]
    draw_scaled_polygon(draw, lower, scale, 255)

    # Small nostril/ala lobes so the mask follows the source nose rather than a triangle.
    draw.ellipse([344 * scale, 382 * scale, 372 * scale, 408 * scale], fill=255)
    draw.ellipse([394 * scale, 382 * scale, 422 * scale, 408 * scale], fill=255)

    # Carve protected neighbors with a few pixels of slack.
    protected = ImageDraw.Draw(hi)
    carve_rects = [
        (245, 304, 335, 339),  # viewer-left eye aperture
        (418, 304, 517, 339),  # viewer-right eye aperture
        (288, 428, 457, 490),  # lips/mouth
        (313, 410, 432, 460),  # philtrum/upper-lip skin
    ]
    for left, top, right, bottom in carve_rects:
        protected.rectangle([left * scale, top * scale, right * scale, bottom * scale], fill=0)

    return hi.resize(size, Image.Resampling.LANCZOS).point(lambda value: 255 if value > 24 else 0)


def make_overlay(source: Image.Image, mask: Image.Image) -> Image.Image:
    rgba = source.convert("RGBA")
    fill = Image.new("RGBA", source.size, (255, 0, 0, 0))
    fill.putalpha(mask.point(lambda value: 128 if value > 8 else 0))
    return Image.alpha_composite(rgba, fill).convert("RGB")


def draw_boundary_overlay(source: Image.Image, mask: Image.Image) -> Image.Image:
    out = make_overlay(source, mask)
    draw = ImageDraw.Draw(out)
    draw.rectangle(ALLOWED_BBOX, outline=(0, 255, 0), width=4)
    for zone in PROTECTED_ZONES.values():
        draw.rectangle(zone, outline=(255, 200, 0), width=3)
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


def make_panel(source: Image.Image, mask: Image.Image, panel_path: Path) -> None:
    crop = (255, 210, 520, 475)
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

    mask_path = OUT_DIR / "wave70_mf70_nose_mask.png"
    overlay_path = OUT_DIR / "wave70_mf70_nose_overlay.png"
    panel_path = RUNTIME_DIR / "mf70_nose_v3_source_landmark_panel.png"
    manifest_path = RUNTIME_DIR / "mf70_nose_v3_source_landmarks.json"

    mask.save(mask_path)
    make_overlay(source, mask).save(overlay_path)
    make_panel(source, mask, panel_path)
    shutil.copy2(mask_path, COMFYUI_INPUT)

    total = count_nonzero(mask)
    allowed = count_rect(mask, ALLOWED_BBOX)
    protected_hits = {name: count_rect(mask, rect) for name, rect in PROTECTED_ZONES.items()}
    protected_hits = {name: value for name, value in protected_hits.items() if value}
    coverage_percent = round(total / (source.width * source.height) * 100, 4)

    payload = {
        "schema_version": "1.0",
        "evidence_id": f"W70_MF70_NOSE_SOURCE_LANDMARK_REPAIR_V3_{RUN_STAMP}",
        "timestamp_local": RUN_STAMP,
        "mask_type_id": "mf70_nose",
        "tracker_id": "TRK-W70-0017",
        "item_id": "ITEM-W70-0017",
        "project_root": str(PROJECT_ROOT),
        "source_image": rel(SOURCE_IMAGE),
        "source_sha256": sha256_file(SOURCE_IMAGE),
        "target_definition": "visible nose bridge, sidewalls, tip, alae, and nostril base; excludes philtrum, lips, mouth, eye apertures, and cheek skin",
        "status": "repair_evidence_only_not_promoted",
        "result": "mf70_nose_v3_source_landmark_repair_created_pending_source_alignment_validation",
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
        "protected_zones": PROTECTED_ZONES,
        "mask_pixels": total,
        "allowed_bbox_pixels": allowed,
        "outside_allowed_pixels": max(0, total - allowed),
        "coverage_percent": coverage_percent,
        "protected_zone_hits": protected_hits,
        "geometry_notes": [
            "Bottom boundary is kept above philtrum/upper-lip guardrail.",
            "Eye aperture guardrails are separated left/right so the nose bridge is not falsely blocked by a cross-face eye rectangle.",
            "Mask follows the visible bridge-to-tip taper and alae/nostril base instead of a broad triangle.",
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
