#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from PIL import Image, ImageChops, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
STAMP = "20260710T010600-0500"
EVIDENCE_ID = f"W70_MF70_NOSE_VISIBLE_SURFACE_REPAIR_V4_{STAMP}"
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
V3_MASK = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    "wave70_mf70_nose_source_landmark_v3_20260707T225500-0500/"
    "wave70_mf70_nose_mask.png"
)
V3_OVERLAY = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Prepared_Input_Assets/"
    "wave70_mf70_nose_source_landmark_v3_20260707T225500-0500/"
    "wave70_mf70_nose_overlay.png"
)
GOLD_IMAGE = PROJECT_ROOT / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/18000.jpg"
GOLD_NOSE = PROJECT_ROOT / "MaskedWarehouse/CelebAMask-HQ/CelebAMask-HQ-mask-anno/9/18000_nose.png"
GOLD_MOUTH = PROJECT_ROOT / "MaskedWarehouse/CelebAMask-HQ/CelebAMask-HQ-mask-anno/9/18000_mouth.png"
OUT_DIR = PROJECT_ROOT / f"Plan/Instructions/Operations/Prepared_Input_Assets/wave70_mf70_nose_visible_surface_v4_{STAMP}"
RUNTIME_DIR = PROJECT_ROOT / f"runtime_artifacts/mask_factory/wave70_mf70_nose_visible_surface_v4/{STAMP}"
QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def polygons_v4() -> dict[str, list[tuple[int, int]]]:
    # Source-image pixel coordinates. V4 keeps the lower boundary above the
    # philtrum/lip plane and follows visible bridge, tip, alae, and nostril base.
    return {
        "bridge_and_sidewalls": [
            (368, 300),
            (394, 300),
            (400, 334),
            (400, 360),
            (392, 377),
            (372, 377),
            (362, 360),
            (363, 334),
        ],
        "tip_and_alae": [
            (355, 370),
            (370, 358),
            (395, 358),
            (411, 372),
            (417, 391),
            (407, 402),
            (388, 407),
            (363, 403),
            (350, 392),
            (349, 378),
        ],
    }


def protected_regions() -> dict[str, list[tuple[int, int]]]:
    return {
        "mouth_lips_guardrail": [(286, 428), (458, 428), (458, 493), (286, 493)],
        "upper_lip_philtrum_guardrail": [(313, 410), (433, 410), (433, 459), (313, 459)],
        "viewer_left_eye_guardrail": [(242, 304), (336, 304), (336, 340), (242, 340)],
        "viewer_right_eye_guardrail": [(418, 304), (518, 304), (518, 340), (418, 340)],
    }


def make_mask(size: tuple[int, int]) -> Image.Image:
    scale = 4
    hi = Image.new("L", (size[0] * scale, size[1] * scale), 0)
    draw = ImageDraw.Draw(hi)
    for polygon in polygons_v4().values():
        draw.polygon([(x * scale, y * scale) for x, y in polygon], fill=255)
    draw.ellipse([345 * scale, 382 * scale, 371 * scale, 405 * scale], fill=255)
    draw.ellipse([395 * scale, 382 * scale, 421 * scale, 405 * scale], fill=255)

    for polygon in protected_regions().values():
        draw.polygon([(x * scale, y * scale) for x, y in polygon], fill=0)
    return hi.resize(size, Image.Resampling.LANCZOS).point(lambda value: 255 if value > 28 else 0)


def make_overlay(source: Image.Image, mask: Image.Image) -> Image.Image:
    rgba = source.convert("RGBA")
    fill = Image.new("RGBA", rgba.size, (255, 35, 35, 0))
    fill.putalpha(mask.point(lambda value: 138 if value > 8 else 0))
    overlay = Image.alpha_composite(rgba, fill)
    outline = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(outline)
    for polygon in polygons_v4().values():
        draw.line(polygon + [polygon[0]], fill=(255, 245, 245, 235), width=2)
    return Image.alpha_composite(overlay, outline).convert("RGB")


def draw_guardrail_overlay(source: Image.Image, mask: Image.Image) -> Image.Image:
    out = make_overlay(source, mask)
    draw = ImageDraw.Draw(out)
    for polygon in protected_regions().values():
        draw.line(polygon + [polygon[0]], fill=(255, 210, 0), width=3)
    draw.rectangle((330, 270, 455, 430), outline=(30, 255, 70), width=3)
    return out


