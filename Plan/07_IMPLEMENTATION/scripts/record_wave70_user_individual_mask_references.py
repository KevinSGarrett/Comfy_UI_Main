#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
RUN_STAMP = "20260708T002500-0500"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_user_individual_mask_references" / RUN_STAMP
QA_EVIDENCE = PROJECT_ROOT / (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    f"W70_USER_INDIVIDUAL_MASK_REFERENCES_REVIEW_{RUN_STAMP}.json"
)
TRACKER_EVIDENCE = PROJECT_ROOT / (
    "Plan/Tracker/Evidence/"
    f"W70_USER_INDIVIDUAL_MASK_REFERENCES_REVIEW_{RUN_STAMP}.json"
)

REFERENCES: list[dict[str, Any]] = [
    {
        "label": "neck_mask_reference_a",
        "source_path": r"C:\Users\kevin\AppData\Local\Temp\codex-clipboard-5766ecf9-a6e8-4c9d-b45d-0f64fe2d5b7c.png",
        "mask_type_ids": ["mf70_neck", "mf70_chest_upper_torso"],
        "review_note": "Neck reference starts below jaw/chin and stops at jacket/collar; it is neck/upper-exposed-skin guidance, not face or jaw.",
    },
    {
        "label": "teeth_area_mask_reference",
        "source_path": r"C:\Users\kevin\AppData\Local\Temp\codex-clipboard-4502ed74-a7e6-4694-90a7-88b1e5f074a4.png",
        "mask_type_ids": ["mf70_teeth", "mf70_mouth_lips"],
        "review_note": "This shows why teeth must be much smaller than the lips; the visible teeth area is only the thin exposed bright slit inside the mouth, while the cyan example includes too much lip if treated as teeth.",
    },
    {
        "label": "jaw_mask_reference",
        "source_path": r"C:\Users\kevin\AppData\Local\Temp\codex-clipboard-57651f0a-ebb3-43e6-b41c-e7f33dd0db2e.png",
        "mask_type_ids": ["mf70_jawline_chin"],
        "review_note": "Jaw/chin reference is a lower-face crescent constrained by cheeks, chin, and lower lip; it must not drift upward into full cheeks or outward into hair.",
    },
    {
        "label": "neck_mask_reference_b_duplicate_visual",
        "source_path": r"C:\Users\kevin\AppData\Local\Temp\codex-clipboard-bd75720c-201e-49eb-8cc0-fc866dc2aa10.png",
        "mask_type_ids": ["mf70_neck", "mf70_chest_upper_torso"],
        "review_note": "Second neck reference appears visually identical to the first and reinforces the same neck/collar/jaw separation.",
    },
    {
        "label": "hair_mask_reference",
        "source_path": r"C:\Users\kevin\AppData\Local\Temp\codex-clipboard-b4106133-70ef-4077-8bf6-730616d1dd6c.png",
        "mask_type_ids": ["mf70_hair_full", "mf70_hairline_edges", "mf70_hair_strands_flyaways"],
        "review_note": "Hair reference shows hair as a large outer mass with a face-shaped inner cutout; current face/eye/brow rows must respect this occlusion boundary.",
    },
    {
        "label": "lips_mask_reference",
        "source_path": r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_43_10 PM.png",
        "mask_type_ids": ["mf70_mouth_lips"],
        "review_note": "Lips reference covers both upper and lower lip surfaces only; it excludes nose, philtrum, chin, surrounding skin, and teeth slit.",
    },
    {
        "label": "irises_mask_reference",
        "source_path": r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_42_58 PM.png",
        "mask_type_ids": ["mf70_pupils_iris_sclera"],
        "review_note": "Irises are small circles inside the visible eye apertures; they must not use broad eye ellipses or include eyelids/sclera.",
    },
    {
        "label": "top_lip_mask_reference",
        "source_path": r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_43_14 PM.png",
        "mask_type_ids": ["mf70_mouth_lips"],
        "review_note": "Top lip is a separate upper-lip crescent under the philtrum; it should not include the bottom lip, teeth slit, or nose base.",
    },
    {
        "label": "pupils_mask_reference",
        "source_path": r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_43_02 PM.png",
        "mask_type_ids": ["mf70_pupils_iris_sclera"],
        "review_note": "Pupils are tiny centered regions inside the irises; a pupil mask must be far smaller than the iris mask.",
    },
    {
        "label": "nose_mask_reference",
        "source_path": r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_43_06 PM.png",
        "mask_type_ids": ["mf70_nose"],
        "review_note": "Nose reference is centered on bridge/tip/nostril bulb, below the brow band and above lips; it must not cover mouth or eyes.",
    },
    {
        "label": "eyebrows_mask_reference",
        "source_path": r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_42_51 PM.png",
        "mask_type_ids": ["mf70_eyebrows"],
        "review_note": "Eyebrows are short strips above eye apertures; the viewer-left eyebrow is partly hair-occluded and must not be extended into hair.",
    },
    {
        "label": "eyes_mask_reference",
        "source_path": r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_42_55 PM.png",
        "mask_type_ids": ["mf70_eyes_full", "mf70_left_eye", "mf70_right_eye"],
        "review_note": "Eyes full reference covers visible eye apertures only; it does not include eyebrows, upper eyelid bands, or surrounding cheek/under-eye skin.",
    },
    {
        "label": "skin_mask_reference",
        "source_path": r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_42_47 PM.png",
        "mask_type_ids": ["mf70_face_full_instance", "mf70_face_identity_critical", "mf70_skin_tone_continuity", "mf70_neck"],
        "review_note": "Skin reference is broad face+neck exposed skin with holes/exclusions for hair, eyes, brows, and lips; it should not be reused as a face-only mask without splitting face and neck.",
    },
    {
        "label": "upper_eyelids_mask_reference",
        "source_path": r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_42_37 PM.png",
        "mask_type_ids": ["mf70_eyelids"],
        "review_note": "Upper eyelids are narrow curved strips above the visible eye aperture; they must not include eyebrow or hair.",
    },
    {
        "label": "lower_eyelids_mask_reference",
        "source_path": r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_42_43 PM.png",
        "mask_type_ids": ["mf70_eyelids", "mf70_under_eye"],
        "review_note": "Lower eyelids are narrow curved strips below the visible eye aperture; they are distinct from broader under-eye bags/skin.",
    },
    {
        "label": "facial_masking_reference_sheet",
        "source_path": r"C:\Users\kevin\Downloads\ChatGPT Image Jul 7, 2026, 11_36_14 PM (2).png",
        "mask_type_ids": [
            "mf70_eyelids",
            "mf70_skin_tone_continuity",
            "mf70_eyebrows",
            "mf70_eyes_full",
            "mf70_pupils_iris_sclera",
            "mf70_nose",
            "mf70_mouth_lips",
            "mf70_teeth",
            "mf70_jawline_chin",
            "mf70_neck",
            "mf70_hair_full",
        ],
        "review_note": "Reference sheet clarifies the hierarchy: skin/face/neck/hair are large parent regions; eyes/irises/pupils/eyelids/brows/lips/teeth/nose/jaw are nested child regions.",
    },
]


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


