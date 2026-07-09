#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


RUN_STAMP = "20260707T222606-0500"
PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
MASK_DIR = PROJECT_ROOT / "ComfyUI/input"
OUT_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_user_dispute_current_mask_contact_sheet"
QA_EVIDENCE = PROJECT_ROOT / (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    f"W70_CURRENT_INPUT_MASKS_USER_DISPUTE_FAIL_CLOSED_AUDIT_{RUN_STAMP}.json"
)
TRACKER_EVIDENCE = PROJECT_ROOT / (
    "Plan/Tracker/Evidence/"
    f"W70_CURRENT_INPUT_MASKS_USER_DISPUTE_FAIL_CLOSED_AUDIT_{RUN_STAMP}.json"
)

FACE_CROP = (135, 170, 630, 575)
THUMB_W = 330
THUMB_H = 300
COLS = 3

REVIEW_FINDINGS = {
    "cheeks_skin": "blocked_fail_closed: broad cheek blobs are not source-contour-traced and need protected-neighbor proof.",
    "expression_region": "blocked_fail_closed: broad facial polygon is not an anatomical expression-region proof.",
    "eyebrows": "blocked_fail_closed: horizontal band includes non-brow forehead/skin context and is not eyebrow-shaped.",
    "eyelashes": "blocked_fail_closed: short strokes are not proven aligned to actual lash strands or protected eyelid/eye boundaries.",
    "eyelids": "blocked_fail_closed: large patches sit around/above the eyes rather than thin upper/lower eyelid bands.",
    "eyes_full": "blocked_fail_closed: eye regions include surrounding skin and require zoomed source-boundary proof.",
    "face_full_instance": "blocked_fail_closed: broad face polygon requires target-definition proof and hair/background/neck exclusion.",
    "face_identity_critical": "blocked_fail_closed: broad identity polygon includes non-face/hair/background-adjacent regions.",
    "forehead_skin": "blocked_fail_closed: broad forehead blob needs hairline/eyebrow protected-boundary proof.",
    "jawline_chin": "blocked_fail_closed: jaw/chin arc is not source-contour-traced and spills into neck/collar neighborhood.",
    "left_eye": "blocked_fail_closed: single-eye patch includes surrounding skin; needs visible-eye target definition and zoomed proof.",
    "mouth_lips": "blocked_fail_closed: current shape is closer to a lip strip/contour than a proven full mouth-lips mask.",
    "nose": "blocked_fail_closed: nose mask remains too broad and reaches toward philtrum/upper-mouth area.",
    "pupils_iris_sclera": "blocked_fail_closed: needs per-eye zoom proof; full-face sheet alone cannot prove iris/sclera alignment.",
    "right_eye": "blocked_fail_closed: single-eye patch includes surrounding skin; needs visible-eye target definition and zoomed proof.",
    "skin_tone_continuity": "blocked_fail_closed: broad skin polygon includes mixed face/neck regions and needs explicit target definition.",
    "teeth": "blocked_fail_closed: tiny visible-teeth strip needs zoomed proof and mouth/lip protected-neighbor matrix.",
    "under_eye": "blocked_fail_closed: under-eye bands need zoomed proof against eyelid, nose bridge, cheek, and sclera boundaries.",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mask_label(path: Path) -> str:
    return path.stem.replace("wave70_mf70_", "").replace("_mask", "")


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def threshold_count(mask: Image.Image) -> int:
    return sum(1 for value in mask.getdata() if value > 0)


def make_overlay(source: Image.Image, mask: Image.Image) -> Image.Image:
    overlay = Image.new("RGBA", source.size, (255, 0, 0, 0))
    visible = mask.point(lambda value: 125 if value > 12 else 0)
    overlay.putalpha(visible)
    return Image.alpha_composite(source.convert("RGBA"), overlay).convert("RGB")


def draw_tile(source: Image.Image, mask_path: Path, font: ImageFont.ImageFont) -> tuple[Image.Image, dict[str, Any]]:
    mask = Image.open(mask_path).convert("L")
    label = mask_label(mask_path)
    overlay = make_overlay(source, mask).crop(FACE_CROP)
    draw = ImageDraw.Draw(overlay)
    bbox = mask.getbbox()
    if bbox:
        left, top, right, bottom = bbox
        clipped = (
            max(left, FACE_CROP[0]) - FACE_CROP[0],
            max(top, FACE_CROP[1]) - FACE_CROP[1],
            min(right, FACE_CROP[2]) - FACE_CROP[0],
            min(bottom, FACE_CROP[3]) - FACE_CROP[1],
        )
        if clipped[0] < clipped[2] and clipped[1] < clipped[3]:
            draw.rectangle(clipped, outline=(255, 255, 0), width=2)

    overlay = overlay.resize((THUMB_W, THUMB_H - 28), Image.Resampling.LANCZOS)
    tile = Image.new("RGB", (THUMB_W, THUMB_H), (10, 10, 10))
    tile.paste(overlay, (0, 28))
    draw = ImageDraw.Draw(tile)
    draw.text((8, 8), label, fill=(255, 255, 255), font=font)

    record = {
        "mask_type_id": f"mf70_{label}",
        "mask_label": label,
        "mask_path": rel(mask_path),
        "mask_sha256": sha256_file(mask_path),
        "mask_bbox": bbox,
        "mask_nonzero_pixels": threshold_count(mask),
        "face_crop_nonzero_pixels": threshold_count(mask.crop(FACE_CROP)),
        "review_finding": REVIEW_FINDINGS.get(label, "blocked_fail_closed: no source-alignment pass recorded."),
        "promotion_decision": "blocked_no_wave70_mask_promotion_row_gate_pass_true",
    }
    return tile, record


def main() -> int:
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    masks = sorted(MASK_DIR.glob("wave70_mf70_*_mask.png"))
    font = ImageFont.load_default()
    rows = (len(masks) + COLS - 1) // COLS
    panel = Image.new("RGB", (COLS * THUMB_W, rows * THUMB_H), (18, 18, 18))
    records: list[dict[str, Any]] = []

    for index, mask_path in enumerate(masks):
        tile, record = draw_tile(source, mask_path, font)
        panel.paste(tile, ((index % COLS) * THUMB_W, (index // COLS) * THUMB_H))
        records.append(record)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    contact_sheet = OUT_DIR / "wave70_current_all_input_masks_source_overlay_contact_sheet.png"
    summary_json = OUT_DIR / "wave70_current_all_input_masks_source_overlay_contact_sheet.json"
    panel.save(contact_sheet)

    payload = {
        "evidence_id": f"W70_CURRENT_INPUT_MASKS_USER_DISPUTE_FAIL_CLOSED_AUDIT_{RUN_STAMP}",
        "timestamp_local": RUN_STAMP,
        "source_image": rel(SOURCE_IMAGE),
        "source_sha256": sha256_file(SOURCE_IMAGE),
        "face_crop": FACE_CROP,
        "contact_sheet": rel(contact_sheet),
        "contact_sheet_sha256": sha256_file(contact_sheet),
        "user_report": "User states every generated mask appears visibly off from the actual picture; prior mask passes are not trusted.",
        "audit_scope": "All current wave70_mf70_*_mask.png files in ComfyUI/input over the active source portrait.",
        "decision": "fail_closed_global_mask_alignment_dispute_confirmed",
        "status_policy": "No current mask receives pass/candidate/complete status without exact W70_MASK_PROMOTION_ROW_GATE_PASS_TRUE evidence.",
        "generated_output_policy": "Generated-output stability is output-geometry evidence only and does not prove source-image mask alignment.",
        "mask_count": len(records),
        "records": records,
    }
    write_json(summary_json, payload)
    write_json(QA_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)
    print(QA_EVIDENCE)
    print(TRACKER_EVIDENCE)
    print(contact_sheet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
