from __future__ import annotations

import csv
import hashlib
import json
import math
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
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_front_calibration_visual_inventory" / STAMP

FRONT_SLOT = PROJECT_ROOT / "Ref_Image_Canonical_Body/slots/front_full_body_with_masks"
SOURCE_DIR = FRONT_SLOT / "source_images"
MASK_ROOT = FRONT_SLOT / "masks"

EVIDENCE = QA_DIR / f"W70_FRONT_CALIBRATION_VISUAL_INVENTORY_{STAMP}.json"
CANONICAL_EVIDENCE = QA_DIR / "front_calibration_visual_inventory.json"
AUDIT_CSV = PROJECT_ROOT / "Ref_Image_Canonical_Body/front_calibration_visual_inventory.csv"
SOURCE_CONTACT_SHEET = RUNTIME_DIR / "front_calibration_source_contact_sheet.png"
MASK_CONTACT_SHEET = RUNTIME_DIR / "front_calibration_mask_label_contact_sheet.png"
SUMMARY_PANEL = RUNTIME_DIR / "front_calibration_visual_inventory_panel.png"

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
EXPECTED_LABELS = ["hands", "arms", "abdomen", "thigh", "calves", "feet", "hair"]


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def image_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTS)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_font(size: int) -> ImageFont.ImageFont:
    for candidate in [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"]:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def image_record(path: Path, role: str, label: str = "") -> dict[str, object]:
    try:
        with Image.open(path) as img:
            return {
                "path": rel(path),
                "role": role,
                "label": label,
                "sha256": file_sha256(path),
                "bytes": path.stat().st_size,
                "width": img.width,
                "height": img.height,
                "mode": img.mode,
                "readable": True,
            }
    except Exception as exc:
        return {
            "path": rel(path),
            "role": role,
            "label": label,
            "sha256": "",
            "bytes": path.stat().st_size if path.exists() else 0,
            "width": 0,
            "height": 0,
            "mode": "",
            "readable": False,
            "error": str(exc),
        }


def thumb(path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as img:
        image = ImageOps.exif_transpose(img).convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (232, 232, 228))
    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def write_contact_sheet(path: Path, records: list[dict[str, object]], title: str, columns: int, thumb_size: tuple[int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    title_font = load_font(28)
    label_font = load_font(14)
    rows = max(1, math.ceil(len(records) / columns))
    cell_w = thumb_size[0] + 28
    cell_h = thumb_size[1] + 72
    width = max(900, columns * cell_w + 44)
    height = 86 + rows * cell_h + 34
    sheet = Image.new("RGB", (width, height), (248, 248, 246))
    draw = ImageDraw.Draw(sheet)
    draw.rectangle([0, 0, width, 72], fill=(42, 55, 72))
    draw.text((24, 20), title, fill=(255, 255, 255), font=title_font)
    for idx, record in enumerate(records):
        row = idx // columns
        col = idx % columns
        x = 24 + col * cell_w
        y = 92 + row * cell_h
        try:
            image = thumb(PROJECT_ROOT / str(record["path"]), thumb_size)
            sheet.paste(image, (x, y))
        except Exception:
            draw.rectangle([x, y, x + thumb_size[0], y + thumb_size[1]], fill=(210, 210, 210), outline=(120, 40, 30), width=2)
            draw.text((x + 10, y + 10), "unreadable", fill=(120, 40, 30), font=label_font)
        draw.rectangle([x, y, x + thumb_size[0], y + thumb_size[1]], outline=(80, 80, 80), width=2)
        label = str(record.get("label") or record.get("role") or "")
        name = Path(str(record["path"])).name
        draw.text((x, y + thumb_size[1] + 8), label[:28], fill=(35, 35, 35), font=label_font)
        draw.text((x, y + thumb_size[1] + 28), name[:34], fill=(35, 35, 35), font=label_font)
    sheet.save(path)


def write_audit_csv(path: Path, records: list[dict[str, object]]) -> None:
    fieldnames = ["path", "role", "label", "sha256", "bytes", "width", "height", "mode", "readable"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


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
        "Wave70 front calibration visual inventory audit",
        "Rendered source and mask contact sheets for the canonical front calibration slot; all seeded files are readable and remain calibration-only with no promotion.",
        "; ".join(payload["evidence_paths"]),
        "python py_compile; PIL image readability scan; hash/dimension audit CSV; source contact sheet; mask label contact sheet; tracker/item row verification",
        "FRONT_CALIBRATION_VISUAL_INVENTORY_RECORDED_NO_PROMOTION",
        rel(EVIDENCE),
        "Continue fail-closed until missing side/profile, back, 3/4, contact/support references and model-backed geometry authority are available.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def draw_summary_panel(payload: dict[str, object]) -> None:
    SUMMARY_PANEL.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1600, 940), (248, 248, 246))
    draw = ImageDraw.Draw(img)
    title_font = load_font(34)
    head_font = load_font(24)
    body_font = load_font(20)
    small_font = load_font(16)
    draw.rectangle([0, 0, 1600, 88], fill=(42, 55, 72))
    draw.text((34, 24), "Wave70 Front Calibration Visual Inventory", fill=(255, 255, 255), font=title_font)
    draw.text((36, 120), f"Decision: {payload['qa_decision']}", fill=(35, 35, 35), font=head_font)
    draw.text((36, 158), "Visual inventory only. No mask promotion. No hard-gate rerun.", fill=(125, 38, 28), font=body_font)
    summary = payload["visual_inventory_summary"]
    rows = [
        f"Source images: {summary['source_image_count']} readable {summary['readable_source_image_count']}",
        f"Mask images: {summary['mask_image_count']} readable {summary['readable_mask_image_count']}",
        f"Labels present: {summary['labels_present_count']} / {summary['expected_label_count']}",
        f"Unreadable files: {summary['unreadable_file_count']}",
        f"Authority complete: {payload['authority_complete']}",
    ]
    y = 230
    draw.text((36, y), "Audit Summary", fill=(42, 55, 72), font=head_font)
    y += 42
    for row in rows:
        draw.text((62, y), "- " + row, fill=(35, 35, 35), font=body_font)
        y += 32
    y += 24
    draw.text((36, y), "Label Counts", fill=(42, 55, 72), font=head_font)
    y += 42
    for label, count in payload["mask_counts_by_label"].items():
        draw.text((62, y), f"- {label}: {count}", fill=(35, 35, 35), font=body_font)
        y += 28
    draw.rectangle([36, 780, 1564, 880], outline=(160, 55, 45), width=3)
    draw.text((60, 804), "Fail-closed policy", fill=(120, 40, 30), font=head_font)
    draw.text((60, 842), "Readable front calibration files do not prove side/back/contact geometry or canonical polygon authority.", fill=(35, 35, 35), font=small_font)
    draw.text((60, 866), f"Evidence: {rel(EVIDENCE)}", fill=(35, 35, 35), font=small_font)
    img.save(SUMMARY_PANEL)


def main() -> None:
    source_records = [image_record(path, "source") for path in image_files(SOURCE_DIR)]
    mask_records: list[dict[str, object]] = []
    mask_counts_by_label: dict[str, int] = {}
    for label in EXPECTED_LABELS:
        records = [image_record(path, "mask", label) for path in image_files(MASK_ROOT / label)]
        mask_counts_by_label[label] = len(records)
        mask_records.extend(records)
    all_records = [*source_records, *mask_records]
    unreadable = [record for record in all_records if not record.get("readable")]
    labels_present = [label for label, count in mask_counts_by_label.items() if count > 0]

    write_audit_csv(AUDIT_CSV, all_records)
    write_contact_sheet(SOURCE_CONTACT_SHEET, source_records, "Front Calibration Source References", columns=4, thumb_size=(260, 320))
    write_contact_sheet(MASK_CONTACT_SHEET, mask_records, "Front Calibration Mask Labels", columns=6, thumb_size=(190, 220))

    evidence_paths = [
        rel(EVIDENCE),
        rel(CANONICAL_EVIDENCE),
        rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name),
        rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name),
        rel(AUDIT_CSV),
        rel(SOURCE_CONTACT_SHEET),
        rel(MASK_CONTACT_SHEET),
        rel(SUMMARY_PANEL),
    ]
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"W70_FRONT_CALIBRATION_VISUAL_INVENTORY_{STAMP}",
        "created_iso": ISO_TS,
        "task": "Audit visual readability and label inventory for the canonical front calibration slot.",
        "target_slot": "front_full_body_with_masks",
        "source_dir": rel(SOURCE_DIR),
        "mask_root": rel(MASK_ROOT),
        "visual_inventory_summary": {
            "source_image_count": len(source_records),
            "readable_source_image_count": sum(1 for record in source_records if record.get("readable")),
            "mask_image_count": len(mask_records),
            "readable_mask_image_count": sum(1 for record in mask_records if record.get("readable")),
            "expected_label_count": len(EXPECTED_LABELS),
            "labels_present_count": len(labels_present),
            "unreadable_file_count": len(unreadable),
        },
        "mask_counts_by_label": mask_counts_by_label,
        "source_records": source_records,
        "mask_records": mask_records,
        "unreadable_records": unreadable,
        "policy": {
            "visual_inventory_only": True,
            "calibration_only": True,
            "mask_promotion_allowed": False,
            "wave71_activation_allowed": False,
            "hard_gate_rerun_performed": False,
            "front_slot_authority_complete": False,
        },
        "authority_complete": False,
        "qa_decision": "front_calibration_visual_inventory_recorded_no_promotion",
        "promotion_decision": "no_mask_promoted_visual_inventory_only",
        "next_step": "Continue fail-closed until missing side/profile, back, 3/4, contact/support references and model-backed geometry authority are available.",
        "evidence_paths": evidence_paths,
    }
    draw_summary_panel(payload)
    write_json(EVIDENCE, payload)
    write_json(CANONICAL_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE_DIR / EVIDENCE.name, payload)
    write_json(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name, payload)

    coverage_additions = [
        "front_calibration_visual_inventory_recorded",
        "front_calibration_files_readability_audited",
        "front_calibration_contact_sheets_rendered",
        "no_mask_promoted_visual_inventory_only",
    ]
    note = (
        f"Front calibration visual inventory {STAMP}: rendered contact sheets for {len(source_records)} sources and "
        f"{len(mask_records)} masks across {len(labels_present)} labels; unreadable files {len(unreadable)}. No masks promoted."
    )
    tracker_updates = {}
    for path in TRACKER_FILES:
        tracker_updates[rel(path)] = update_csv(
            path,
            "Tracker_ID",
            "TRK-W70-0178",
            {
                "Status_Decision": "blocked_front_calibration_visual_inventory_recorded_no_promotion",
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

    top_block = f"""## Immediate Next Action - Front Calibration Visual Inventory - {ISO_TS}

Recorded a visual inventory audit for the canonical front calibration slot.

Result: rendered contact sheets for `{len(source_records)}` source images and `{len(mask_records)}` front calibration masks across `{len(labels_present)}` expected labels. Unreadable files: `{len(unreadable)}`. This is visual inventory only; no masks were promoted and no hard gates were rerun.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(AUDIT_CSV)}`
- `{rel(SOURCE_CONTACT_SHEET)}`
- `{rel(MASK_CONTACT_SHEET)}`
- `{rel(SUMMARY_PANEL)}`

Next exact local action: continue fail-closed until missing side/profile, back, 3/4, contact/support references and model-backed geometry authority are available."""

    for name in [
        "NEXT_ACTION.md",
        "CURRENT_SESSION_STATE.md",
        "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        prepend(HYDRATION_DIR / name, top_block)

    qa_block = f"""
## Wave70 Front Calibration Visual Inventory - {ISO_TS}

Rendered visual inventory contact sheets for the canonical front calibration slot. This only proves file readability and label inventory; it does not promote masks or satisfy whole-body geometry authority.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(AUDIT_CSV)}`
- `{rel(SOURCE_CONTACT_SHEET)}`
- `{rel(MASK_CONTACT_SHEET)}`
- `{rel(SUMMARY_PANEL)}`
"""
    prepend(HYDRATION_DIR / "QA_EVIDENCE_INDEX.md", qa_block)
    append_proof_log(payload)

    print(
        json.dumps(
            {
                "evidence": str(EVIDENCE),
                "canonical": str(CANONICAL_EVIDENCE),
                "audit_csv": str(AUDIT_CSV),
                "source_contact_sheet": str(SOURCE_CONTACT_SHEET),
                "mask_contact_sheet": str(MASK_CONTACT_SHEET),
                "summary_panel": str(SUMMARY_PANEL),
                "source_image_count": len(source_records),
                "mask_image_count": len(mask_records),
                "labels_present_count": len(labels_present),
                "unreadable_file_count": len(unreadable),
                "tracker_updates": tracker_updates,
                "item_updates": item_updates,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
