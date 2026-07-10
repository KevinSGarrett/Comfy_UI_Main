#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
V2_EVIDENCE = PROJECT_ROOT / (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_MF70_EYES_FULL_SOURCE_LANDMARK_REPAIR_V2_20260709T215300-0500.json"
)
GOLD_EVIDENCE = PROJECT_ROOT / (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_MASKED_WAREHOUSE_FACIAL_GOLD_STANDARD_INTAKE_20260709T221608-0500.json"
)
OUT_DIR_BASE = PROJECT_ROOT / "Plan/Instructions/Operations/Prepared_Input_Assets"
QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_BASE = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_mf70_eyes_full_source_landmark_v3"

# Tighter active-source eye-aperture traces. These are candidate pixels only.
# They intentionally avoid brow bands, eyelid skin slabs, and the viewer-left hair edge.
EYE_POLYGONS_V3 = {
    "viewer_left_visible_eye_aperture": [
        (292, 331),
        (300, 325),
        (314, 323),
        (327, 326),
        (335, 332),
        (326, 337),
        (311, 338),
        (298, 335),
    ],
    "viewer_right_visible_eye_aperture": [
        (400, 330),
        (409, 324),
        (426, 321),
        (443, 324),
        (455, 331),
        (446, 338),
        (427, 340),
        (410, 337),
    ],
}


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def draw_antialiased_mask(size: tuple[int, int], polygons: dict[str, list[tuple[int, int]]]) -> Image.Image:
    scale = 4
    mask = Image.new("L", (size[0] * scale, size[1] * scale), 0)
    draw = ImageDraw.Draw(mask)
    for polygon in polygons.values():
        draw.polygon([(x * scale, y * scale) for x, y in polygon], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=0.65 * scale))
    return mask.resize(size, Image.Resampling.LANCZOS)


def threshold(mask: Image.Image) -> Image.Image:
    return mask.point(lambda value: 255 if value > 18 else 0)


def stats(mask: Image.Image) -> dict[str, Any]:
    hard = threshold(mask)
    bbox = hard.getbbox()
    pixels = sum(hard.histogram()[1:])
    area = hard.width * hard.height
    return {
        "bbox": list(bbox) if bbox else None,
        "image_size": [hard.width, hard.height],
        "nonzero_pixels": pixels,
        "nonzero_ratio": round(pixels / area, 6) if area else 0,
    }


def component_stats(mask: Image.Image) -> dict[str, dict[str, Any]]:
    hard = threshold(mask)
    components = {}
    for name, box in {
        "viewer_left": (240, 285, 360, 370),
        "viewer_right": (370, 285, 490, 370),
    }.items():
        crop = hard.crop(box)
        bbox = crop.getbbox()
        pixels = sum(crop.histogram()[1:])
        if bbox:
            global_bbox = [bbox[0] + box[0], bbox[1] + box[1], bbox[2] + box[0], bbox[3] + box[1]]
        else:
            global_bbox = None
        components[name] = {"bbox": global_bbox, "nonzero_pixels": pixels}
    return components


def overlay(source: Image.Image, mask: Image.Image, fill_color: tuple[int, int, int]) -> Image.Image:
    rgba = source.convert("RGBA")
    fill = Image.new("RGBA", source.size, (*fill_color, 0))
    fill.putalpha(mask.point(lambda value: min(145, int(value * 0.55))))
    edge = threshold(mask).filter(ImageFilter.FIND_EDGES).point(lambda value: 255 if value > 12 else 0)
    outline = Image.new("RGBA", source.size, (255, 255, 0, 0))
    outline.putalpha(edge)
    return Image.alpha_composite(Image.alpha_composite(rgba, fill), outline).convert("RGB")


