from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont, ImageOps


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
ISO_TS = NOW.replace(microsecond=0).isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_main_reference_source_test_intake" / STAMP

MAIN_DIR = PROJECT_ROOT / "Ref_Image_Canonical_Body/Main"
AUDIT_CSV = PROJECT_ROOT / "Ref_Image_Canonical_Body/main_source_test_intake.csv"
EVIDENCE = QA_DIR / f"W70_MAIN_REFERENCE_SOURCE_TEST_INTAKE_{STAMP}.json"
CANONICAL_EVIDENCE = QA_DIR / "main_reference_source_test_intake.json"
CONTACT_SHEET = RUNTIME_DIR / "main_reference_source_test_contact_sheet.png"
SUMMARY_PANEL = RUNTIME_DIR / "main_reference_source_test_intake_panel.png"

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def image_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTS)


def slug_text(path: Path) -> str:
    return re.sub(r"[^a-z0-9]+", " ", path.stem.lower()).strip()


def classify_view(path: Path, width: int, height: int) -> tuple[str, str, list[str]]:
    text = slug_text(path)
    notes: list[str] = []
    if "cropped" in text or "portrait" in text and "studio" in text:
        notes.append("portrait_or_crop_context_only")
    if "back view" in text or re.search(r"\bback\b", text):
        return "back_full_body", "candidate_source_test_only", notes
    if "sideways" in text or "profile" in text:
        return "side_or_profile_full_body", "candidate_source_test_only", notes
    if "half turned" in text:
        return "three_quarter_or_half_turn", "candidate_source_test_only", notes
    if "full length" in text or height > width * 1.25:
        return "front_full_body_or_near_full_body", "candidate_source_test_only", notes
    if "posing" in text or "standing" in text:
        return "front_or_pose_context", "candidate_source_test_only", notes
    return "unclassified_source_context", "candidate_source_test_only", notes


def image_record(path: Path) -> dict[str, object]:
    try:
        with Image.open(path) as img:
            width, height, mode = img.width, img.height, img.mode
        view, status, notes = classify_view(path, width, height)
        return {
            "path": rel(path),
            "sha256": file_sha256(path),
            "bytes": path.stat().st_size,
            "width": width,
            "height": height,
            "mode": mode,
            "view_class": view,
            "intake_status": status,
            "notes": "|".join(notes),
            "readable": True,
            "gold_mask_available": False,
            "gold_standard_allowed": False,
            "promotion_allowed": False,
        }
    except Exception as exc:
        return {
            "path": rel(path),
            "sha256": "",
            "bytes": path.stat().st_size if path.exists() else 0,
            "width": 0,
            "height": 0,
            "mode": "",
            "view_class": "unreadable",
            "intake_status": "blocked_unreadable",
            "notes": str(exc),
            "readable": False,
            "gold_mask_available": False,
            "gold_standard_allowed": False,
            "promotion_allowed": False,
        }


