from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REF_FULL_DIR = PROJECT_ROOT / "Ref_Image_1/Full"
GOLD_STANDARD_MANIFEST = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_body_mask_gold_standard.json"

NOW = datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0)
RUN_STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")
ISO_STAMP = NOW.isoformat()
EVIDENCE_ID = f"W70_REF_IMAGE_1_FULL_BODY_REFERENCES_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/ingest_ref_image_1_full_body_references.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/ref_image_1_full_body_references" / RUN_STAMP
RUNTIME_IMAGE_DIR = RUNTIME_DIR / "images"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_gold_mask_summary() -> dict[str, object]:
    summary: dict[str, object] = {
        "manifest_path": rel(GOLD_STANDARD_MANIFEST),
        "manifest_exists": GOLD_STANDARD_MANIFEST.exists(),
        "overlay_file_count": 0,
        "extracted_nonzero_mask_count": 0,
        "layout_interpretation": {
            "top_strip": "partial upper-body / one-third-body reference only; absent lower/full-body masks here are not failures",
            "lower_strip": "primary full-body pose/body-mask validation area",
        },
        "torso_reference_mask_count": 0,
        "limb_reference_mask_count": 0,
        "hand_reference_mask_count": 0,
    }
    if not GOLD_STANDARD_MANIFEST.exists():
        return summary
    manifest = json.loads(GOLD_STANDARD_MANIFEST.read_text(encoding="utf-8"))
    masks = manifest.get("extracted_masks", [])
    torso_tokens = ("abdomen", "stomach", "belly", "pelvic", "breast", "glute", "chest")
    limb_tokens = ("arm", "thigh", "calf", "feet", "foot", "toes")
    hand_tokens = ("hand", "finger", "thumb", "pinky")
    summary.update(
        {
            "overlay_file_count": manifest.get("overlay_file_count", len(masks)),
            "extracted_nonzero_mask_count": manifest.get("extracted_nonzero_mask_count", 0),
            "torso_reference_mask_count": sum(
                1 for item in masks if any(token in str(item.get("label", "")).lower() for token in torso_tokens)
            ),
            "limb_reference_mask_count": sum(
                1 for item in masks if any(token in str(item.get("label", "")).lower() for token in limb_tokens)
            ),
            "hand_reference_mask_count": sum(
                1 for item in masks if any(token in str(item.get("label", "")).lower() for token in hand_tokens)
            ),
        }
    )
    return summary


def discover_images() -> list[Path]:
    if not REF_FULL_DIR.exists():
        return []
    return [
        path
        for path in sorted(REF_FULL_DIR.rglob("*"))
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]


def image_record(path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        width, height = image.size
        mode = image.mode
    runtime_copy = RUNTIME_IMAGE_DIR / path.relative_to(REF_FULL_DIR)
    runtime_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, runtime_copy)
    relative_name = path.relative_to(REF_FULL_DIR).as_posix()
    coverage_scope = "full_or_near_full_body_reference_user_provided"
    coverage_limitations: list[str] = []
    if relative_name.lower().startswith("new folder/"):
        coverage_scope = "near_full_body_knees_to_head_reference"
        coverage_limitations = [
            "user_corrected_not_full_body",
            "covers_from_knees_to_top_of_head",
            "do_not_use_as_full_body_feet_toes_ankles_or_lower_calf_proof",
            "usable_for_torso_head_hair_upper_limb_and_above_knee_body_context_only",
        ]
    return {
        "path": rel(path),
        "runtime_copy": rel(runtime_copy),
        "sha256": sha256_file(path),
        "byte_length": path.stat().st_size,
        "dimensions": [width, height],
        "mode": mode,
        "relative_to_full_dir": relative_name,
        "coverage_scope": coverage_scope,
        "coverage_limitations": coverage_limitations,
        "role": "user_provided_full_or_near_full_body_reference_for_body_part_authority_rows",
    }


def make_contact_sheet(records: list[dict[str, object]]) -> Path | None:
    if not records:
        return None
    thumbs = []
    for record in records:
        image = Image.open(PROJECT_ROOT / str(record["path"])).convert("RGB")
        image.thumbnail((220, 300))
        thumbs.append((record, image.copy()))
        image.close()

    font = ImageFont.load_default()
    cell_w, cell_h = 260, 360
    cols = 4
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h + 80), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((16, 14), "Ref_Image_1/Full body references", fill=(0, 0, 0), font=font)
    draw.text((16, 38), f"Images: {len(thumbs)} | Use with Ref_Image_1 gold masks; no automatic promotion.", fill=(120, 0, 0), font=font)

    for index, (record, thumb) in enumerate(thumbs):
        col = index % cols
        row = index // cols
        x = col * cell_w + 20
        y = row * cell_h + 90
        sheet.paste(thumb, (x, y))
        draw.rectangle([x, y, x + thumb.width - 1, y + thumb.height - 1], outline=(0, 0, 0), width=1)
        dims = record["dimensions"]
        label = f"{index + 1}: {dims[0]}x{dims[1]}"
        rel_name = str(record["relative_to_full_dir"])[:34]
        draw.text((x, y + thumb.height + 8), label, fill=(0, 0, 0), font=font)
        draw.text((x, y + thumb.height + 28), rel_name, fill=(40, 40, 40), font=font)

    panel_path = RUNTIME_DIR / "ref_image_1_full_body_references_contact_sheet.png"
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(panel_path)
    return panel_path


def main() -> int:
    records = [image_record(path) for path in discover_images()]
    panel_path = make_contact_sheet(records)
    gold_summary = load_gold_mask_summary()

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "ref_image_1_full_body_references.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "ref_image_1_full_body_references.json"
    runtime_evidence_path = RUNTIME_DIR / "ref_image_1_full_body_references.json"

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "created_iso": ISO_STAMP,
        "script": SCRIPT_REL,
        "project_root": str(PROJECT_ROOT),
        "reference_full_dir": {
            "path": rel(REF_FULL_DIR),
            "exists": REF_FULL_DIR.exists(),
            "recursive_image_count": len(records),
        },
        "user_correction_applied": {
            "summary": "Use Ref_Image_1/Full full-body and near-full-body references for body parts/full-body parts together with the Ref_Image_1 gold-standard masks.",
            "supersedes_for_body_rows": "Do not keep reusing the older non-full-body portrait source as the decisive body-part visibility blocker when Ref_Image_1/Full is the intended body authority reference set.",
            "near_full_exception": "The image under Ref_Image_1/Full/New folder is not full body; user clarified it covers from the knees to the top of the head, so it cannot prove feet/toes/ankles/lower-calf coverage.",
        },
        "gold_standard_masks": gold_summary,
        "full_body_references": records,
        "artifacts": {
            "runtime_evidence": rel(runtime_evidence_path),
            "contact_sheet": rel(panel_path) if panel_path else None,
        },
        "qa_decision": "ref_image_1_full_body_references_available_for_body_authority_rows",
        "promotion_decision": "no_mask_promoted_reference_manifest_only",
        "next_step": "Re-evaluate TRK-W70-0167 torso authority using this full-body reference manifest plus Ref_Image_1 body-mask gold standard evidence.",
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
        },
    }

    for path in [
        qa_evidence_path,
        qa_canonical_path,
        tracker_evidence_path,
        tracker_canonical_path,
        runtime_evidence_path,
    ]:
        write_json(path, payload)

    print(
        json.dumps(
            {
                "evidence_id": EVIDENCE_ID,
                "image_count": len(records),
                "qa_decision": payload["qa_decision"],
                "evidence": rel(qa_evidence_path),
                "contact_sheet": rel(panel_path) if panel_path else None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