def font(size: int = 18) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def copy_references() -> list[dict[str, Any]]:
    refs_dir = RUNTIME_DIR / "reference_images"
    refs_dir.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, Any]] = []
    for index, ref in enumerate(REFERENCES, start=1):
        source = Path(ref["source_path"])
        if not source.exists():
            raise FileNotFoundError(source)
        dest = refs_dir / f"{index:02d}_{ref['label']}.png"
        shutil.copy2(source, dest)
        with Image.open(dest) as img:
            dimensions = list(img.size)
            mode = img.mode
        copied.append(
            {
                "label": ref["label"],
                "original_path": str(source),
                "project_path": rel(dest),
                "sha256": sha256_file(dest),
                "dimensions": dimensions,
                "mode": mode,
                "mask_type_ids": ref["mask_type_ids"],
                "review_note": ref["review_note"],
            }
        )
    return copied


def make_contact_sheet(copied: list[dict[str, Any]]) -> Path:
    tile_w, tile_h = 320, 360
    cols = 4
    rows = (len(copied) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (12, 12, 12))
    draw = ImageDraw.Draw(sheet)
    label_font = font(15)
    for index, item in enumerate(copied):
        row, col = divmod(index, cols)
        x = col * tile_w
        y = row * tile_h
        img = Image.open(PROJECT_ROOT / item["project_path"]).convert("RGB")
        img.thumbnail((tile_w, tile_h - 46), Image.Resampling.LANCZOS)
        px = x + (tile_w - img.width) // 2
        py = y + 36 + (tile_h - 46 - img.height) // 2
        sheet.paste(img, (px, py))
        draw.rectangle([x, y, x + tile_w - 1, y + tile_h - 1], outline=(90, 90, 90), width=1)
        draw.text((x + 8, y + 8), item["label"][:38], fill=(245, 245, 245), font=label_font)
    path = RUNTIME_DIR / "wave70_user_individual_mask_references_contact_sheet.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return path