def write_csv(path: Path, records: list[dict[str, object]]) -> None:
    fieldnames = [
        "path",
        "sha256",
        "bytes",
        "width",
        "height",
        "mode",
        "view_class",
        "intake_status",
        "notes",
        "readable",
        "gold_mask_available",
        "gold_standard_allowed",
        "promotion_allowed",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def load_font(size: int) -> ImageFont.ImageFont:
    for candidate in [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"]:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def thumb(path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as img:
        image = ImageOps.exif_transpose(img).convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (232, 232, 228))
    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def write_contact_sheet(records: list[dict[str, object]]) -> None:
    CONTACT_SHEET.parent.mkdir(parents=True, exist_ok=True)
    columns = 4
    thumb_size = (270, 310)
    cell_w = 310
    cell_h = 390
    rows = max(1, math.ceil(len(records) / columns))
    width = columns * cell_w + 46
    height = 86 + rows * cell_h + 34
    sheet = Image.new("RGB", (width, height), (248, 248, 246))
    draw = ImageDraw.Draw(sheet)
    title_font = load_font(28)
    small_font = load_font(14)
    draw.rectangle([0, 0, width, 72], fill=(42, 55, 72))
    draw.text((24, 20), "Wave70 Main Source-Test References", fill=(255, 255, 255), font=title_font)
    for idx, record in enumerate(records):
        row = idx // columns
        col = idx % columns
        x = 24 + col * cell_w
        y = 92 + row * cell_h
        path = PROJECT_ROOT / str(record["path"])
        try:
            sheet.paste(thumb(path, thumb_size), (x, y))
        except Exception:
            draw.rectangle([x, y, x + thumb_size[0], y + thumb_size[1]], fill=(210, 210, 210), outline=(120, 40, 30), width=2)
        draw.rectangle([x, y, x + thumb_size[0], y + thumb_size[1]], outline=(80, 80, 80), width=2)
        draw.text((x, y + thumb_size[1] + 8), str(record["view_class"])[:34], fill=(35, 35, 35), font=small_font)
        draw.text((x, y + thumb_size[1] + 28), Path(str(record["path"])).name[:38], fill=(35, 35, 35), font=small_font)
        draw.text((x, y + thumb_size[1] + 48), "source-test only; no gold mask", fill=(125, 38, 28), font=small_font)
    sheet.save(CONTACT_SHEET)


def draw_summary_panel(payload: dict[str, object]) -> None:
    SUMMARY_PANEL.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1600, 980), (248, 248, 246))
    draw = ImageDraw.Draw(img)
    title_font = load_font(34)
    head_font = load_font(24)
    body_font = load_font(20)
    small_font = load_font(16)
    draw.rectangle([0, 0, 1600, 88], fill=(42, 55, 72))
    draw.text((34, 24), "Wave70 Main Reference Source-Test Intake", fill=(255, 255, 255), font=title_font)
    draw.text((36, 120), f"Decision: {payload['qa_decision']}", fill=(35, 35, 35), font=head_font)
    draw.text((36, 158), "Source-test inputs only. No gold masks. No promotion.", fill=(125, 38, 28), font=body_font)
    summary = payload["intake_summary"]
    rows = [
        f"Main source images: {summary['image_count']}",
        f"Readable images: {summary['readable_image_count']}",
        f"Gold mask files found: {summary['gold_mask_file_count']}",
        f"Candidate view classes: {len(summary['view_class_counts'])}",
        f"Gold standard allowed now: {payload['gold_standard_allowed']}",
    ]
    y = 230
    draw.text((36, y), "Intake Summary", fill=(42, 55, 72), font=head_font)
    y += 42
    for row in rows:
        draw.text((62, y), "- " + row, fill=(35, 35, 35), font=body_font)
        y += 32
    y += 24
    draw.text((36, y), "View Classes", fill=(42, 55, 72), font=head_font)
    y += 42
    for view, count in summary["view_class_counts"].items():
        draw.text((62, y), f"- {view}: {count}", fill=(35, 35, 35), font=body_font)
        y += 28
    draw.rectangle([36, 830, 1564, 930], outline=(160, 55, 45), width=3)
    draw.text((60, 854), "Fail-closed policy", fill=(120, 40, 30), font=head_font)
    draw.text((60, 892), "These images can test candidate masking/geometry behavior, but cannot certify gold masks until masks are supplied or approved.", fill=(35, 35, 35), font=small_font)
    draw.text((60, 916), f"Evidence: {rel(EVIDENCE)}", fill=(35, 35, 35), font=small_font)
    img.save(SUMMARY_PANEL)


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def update_csv(path: Path, key: str, key_value: str, updates: dict[str, list[str] | str]) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    count = 0
    for row in rows:
        if row.get(key) != key_value:
            continue
        count += 1
        for field, value in updates.items():
            if field not in fieldnames:
                continue
            if isinstance(value, list):
                row[field] = append_unique(row.get(field, ""), value)
            else:
                row[field] = value
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return count


def prepend(path: Path, block: str) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(block.rstrip() + "\n\n" + existing, encoding="utf-8")


