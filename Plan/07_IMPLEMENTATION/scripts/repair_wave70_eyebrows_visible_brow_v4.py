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
STAMP = "20260710T001900-0500"
EVIDENCE_ID = f"W70_MF70_EYEBROWS_VISIBLE_BROW_REPAIR_V4_{STAMP}"
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
V3_MASK = PROJECT_ROOT / "Plan/Instructions/Operations/Prepared_Input_Assets/wave70_mf70_eyebrows_v3_20260708T001500-0500/wave70_mf70_eyebrows_v3_mask.png"
V3_OVERLAY = PROJECT_ROOT / "Plan/Instructions/Operations/Prepared_Input_Assets/wave70_mf70_eyebrows_v3_20260708T001500-0500/wave70_mf70_eyebrows_v3_overlay.png"
GOLD_L_BROW = PROJECT_ROOT / "MaskedWarehouse/CelebAMask-HQ/CelebAMask-HQ-mask-anno/0/00000_l_brow.png"
GOLD_R_BROW = PROJECT_ROOT / "MaskedWarehouse/CelebAMask-HQ/CelebAMask-HQ-mask-anno/0/00000_r_brow.png"
GOLD_IMAGE = PROJECT_ROOT / "MaskedWarehouse/CelebAMask-HQ/CelebA-HQ-img/0.jpg"
OUT_DIR = PROJECT_ROOT / f"Plan/Instructions/Operations/Prepared_Input_Assets/wave70_mf70_eyebrows_visible_brow_v4_{STAMP}"
RUNTIME_DIR = PROJECT_ROOT / f"runtime_artifacts/mask_factory/wave70_mf70_eyebrows_visible_brow_v4/{STAMP}"
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
    # Coordinates are source-image pixel coordinates, manually tightened from the
    # visible dark brow strokes after the user rejected v3's broad/high masks.
    return {
        "viewer_left_visible_brow": [
            (219, 282),
            (239, 276),
            (263, 277),
            (288, 285),
            (300, 294),
            (293, 303),
            (263, 296),
            (236, 292),
            (219, 291),
        ],
        "viewer_right_visible_brow": [
            (415, 283),
            (440, 277),
            (468, 279),
            (494, 287),
            (505, 296),
            (498, 303),
            (466, 295),
            (438, 292),
            (416, 292),
        ],
    }


def make_mask(size: tuple[int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for polygon in polygons_v4().values():
        draw.polygon(polygon, fill=255)
    return mask


def make_overlay(source: Image.Image, mask: Image.Image) -> Image.Image:
    rgba = source.convert("RGBA")
    fill = Image.new("RGBA", rgba.size, (30, 220, 120, 0))
    fill.putalpha(mask.point(lambda value: min(175, int(value * 0.68))))
    overlay = Image.alpha_composite(rgba, fill)
    outline = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(outline)
    for polygon in polygons_v4().values():
        draw.line(polygon + [polygon[0]], fill=(255, 255, 255, 235), width=2)
    return Image.alpha_composite(overlay, outline).convert("RGB")


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


def build_panel(source: Image.Image, v3_overlay: Image.Image, v4_overlay: Image.Image, v4_mask: Image.Image, delta: Image.Image) -> Path:
    crop = (185, 245, 555, 350)
    gold = Image.open(GOLD_IMAGE).convert("RGB")
    gold_l = Image.open(GOLD_L_BROW).convert("L")
    gold_r = Image.open(GOLD_R_BROW).convert("L")
    gold_brows = ImageChops.lighter(gold_l, gold_r).convert("RGB")

    tiles = [
        label_tile(source.crop(crop), "source brow crop", (370, 130)),
        label_tile(v3_overlay.crop(crop), "v3 overbroad/high overlay", (370, 130)),
        label_tile(v4_overlay.crop(crop), "v4 visible-brow candidate", (370, 130)),
        label_tile(v4_mask.convert("RGB").crop(crop), "v4 mask only", (370, 130)),
        label_tile(delta.convert("RGB").crop(crop), "v3 to v4 delta", (370, 130)),
        label_tile(gold_brows, "CelebAMask brow-mask shape ref", (370, 370)),
        label_tile(gold, "CelebAMask source ref", (370, 370)),
    ]
    panel = Image.new("RGB", (370 * 5, 164 + 404), (0, 0, 0))
    for idx, tile in enumerate(tiles[:5]):
        panel.paste(tile, (370 * idx, 0))
    panel.paste(tiles[5], (370 * 1, 164))
    panel.paste(tiles[6], (370 * 2, 164))
    draw = ImageDraw.Draw(panel)
    draw.text(
        (370 * 3 + 16, 210),
        "Candidate-only QA notes:\n"
        "- V3 was too broad/high for the visible brows.\n"
        "- V4 trims outer overreach and stays separate\n"
        "  from eyes, eyelids, forehead, and hair.\n"
        "- No active mask promotion or generation.",
        fill=(255, 220, 150),
    )
    panel_path = RUNTIME_DIR / "wave70_mf70_eyebrows_visible_brow_v4_review_panel.png"
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(panel_path)
    return panel_path


def main() -> int:
    for path in [SOURCE_IMAGE, V3_MASK, V3_OVERLAY, GOLD_L_BROW, GOLD_R_BROW, GOLD_IMAGE]:
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
    mask_path = OUT_DIR / "wave70_mf70_eyebrows_visible_brow_v4_mask.png"
    overlay_path = OUT_DIR / "wave70_mf70_eyebrows_visible_brow_v4_overlay.png"
    coords_path = OUT_DIR / "wave70_mf70_eyebrows_visible_brow_v4_coordinates.json"
    v4_mask.save(mask_path)
    v4_overlay.save(overlay_path)
    write_json(coords_path, {"source_image": rel(SOURCE_IMAGE), "polygons": polygons_v4()})
    panel_path = build_panel(source, v3_overlay, v4_overlay, v4_mask, delta)

    v3_stats = mask_stats(v3_mask)
    v4_stats = mask_stats(v4_mask)
    removed_pixels = mask_stats(removed)["nonzero_pixels"]
    added_pixels = mask_stats(added)["nonzero_pixels"]
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_at": datetime.now(ZoneInfo("America/Chicago")).isoformat(),
        "result": "candidate_created_pending_strict_visual_review_not_promoted",
        "task": "Repair mf70_eyebrows after v3 review showed broad/high eyebrow masks extending beyond visible brow strokes.",
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
        "supersedes_candidate": "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MF70_EYEBROWS_V3_SOURCE_LANDMARK_REPAIR_20260708T001500-0500.json",
        "gold_standard_inputs": {
            "intake_evidence": "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASKED_WAREHOUSE_FACIAL_GOLD_STANDARD_INTAKE_20260709T221608-0500.json",
            "celebamask_l_brow": rel(GOLD_L_BROW),
            "celebamask_r_brow": rel(GOLD_R_BROW),
            "rule_applied": "eyebrow masks should be narrow visible brow strokes, separate from eyes, eyelids, forehead skin, and hair occlusion.",
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
        "strict_visual_findings": [
            "Existing v3 panel shows brow masks too broad/high, with outer extension beyond visible brow strokes.",
            "V4 trims the viewer-right brow outer tail and viewer-left hair-side overreach compared with v3.",
            "V4 is still a single-source candidate and is not promotion evidence.",
            "No ComfyUI input mask was overwritten, no generation ran, and no row was completed.",
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