def main() -> int:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    copied = copy_references()
    contact_sheet = make_contact_sheet(copied)
    duplicate_groups: dict[str, list[str]] = {}
    for item in copied:
        duplicate_groups.setdefault(item["sha256"], []).append(item["label"])
    duplicate_groups = {digest: labels for digest, labels in duplicate_groups.items() if len(labels) > 1}
    payload = {
        "schema_version": "1.0",
        "evidence_id": f"W70_USER_INDIVIDUAL_MASK_REFERENCES_REVIEW_{RUN_STAMP}",
        "created_local": RUN_STAMP,
        "task": "Review user-provided individual facial mask references and record exact geometry/semantic corrections for Wave70 mask work.",
        "runtime_artifacts": {
            "runtime_dir": rel(RUNTIME_DIR),
            "contact_sheet": rel(contact_sheet),
            "contact_sheet_sha256": sha256_file(contact_sheet),
        },
        "references": copied,
        "duplicate_reference_hash_groups": duplicate_groups,
        "review_findings": [
            "The user's references confirm the old failure mode: masks were being evaluated as local shapes instead of nested anatomical regions constrained by full face, hair, jaw, neck, and mouth hierarchy.",
            "Eye-family masks must not be broad cyan ellipses that include eyelids/brows/hair. Eyes, irises, pupils, upper eyelids, lower eyelids, eyebrows, and under-eye skin need separate nested regions.",
            "The teeth mask must be the thin visible teeth slit only. A lips-sized or mouth-sized cyan region is wrong for mf70_teeth.",
            "The skin reference is a broad exposed-skin parent region that includes face and neck while excluding hair, eyes, brows, and lips; it must be split before using it for face-only or neck-only rows.",
            "Hair must be treated as a parent occlusion region with an inner face cutout. Face, eye, brow, and cheek masks must be clipped against the hair occlusion boundary.",
            "Jaw/chin and neck are separate: jaw/chin is the lower-face crescent under the mouth; neck begins below the jaw/chin boundary and must stop at clothing/collar where appropriate.",
            "These images are 1024x1024 or sheet references and are not pixel-exact replacements for the active 768x768 source. They are user intent references for geometry rules and future row-specific candidate derivation.",
        ],
        "correction_rules": [
            "No mask row should be promoted from these images alone.",
            "Every derived candidate must be rebuilt against the active source image with a coordinate-transform manifest.",
            "Parent regions must be derived first: hair occlusion, visible face/skin, neck/clothing, and mouth plane.",
            "Child masks must be clipped to parent and protected-neighbor regions: pupils within irises, irises within eyes, eyelids around eyes, brows above eyes and outside hair, teeth within mouth/lip opening.",
            "Future QA panels must show source, mask-only, source+mask, and protected-neighbor overlay at readable zoom.",
        ],
        "affected_mask_type_ids": sorted({mask for ref in copied for mask in ref["mask_type_ids"]}),
        "qa_decision": "user_individual_mask_references_recorded_as_geometry_intent_not_promotable_masks",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_no_W70_MASK_PROMOTION_ROW_GATE_PASS_TRUE",
        "next_step": "Use these references with the full-face scaffold to derive exactly one row-specific candidate mask and visually review it before any runtime proof.",
    }
    write_json(RUNTIME_DIR / "wave70_user_individual_mask_references_review_manifest.json", payload)
    write_json(QA_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE, payload)
    print(json.dumps({"qa_evidence": rel(QA_EVIDENCE), "contact_sheet": rel(contact_sheet)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