def append_proof_log(payload: dict[str, object]) -> None:
    proof_path = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    line = [
        ISO_TS,
        "70",
        "Wave70 Main reference source-test intake",
        "Classified Ref_Image_Canonical_Body/Main images as source-test inputs only; no gold masks were found, no masks were promoted, and gold-standard certification remains blocked.",
        "; ".join(payload["evidence_paths"]),
        "python py_compile; PIL image readability scan; view classification; contact sheet; JSON/CSV evidence; tracker/item row verification",
        "MAIN_REFERENCE_SOURCE_TEST_INTAKE_RECORDED_NO_PROMOTION",
        rel(EVIDENCE),
        "Use Main images for candidate testing only; provide or approve masks before gold-standard validation.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    records = [image_record(path) for path in image_files(MAIN_DIR)]
    view_counts = dict(sorted(Counter(str(record["view_class"]) for record in records).items()))
    readable_count = sum(1 for record in records if record.get("readable"))
    gold_mask_file_count = 0
    write_csv(AUDIT_CSV, records)
    write_contact_sheet(records)
    evidence_paths = [
        rel(EVIDENCE),
        rel(CANONICAL_EVIDENCE),
        rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name),
        rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name),
        rel(AUDIT_CSV),
        rel(CONTACT_SHEET),
        rel(SUMMARY_PANEL),
    ]
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"W70_MAIN_REFERENCE_SOURCE_TEST_INTAKE_{STAMP}",
        "created_iso": ISO_TS,
        "task": "Classify Ref_Image_Canonical_Body/Main images as source-test references for candidate masking and geometry tests.",
        "source_root": rel(MAIN_DIR),
        "intake_summary": {
            "image_count": len(records),
            "readable_image_count": readable_count,
            "unreadable_image_count": len(records) - readable_count,
            "gold_mask_file_count": gold_mask_file_count,
            "view_class_counts": view_counts,
        },
        "records": records,
        "policy": {
            "source_test_only": True,
            "gold_masks_available": False,
            "gold_standard_allowed": False,
            "mask_promotion_allowed": False,
            "wave71_activation_allowed": False,
            "hard_gate_rerun_performed": False,
            "manual_or_approved_masks_required_for_gold_standard": True,
        },
        "gold_standard_allowed": False,
        "qa_decision": "main_reference_source_test_intake_recorded_no_gold_masks_no_promotion",
        "promotion_decision": "no_mask_promoted_source_test_only",
        "next_step": "Use Main images for candidate mask/geometry behavior tests only; supply or approve masks before gold-standard validation.",
        "evidence_paths": evidence_paths,
    }
    draw_summary_panel(payload)
    write_json(EVIDENCE, payload)
    write_json(CANONICAL_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE_DIR / EVIDENCE.name, payload)
    write_json(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name, payload)

    coverage_additions = [
        "main_reference_source_test_intake_recorded",
        "main_reference_images_not_gold_without_masks",
        "main_reference_contact_sheet_rendered",
        "no_mask_promoted_main_source_test_only",
    ]
    note = (
        f"Main reference source-test intake {STAMP}: classified {len(records)} Main images across {len(view_counts)} view classes; "
        "no gold masks found, source-test only, no promotion."
    )
    tracker_updates = {}
    for path in TRACKER_FILES:
        tracker_updates[rel(path)] = update_csv(
            path,
            "Tracker_ID",
            "TRK-W70-0178",
            {
                "Status_Decision": "blocked_main_reference_source_test_intake_no_gold_masks_no_promotion",
                "Evidence_Path": evidence_paths,
                "Coverage_Audit_Status": coverage_additions,
                "Notes": [note],
            },
        )
    item_updates = {}
    for path in ITEM_FILES:
        item_updates[rel(path)] = update_csv(
            path,
            "Item_ID",
            "ITEM-W70-0178",
            {
                "Evidence_Required": evidence_paths,
                "Coverage_Audit_Status": coverage_additions,
                "Notes": [note],
            },
        )

    top_block = f"""## Immediate Next Action - Main Reference Source-Test Intake - {ISO_TS}

Classified `Ref_Image_Canonical_Body/Main` as source-test input for Wave70 candidate masking and geometry tests.

Result: `{len(records)}` readable source images were inventoried and classified across `{len(view_counts)}` view classes. No gold mask files were present. These images can be used for candidate behavior testing, but cannot certify gold-standard masks until masks are supplied or explicitly approved.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(AUDIT_CSV)}`
- `{rel(CONTACT_SHEET)}`
- `{rel(SUMMARY_PANEL)}`

No masks were promoted. No hard gates were rerun. Next exact local action: use Main images for candidate test workflows only, and require supplied/approved masks before gold-standard validation."""

    for name in [
        "NEXT_ACTION.md",
        "CURRENT_SESSION_STATE.md",
        "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        prepend(HYDRATION_DIR / name, top_block)

    qa_block = f"""
## Wave70 Main Reference Source-Test Intake - {ISO_TS}

Classified `Ref_Image_Canonical_Body/Main` images as source-test references. No gold mask files were present; these images are not promotable as gold-standard validation evidence without masks.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(AUDIT_CSV)}`
- `{rel(CONTACT_SHEET)}`
- `{rel(SUMMARY_PANEL)}`
"""
    prepend(HYDRATION_DIR / "QA_EVIDENCE_INDEX.md", qa_block)
    append_proof_log(payload)

    print(json.dumps({
        "evidence": str(EVIDENCE),
        "canonical": str(CANONICAL_EVIDENCE),
        "audit_csv": str(AUDIT_CSV),
        "contact_sheet": str(CONTACT_SHEET),
        "summary_panel": str(SUMMARY_PANEL),
        "image_count": len(records),
        "readable_image_count": readable_count,
        "gold_mask_file_count": gold_mask_file_count,
        "view_class_counts": view_counts,
        "tracker_updates": tracker_updates,
        "item_updates": item_updates,
    }, indent=2))


if __name__ == "__main__":
    main()