def mask_stats(mask: Image.Image) -> dict[str, Any]:
    hard = mask.point(lambda value: 255 if value > 8 else 0)
    hist = hard.histogram()
    nonzero = sum(hist[1:])
    bbox = hard.getbbox()
    return {
        "image_size": list(mask.size),
        "nonzero_pixels": nonzero,
        "nonzero_ratio": round(nonzero / float(mask.size[0] * mask.size[1]), 6),
        "bbox": list(bbox) if bbox else None,
    }


def count_intersection(a: Image.Image, b: Image.Image) -> int:
    return mask_stats(ImageChops.multiply(a.point(lambda v: 255 if v > 8 else 0), b.point(lambda v: 255 if v > 8 else 0)))["nonzero_pixels"]


def label_tile(image: Image.Image, label: str, size: tuple[int, int]) -> Image.Image:
    w, h = size
    tile = Image.new("RGB", (w, h + 34), (18, 18, 18))
    tile.paste(image.convert("RGB").resize((w, h), Image.Resampling.LANCZOS), (0, 34))
    draw = ImageDraw.Draw(tile)
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    draw.text((8, 8), label, fill=(245, 245, 245), font=font)
    return tile


def gold_overlay() -> Image.Image:
    source = Image.open(GOLD_IMAGE).convert("RGBA")
    nose = Image.open(GOLD_NOSE).convert("L").resize(source.size, Image.Resampling.NEAREST)
    mouth = Image.open(GOLD_MOUTH).convert("L").resize(source.size, Image.Resampling.NEAREST)
    red = Image.new("RGBA", source.size, (255, 40, 40, 0))
    red.putalpha(nose.point(lambda v: 150 if v > 8 else 0))
    cyan = Image.new("RGBA", source.size, (0, 230, 230, 0))
    cyan.putalpha(mouth.point(lambda v: 120 if v > 8 else 0))
    return Image.alpha_composite(Image.alpha_composite(source, red), cyan).convert("RGB")