def tile(image: Image.Image, title: str, note: str = "", size: tuple[int, int] = (320, 210)) -> Image.Image:
    header = 44
    canvas = Image.new("RGB", (size[0], size[1] + header), (18, 18, 18))
    image = image.convert("RGB")
    image.thumbnail(size)
    canvas.paste(image, ((size[0] - image.width) // 2, header + (size[1] - image.height) // 2))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 6), title, fill=(245, 245, 245), font=font(16))
    if note:
        draw.text((8, 25), note, fill=(190, 190, 190), font=font(12))
    return canvas


def mask_color(mask: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    bg = Image.new("RGB", mask.size, "black")
    fg = Image.new("RGB", mask.size, color)
    return Image.composite(fg, bg, threshold(mask))


def source_crop(image: Image.Image) -> Image.Image:
    return image.crop((245, 285, 490, 375))


def part_from_celeba(path: Path) -> str:
    return path.stem.split("_", 1)[1]


def make_panel(
    source: Image.Image,
    v2_mask: Image.Image,
    v3_mask: Image.Image,
    v2_overlay: Image.Image,
    v3_overlay: Image.Image,
    gold: dict[str, Any],
    panel_path: Path,
) -> None:
    celeba_sample = gold["datasets"]["CelebAMask-HQ"]["selected_sample"]
    masks = {part_from_celeba(Path(path)): Path(path) for path in celeba_sample["masks"]}
    diff_removed = ImageChops.subtract(threshold(v2_mask), threshold(v3_mask))
    diff_added = ImageChops.subtract(threshold(v3_mask), threshold(v2_mask))
    diff_rgb = Image.new("RGB", v2_mask.size, "black")
    diff_rgb = Image.composite(Image.new("RGB", v2_mask.size, (255, 60, 60)), diff_rgb, diff_removed)
    diff_rgb = Image.composite(Image.new("RGB", v2_mask.size, (60, 220, 80)), diff_rgb, diff_added)

    cells = [
        tile(source_crop(source), "source eye crop", "active MOD-17 source"),
        tile(source_crop(v2_overlay), "v2 overlay", "candidate only"),
        tile(source_crop(v3_overlay), "v3 overlay", "tighter aperture-only"),
        tile(source_crop(mask_color(v3_mask, (255, 220, 0))), "v3 mask only", "yellow = eyes_full"),
        tile(source_crop(diff_rgb), "v2 to v3 delta", "red removed, green added"),
        tile(Image.open(masks["l_eye"]).convert("L"), "gold left eye", "CelebAMask aperture"),
        tile(Image.open(masks["r_eye"]).convert("L"), "gold right eye", "CelebAMask aperture"),
        tile(Image.open(masks["l_brow"]).convert("L"), "gold left brow", "separate neighbor"),
        tile(Image.open(masks["r_brow"]).convert("L"), "gold right brow", "separate neighbor"),
    ]
    cols = 3
    cell_w = max(cell.width for cell in cells)
    cell_h = max(cell.height for cell in cells)
    rows = (len(cells) + cols - 1) // cols
    panel = Image.new("RGB", (cols * cell_w, rows * cell_h), "black")
    for idx, cell in enumerate(cells):
        panel.paste(cell, ((idx % cols) * cell_w, (idx // cols) * cell_h))
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(panel_path)


def main() -> int:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S-0500")
    run_id = f"W70_MF70_EYES_FULL_SOURCE_LANDMARK_REPAIR_V3_{timestamp}"
    out_dir = OUT_DIR_BASE / f"wave70_mf70_eyes_full_source_landmark_v3_{timestamp}"
    runtime_dir = RUNTIME_BASE / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)

    source = Image.open(SOURCE_IMAGE).convert("RGB")
    v2 = load_json(V2_EVIDENCE)
    gold = load_json(GOLD_EVIDENCE)
    v2_mask = Image.open(PROJECT_ROOT / v2["artifacts"]["mask"]).convert("L")
    v3_mask = draw_antialiased_mask(source.size, EYE_POLYGONS_V3)
    v2_overlay = overlay(source, v2_mask, (0, 220, 255))
    v3_overlay = overlay(source, v3_mask, (0, 220, 255))

    mask_path = out_dir / "wave70_mf70_eyes_full_source_landmark_v3_mask.png"
    overlay_path = out_dir / "wave70_mf70_eyes_full_source_landmark_v3_overlay.png"
    panel_path = runtime_dir / "wave70_mf70_eyes_full_source_landmark_v3_review_panel.png"
    coordinates_path = out_dir / "wave70_mf70_eyes_full_source_landmark_v3_coordinates.json"

    v3_mask.save(mask_path)
    v3_overlay.save(overlay_path)
    make_panel(source, v2_mask, v3_mask, v2_overlay, v3_overlay, gold, panel_path)

    v2_stats = stats(v2_mask)
    v3_stats = stats(v3_mask)
    coordinate_manifest = {
        "schema_version": "1.0",
        "mask_type_id": "mf70_eyes_full",
        "coordinate_space": "active_source_image_pixels_768x768",
        "source_image": rel(SOURCE_IMAGE),
        "eye_polygons": EYE_POLYGONS_V3,
        "candidate_only": True,
        "promotion_allowed": False,
        "gold_reference_rule": "eyes_full should cover visible eye apertures only; eyebrows and hair are protected neighbor regions",
    }
    write_json(coordinates_path, coordinate_manifest)

    removed_pixels = sum(ImageChops.subtract(threshold(v2_mask), threshold(v3_mask)).histogram()[1:])
    added_pixels = sum(ImageChops.subtract(threshold(v3_mask), threshold(v2_mask)).histogram()[1:])
    payload = {
        "schema_version": "1.0",
        "evidence_id": run_id,
        "created_local": timestamp,
        "task": "Create a tighter gold-reference-backed mf70_eyes_full v3 candidate after v2 remained candidate-only.",
        "supersedes_candidate": rel(V2_EVIDENCE),
        "implementation_script": rel(Path(__file__).resolve()),
        "implementation_script_sha256": sha256_file(Path(__file__).resolve()),
        "local_only": True,
        "aws_contacted": False,
        "github_api_contacted": False,
        "civitai_contacted": False,
        "comfyui_contacted": False,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "source_image": rel(SOURCE_IMAGE),
        "source_sha256": sha256_file(SOURCE_IMAGE),
        "artifacts": {
            "mask": rel(mask_path),
            "mask_sha256": sha256_file(mask_path),
            "overlay": rel(overlay_path),
            "overlay_sha256": sha256_file(overlay_path),
            "review_panel": rel(panel_path),
            "review_panel_sha256": sha256_file(panel_path),
            "coordinate_manifest": rel(coordinates_path),
            "coordinate_manifest_sha256": sha256_file(coordinates_path),
        },
        "v2_stats": v2_stats,
        "v3_stats": v3_stats,
        "v3_component_stats": component_stats(v3_mask),
        "v2_to_v3_delta": {
            "removed_pixels": removed_pixels,
            "added_pixels": added_pixels,
            "net_pixel_change": v3_stats["nonzero_pixels"] - v2_stats["nonzero_pixels"],
            "area_change_ratio": round(
                (v3_stats["nonzero_pixels"] - v2_stats["nonzero_pixels"]) / v2_stats["nonzero_pixels"], 6
            )
            if v2_stats["nonzero_pixels"]
            else None,
        },
        "gold_standard_inputs": {
            "intake_evidence": rel(GOLD_EVIDENCE),
            "rule_applied": "eye masks must be small visible aperture masks separate from brow, eyelid-skin, and hair regions",
        },
        "strict_visual_findings": [
            "V3 reduces the viewer-left eye mask away from the hair edge and upper-lid skin compared with v2.",
            "V3 keeps both eyes as small filled aperture regions rather than rectangular or brow-inclusive masks.",
            "V3 still remains candidate-only because this is one source-anchor repair, not matrix-wide proof.",
            "No active ComfyUI input mask was overwritten and no generated-output proof was run.",
        ],
        "qa_decision": "candidate_created_pending_strict_visual_review_and_reference_matrix_validation",
        "promotion_decision": "not_promoted_no_active_input_changed_no_W70_MASK_PROMOTION_ROW_GATE_PASS_TRUE",
        "next_required_action": (
            "Review the v3 panel at high zoom; if visually accepted, run the focused Wave70 geometry/promotion "
            "lockdown checks and then one bounded local generated-output proof."
        ),
    }

    evidence_path = QA_DIR / f"{run_id}.json"
    tracker_path = TRACKER_DIR / f"{run_id}.json"
    write_json(evidence_path, payload)
    write_json(tracker_path, payload)
    print(
        json.dumps(
            {
                "qa_evidence": rel(evidence_path),
                "tracker_evidence": rel(tracker_path),
                "panel": rel(panel_path),
                "mask": rel(mask_path),
                "v2_to_v3_delta": payload["v2_to_v3_delta"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
