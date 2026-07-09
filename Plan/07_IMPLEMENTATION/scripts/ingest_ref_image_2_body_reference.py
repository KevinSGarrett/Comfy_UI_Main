from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
REF_DIR = PROJECT_ROOT / "Ref_Image_2"
MAIN_REFERENCE = REF_DIR / "97f30ff4819b8b8206e8ce30f2355800.jpg"
MANIFEST_CSV = REF_DIR / "manifest.csv"
README = REF_DIR / "README.txt"

NOW = datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0)
RUN_STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")
ISO_STAMP = NOW.isoformat()
EVIDENCE_ID = f"W70_REF_IMAGE_2_BODY_REFERENCE_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/ingest_ref_image_2_body_reference.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/ref_image_2_body_reference" / RUN_STAMP
RUNTIME_IMAGE_DIR = RUNTIME_DIR / "images"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
BODY_CATEGORY_ALIASES = {
    "chest": "breasts",
}


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


def image_info(path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        width, height = image.size
        mode = image.mode
    return {
        "path": rel(path),
        "sha256": sha256_file(path),
        "byte_length": path.stat().st_size,
        "dimensions": [width, height],
        "mode": mode,
    }


def read_manifest_rows() -> list[dict[str, str]]:
    if not MANIFEST_CSV.exists():
        return []
    with MANIFEST_CSV.open("r", newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def find_overlay_file(filename: str) -> Path | None:
    matches = [
        path
        for path in REF_DIR.rglob(filename)
        if path.is_file()
        and path.suffix.lower() in IMAGE_EXTENSIONS
        and "Face\\Ref_Image_2" not in str(path)
        and "Face/Ref_Image_2" not in str(path)
    ]
    if not matches:
        return None
    matches.sort(key=lambda item: len(str(item)))
    return matches[0]


def overlay_record(row: dict[str, str]) -> dict[str, object]:
    category = row.get("category", "").strip()
    mask_label = row.get("mask_label", "").strip()
    organized_path = row.get("organized_path", "").strip()
    filename = Path(organized_path).name
    actual_path = find_overlay_file(filename)
    info: dict[str, object] = {
        "category": category,
        "normalized_category": BODY_CATEGORY_ALIASES.get(category, category),
        "mask_label": mask_label,
        "source_zip_path": row.get("source_zip_path", "").strip(),
        "manifest_organized_path": organized_path,
        "overlay_exists": actual_path is not None,
        "actual_overlay_path": rel(actual_path) if actual_path else "",
        "role": "user_provided_ref_image_2_gold_mask_overlay",
    }
    if actual_path:
        info.update(image_info(actual_path))
    return info


def category_presence(records: list[dict[str, object]]) -> dict[str, bool]:
    labels = " ".join(
        f"{record.get('normalized_category', '')} {record.get('mask_label', '')}".lower()
        for record in records
    )
    return {
        "torso_abdomen": any(token in labels for token in ["abdomen", "stomach", "belly"]),
        "arms_hands_fingers": any(token in labels for token in ["arm", "hand", "finger", "thumb"]),
        "legs_feet_toes": any(token in labels for token in ["thigh", "calf", "feet", "foot", "toe"]),
        "pelvis_glute": any(token in labels for token in ["pelvic", "glute"]),
        "hair": "hair" in labels,
        "breasts": "breast" in labels or "chest" in labels,
        "face": "face" in labels or "eye" in labels or "nose" in labels or "jaw" in labels,
        "clothes": "clothes" in labels or "bra" in labels or "underwear" in labels,
    }


def summarize_categories(records: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("normalized_category", ""))].append(str(record.get("mask_label", "")))
    return [
        {"category": category, "count": len(labels), "labels": sorted(labels)}
        for category, labels in sorted(grouped.items())
    ]


def make_contact_sheet(records: list[dict[str, object]]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "ref_image_2_body_reference_contact_sheet.png"
    font = ImageFont.load_default()
    panel = Image.new("RGB", (1600, 1050), "white")
    draw = ImageDraw.Draw(panel)
    draw.text((24, 18), "Ref_Image_2 full-body reference and organized gold masks", fill=(0, 0, 0), font=font)
    draw.text((24, 42), "Reference only: strengthens gold mask context; does not promote masks by itself.", fill=(120, 0, 0), font=font)

    if MAIN_REFERENCE.exists():
        main_copy = RUNTIME_IMAGE_DIR / MAIN_REFERENCE.name
        main_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MAIN_REFERENCE, main_copy)
        image = Image.open(MAIN_REFERENCE).convert("RGB")
        image.thumbnail((360, 540))
        panel.paste(image, (32, 100))
        draw.rectangle([32, 100, 32 + image.width - 1, 100 + image.height - 1], outline=(0, 0, 0), width=1)
        draw.text((32, 655), "Main full-body Ref_Image_2", fill=(0, 0, 0), font=font)
        image.close()

    sample_records = [record for record in records if record.get("overlay_exists")][:24]
    cell_w, cell_h = 185, 145
    start_x, start_y = 430, 100
    for index, record in enumerate(sample_records):
        path = PROJECT_ROOT / str(record["actual_overlay_path"])
        thumb = Image.open(path).convert("RGB")
        thumb.thumbnail((150, 95))
        col = index % 6
        row = index // 6
        x = start_x + col * cell_w
        y = start_y + row * cell_h
        panel.paste(thumb, (x, y))
        draw.rectangle([x, y, x + thumb.width - 1, y + thumb.height - 1], outline=(80, 80, 80), width=1)
        label = str(record.get("mask_label", ""))[:24]
        category = str(record.get("normalized_category", ""))[:24]
        draw.text((x, y + thumb.height + 6), category, fill=(0, 0, 0), font=font)
        draw.text((x, y + thumb.height + 22), label, fill=(40, 40, 40), font=font)
        thumb.close()

    counts = Counter(str(record.get("normalized_category", "")) for record in records)
    y = 735
    draw.text((32, y), f"Manifest rows: {len(records)} | Located overlays: {sum(1 for r in records if r.get('overlay_exists'))}", fill=(0, 0, 0), font=font)
    y += 26
    for category, count in sorted(counts.items()):
        draw.text((32, y), f"{category}: {count}", fill=(0, 0, 0), font=font)
        y += 22
    panel.save(panel_path)
    return panel_path


def main() -> int:
    if not MAIN_REFERENCE.exists():
        raise FileNotFoundError(MAIN_REFERENCE)
    rows = read_manifest_rows()
    records = [overlay_record(row) for row in rows]
    located = [record for record in records if record.get("overlay_exists")]
    panel_path = make_contact_sheet(records)

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "ref_image_2_body_reference.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "ref_image_2_body_reference.json"
    runtime_evidence_path = RUNTIME_DIR / "ref_image_2_body_reference.json"

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "created_iso": ISO_STAMP,
        "script": SCRIPT_REL,
        "project_root": str(PROJECT_ROOT),
        "reference_dir": {
            "path": rel(REF_DIR),
            "exists": REF_DIR.exists(),
        },
        "main_reference": {
            **image_info(MAIN_REFERENCE),
            "coverage_scope": "full_body_reference_user_provided",
            "role": "additional_full_body_gold_reference_for_body_mask_authority_rows",
        },
        "manifest": {
            "path": rel(MANIFEST_CSV),
            "exists": MANIFEST_CSV.exists(),
            "sha256": sha256_file(MANIFEST_CSV) if MANIFEST_CSV.exists() else "",
            "row_count": len(rows),
            "located_overlay_count": len(located),
            "missing_overlay_count": len(rows) - len(located),
        },
        "readme": {
            "path": rel(README),
            "exists": README.exists(),
            "sha256": sha256_file(README) if README.exists() else "",
        },
        "gold_mask_overlays": records,
        "category_summary": summarize_categories(records),
        "category_presence": category_presence(records),
        "layout_interpretation": {
            "role": "single full-body image with organized per-part mask overlays",
            "use_with": "Ref_Image_1 main/gold masks and Ref_Image_1/Full references",
            "no_duplicate_counting": "Files under Ref_Image_2/Face/Ref_Image_2 are extracted source copies and are not counted as additional organized masks.",
        },
        "artifacts": {
            "runtime_evidence": rel(runtime_evidence_path),
            "contact_sheet": rel(panel_path),
        },
        "qa_decision": "ref_image_2_full_body_reference_and_gold_masks_available_for_body_authority_rows",
        "promotion_decision": "no_mask_promoted_reference_manifest_only",
        "next_step": "Use Ref_Image_1 plus Ref_Image_2 as gold body reference context for body reference matrix and downstream body authority rows.",
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
                "manifest_rows": len(rows),
                "located_overlay_count": len(located),
                "qa_decision": payload["qa_decision"],
                "evidence": rel(qa_evidence_path),
                "contact_sheet": rel(panel_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