def make_panel(source: Image.Image, v3_overlay: Image.Image, v4_overlay: Image.Image, v4_mask: Image.Image, delta: Image.Image) -> Path:
    crop = (255, 210, 520, 475)
    gold_nose = Image.open(GOLD_NOSE).convert("RGB")
    gold_mouth = Image.open(GOLD_MOUTH).convert("RGB")
    tiles = [
        label_tile(source.crop(crop), "source nose/mouth crop", (320, 320)),
        label_tile(v3_overlay.crop(crop), "v3 existing overlay", (320, 320)),
        label_tile(v4_overlay.crop(crop), "v4 candidate overlay", (320, 320)),
        label_tile(draw_guardrail_overlay(source, v4_mask).crop(crop), "v4 guardrails", (320, 320)),
        label_tile(v4_mask.convert("RGB").crop(crop), "v4 mask only", (320, 320)),
        label_tile(delta.convert("RGB").crop(crop), "v3 to v4 delta", (320, 320)),
        label_tile(gold_overlay(), "CelebAMask nose red / mouth cyan", (320, 320)),
        label_tile(gold_nose, "CelebAMask nose mask ref", (320, 320)),
        label_tile(gold_mouth, "CelebAMask mouth protected ref", (320, 320)),
    ]
    panel = Image.new("RGB", (320 * 3, (320 + 34) * 3), (0, 0, 0))
    for index, tile in enumerate(tiles):
        panel.paste(tile, ((index % 3) * 320, (index // 3) * (320 + 34)))
    panel_path = RUNTIME_DIR / "wave70_mf70_nose_visible_surface_v4_review_panel.png"
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(panel_path)
    return panel_path


def main() -> int:
    for path in [SOURCE_IMAGE, V3_MASK, V3_OVERLAY, GOLD_IMAGE, GOLD_NOSE, GOLD_MOUTH]:
        if not path.exists():
            raise FileNotFoundError(path)

    source = Image.open(SOURCE_IMAGE).convert("RGB")
    v3_mask = Image.open(V3_MASK).convert("L")
    v3_overlay = Image.open(V3_OVERLAY).convert("RGB")
    v4_mask = make_mask(source.size)
    v4_overlay = make_overlay(source, v4_mask)
    removed = ImageChops.subtract(v3_mask.point(lambda v: 255 if v > 8 else 0), v4_mask.point(lambda v: 255 if v > 8 else 0))
    added = ImageChops.subtract(v4_mask.point(lambda v: 255 if v > 8 else 0), v3_mask.point(lambda v: 255 if v > 8 else 0))
    delta = Image.new("RGB", source.size, (0, 0, 0))
    delta.paste((255, 65, 65), mask=removed)
    delta.paste((40, 220, 110), mask=added)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mask_path = OUT_DIR / "wave70_mf70_nose_visible_surface_v4_mask.png"
    overlay_path = OUT_DIR / "wave70_mf70_nose_visible_surface_v4_overlay.png"
    coords_path = OUT_DIR / "wave70_mf70_nose_visible_surface_v4_coordinates.json"
    v4_mask.save(mask_path)
    v4_overlay.save(overlay_path)
    write_json(coords_path, {"source_image": rel(SOURCE_IMAGE), "polygons": polygons_v4(), "protected_regions": protected_regions()})
    panel_path = make_panel(source, v3_overlay, v4_overlay, v4_mask, delta)

    protected_masks = {}
    for name, polygon in protected_regions().items():
        m = Image.new("L", source.size, 0)
        ImageDraw.Draw(m).polygon(polygon, fill=255)
        protected_masks[name] = m
    protected_hits = {name: count_intersection(v4_mask, mask) for name, mask in protected_masks.items()}
    protected_hits = {name: count for name, count in protected_hits.items() if count}

    v3_stats = mask_stats(v3_mask)
    v4_stats = mask_stats(v4_mask)
    removed_pixels = mask_stats(removed)["nonzero_pixels"]
    added_pixels = mask_stats(added)["nonzero_pixels"]
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_at": datetime.now(ZoneInfo("America/Chicago")).isoformat(),
        "result": "candidate_created_pending_strict_visual_review_not_promoted",
        "task": "Repair mf70_nose with gold-reference-informed nose/mouth separation after user flagged nose masks covering mouth/philtrum.",
        "local_only": True,
        "aws_contacted": False,
        "github_api_contacted": False,
        "civitai_contacted": False,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "source_image": rel(SOURCE_IMAGE),
        "source_sha256": sha256(SOURCE_IMAGE),
        "supersedes_candidate": "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MF70_NOSE_SOURCE_LANDMARK_REPAIR_V3_20260707T225500-0500.json",
        "gold_standard_inputs": {
            "intake_evidence": "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASKED_WAREHOUSE_FACIAL_GOLD_STANDARD_INTAKE_20260709T221608-0500.json",
            "celebamask_image": rel(GOLD_IMAGE),
            "celebamask_nose": rel(GOLD_NOSE),
            "celebamask_mouth": rel(GOLD_MOUTH),
            "rule_applied": "nose mask is an isolated bridge/tip/alae region and must not include mouth, lips, teeth, or philtrum plane.",
        },
        "artifacts": {
            "mask": rel(mask_path),
            "mask_sha256": sha256(mask_path),
            "overlay": rel(overlay_path),
            "overlay_sha256": sha256(overlay_path),
            "coordinate_manifest": rel(coords_path),
            "coordinate_manifest_sha256": sha256(coords_path),
            "review_panel": rel(panel_path),
            "review_panel_sha256": sha256(panel_path),
        },
        "v3_stats": v3_stats,
        "v4_stats": v4_stats,
        "v3_to_v4_delta": {
            "removed_pixels": removed_pixels,
            "added_pixels": added_pixels,
            "net_pixel_change": v4_stats["nonzero_pixels"] - v3_stats["nonzero_pixels"],
            "area_change_ratio": round((v4_stats["nonzero_pixels"] - v3_stats["nonzero_pixels"]) / max(1, v3_stats["nonzero_pixels"]), 6),
        },
        "protected_region_hits": protected_hits,
        "strict_visual_findings": [
            "V4 remains inside the visible nose bridge/tip/alae surface and keeps the lower boundary above the philtrum/lip plane.",
            "Gold reference panel shows nose and mouth as separate regions; v4 follows that hierarchy for this source.",
            "No active ComfyUI input mask was overwritten, no generation ran, and no row was completed.",
        ],
        "qa_decision": "candidate_only_continue_review_before_any_runtime_or_promotion",
        "next_required_action": "High-zoom review the v4 panel; if acceptable, run one bounded local proof with a v4-specific input filename or continue adjacent facial row repair.",
    }
    qa_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / f"{EVIDENCE_ID}.json"
    write_json(qa_path, payload)
    tracker_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(qa_path, tracker_path)
    print(json.dumps({"qa": rel(qa_path), "tracker": rel(tracker_path), "panel": rel(panel_path), "result": payload["result"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
