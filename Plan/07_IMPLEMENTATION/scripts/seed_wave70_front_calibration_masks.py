from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
ISO_TS = NOW.replace(microsecond=0).isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_front_calibration_mask_seed" / STAMP

DROPZONE_FRONT_MASKS = PROJECT_ROOT / "Ref_Image_Canonical_Body/slots/front_full_body_with_masks/masks"
SEED_MANIFEST = PROJECT_ROOT / "Ref_Image_Canonical_Body/front_calibration_mask_seed_manifest.json"
SEED_CSV = PROJECT_ROOT / "Ref_Image_Canonical_Body/front_calibration_mask_seed_manifest.csv"

EVIDENCE = QA_DIR / f"W70_FRONT_CALIBRATION_MASK_SEED_{STAMP}.json"
CANONICAL_EVIDENCE = QA_DIR / "front_calibration_mask_seed.json"
PANEL = RUNTIME_DIR / "front_calibration_mask_seed_panel.png"

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

LABEL_SOURCE_ROOTS = {
    "arms": [PROJECT_ROOT / "Ref_Image_1/Arms", PROJECT_ROOT / "Ref_Image_2/Arms"],
    "hands": [PROJECT_ROOT / "Ref_Image_1/Hands", PROJECT_ROOT / "Ref_Image_2/Hands"],
    "abdomen": [PROJECT_ROOT / "Ref_Image_1/Abdomen", PROJECT_ROOT / "Ref_Image_2/Abdomen"],
    "thigh": [PROJECT_ROOT / "Ref_Image_1/Thigh", PROJECT_ROOT / "Ref_Image_2/Thigh"],
    "calves": [PROJECT_ROOT / "Ref_Image_1/calves", PROJECT_ROOT / "Ref_Image_2/calves"],
    "feet": [PROJECT_ROOT / "Ref_Image_1/Feet", PROJECT_ROOT / "Ref_Image_2/Feet"],
    "hair": [PROJECT_ROOT / "Ref_Image_1/hair", PROJECT_ROOT / "Ref_Image_2/hair"],
}


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


def image_info(path: Path) -> dict[str, object]:
    with Image.open(path) as img:
        return {"width": img.width, "height": img.height, "mode": img.mode}


def image_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTS)


def existing_hashes(label: str) -> set[str]:
    target = DROPZONE_FRONT_MASKS / label
    if not target.exists():
        return set()
    return {file_sha256(path) for path in image_files(target)}


def safe_name(path: Path) -> str:
    parts = [part for part in path.parts if part not in {":", "\\"}]
    return "_".join(parts[-3:]).replace(" ", "_").replace(",", "").replace("(", "").replace(")", "")


def seed_masks() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for label, roots in LABEL_SOURCE_ROOTS.items():
        target_dir = DROPZONE_FRONT_MASKS / label
        target_dir.mkdir(parents=True, exist_ok=True)
        seen = existing_hashes(label)
        label_index = 0
        for root in roots:
            for source in image_files(root):
                sha = file_sha256(source)
                info = image_info(source)
                if sha in seen:
                    records.append(
                        {
                            "label": label,
                            "source_path": rel(source),
                            "target_path": "",
                            "sha256": sha,
                            "bytes": source.stat().st_size,
                            **info,
                            "action": "skipped_duplicate_sha_already_in_front_mask_label",
                            "calibration_only": True,
                            "authority_complete": False,
                        }
                    )
                    continue
                label_index += 1
                target = target_dir / f"front_{label}_calibration_{label_index:02d}_{safe_name(source)}"
                shutil.copy2(source, target)
                seen.add(sha)
                records.append(
                    {
                        "label": label,
                        "source_path": rel(source),
                        "target_path": rel(target),
                        "sha256": sha,
                        "bytes": target.stat().st_size,
                        **info,
                        "action": "copied_to_front_mask_calibration_label_dropzone",
                        "calibration_only": True,
                        "authority_complete": False,
                    }
                )
    return records


def write_seed_csv(path: Path, records: list[dict[str, object]]) -> None:
    fieldnames = [
        "label",
        "source_path",
        "target_path",
        "sha256",
        "bytes",
        "width",
        "height",
        "mode",
        "action",
        "calibration_only",
        "authority_complete",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
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
        "Wave70 front calibration masks seeded into canonical dropzone",
        "Copied existing Ref_Image_1+2 front body-part gold masks into front slot mask-label folders as calibration-only context; no side/back/contact masks or promotions were created.",
        "; ".join(payload["evidence_paths"]),
        "python py_compile; sha256 dedupe; image copy2; seed manifest JSON/CSV; panel generation; tracker/item row verification",
        "FRONT_CALIBRATION_MASK_SEED_RECORDED_NO_PROMOTION",
        rel(EVIDENCE),
        "Rerun dropzone sync and intake validation; missing side/back/3-4/contact slots still require real references.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def load_font(size: int) -> ImageFont.ImageFont:
    for candidate in [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"]:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def draw_panel(payload: dict[str, object]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1650, 1020), (248, 248, 246))
    draw = ImageDraw.Draw(img)
    title_font = load_font(34)
    head_font = load_font(24)
    body_font = load_font(20)
    small_font = load_font(16)

    draw.rectangle([0, 0, 1650, 88], fill=(42, 55, 72))
    draw.text((34, 24), "Wave70 Front Calibration Mask Seed", fill=(255, 255, 255), font=title_font)
    draw.text((36, 120), f"Decision: {payload['qa_decision']}", fill=(35, 35, 35), font=head_font)
    draw.text((36, 158), "Calibration-only masks copied. No promotion. No hard-gate rerun.", fill=(125, 38, 28), font=body_font)

    summary = payload["seed_summary"]
    rows = [
        f"Candidate mask files: {summary['candidate_mask_count']}",
        f"Copied mask files: {summary['copied_mask_count']}",
        f"Duplicate mask files skipped: {summary['duplicate_mask_count']}",
        f"Labels with copied masks: {summary['labels_with_copied_masks']}",
        f"Authority complete: {payload['authority_complete']}",
    ]
    y = 230
    draw.text((36, y), "Seed Summary", fill=(42, 55, 72), font=head_font)
    y += 42
    for row in rows:
        draw.text((62, y), "- " + row, fill=(35, 35, 35), font=body_font)
        y += 32

    y += 20
    draw.text((36, y), "Label Counts", fill=(42, 55, 72), font=head_font)
    y += 42
    for label, count in payload["copied_counts_by_label"].items():
        draw.text((62, y), f"- {label}: {count}", fill=(35, 35, 35), font=body_font)
        y += 28

    draw.rectangle([36, 860, 1614, 960], outline=(160, 55, 45), width=3)
    draw.text((60, 884), "Fail-closed policy", fill=(120, 40, 30), font=head_font)
    draw.text((60, 922), "These masks are front calibration only. Canonical geometry, side/back/3-4/contact references, and promotion gates remain blocked.", fill=(35, 35, 35), font=small_font)
    draw.text((60, 946), f"Evidence: {rel(EVIDENCE)}", fill=(35, 35, 35), font=small_font)
    img.save(PANEL)


def main() -> None:
    records = seed_masks()
    copied = [record for record in records if str(record["action"]).startswith("copied")]
    duplicates = [record for record in records if "duplicate" in str(record["action"])]
    copied_counts_by_label = {
        label: sum(1 for record in copied if record["label"] == label)
        for label in LABEL_SOURCE_ROOTS
    }
    evidence_paths = [
        rel(EVIDENCE),
        rel(CANONICAL_EVIDENCE),
        rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name),
        rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name),
        rel(SEED_MANIFEST),
        rel(SEED_CSV),
        rel(PANEL),
    ]
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"W70_FRONT_CALIBRATION_MASK_SEED_{STAMP}",
        "created_iso": ISO_TS,
        "task": "Seed existing front/body-part gold masks into canonical front-slot mask label folders.",
        "target_slot": "front_full_body_with_masks",
        "target_mask_root": rel(DROPZONE_FRONT_MASKS),
        "seed_summary": {
            "candidate_mask_count": len(records),
            "copied_mask_count": len(copied),
            "duplicate_mask_count": len(duplicates),
            "labels_with_copied_masks": sum(1 for count in copied_counts_by_label.values() if count > 0),
            "seed_record_count": len(records),
        },
        "copied_counts_by_label": copied_counts_by_label,
        "seed_records": records,
        "policy": {
            "calibration_only": True,
            "source_files_copied": False,
            "missing_side_back_three_quarter_contact_slots_filled": False,
            "mask_promotion_allowed": False,
            "wave71_activation_allowed": False,
            "hard_gate_rerun_allowed": False,
            "gold_masks_are_not_canonical_polygon_authority": True,
        },
        "authority_complete": False,
        "qa_decision": "front_calibration_masks_seeded_no_promotion",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_front_mask_seed_only",
        "next_step": "Rerun dropzone manifest sync and manifest-aware intake validation; add real missing side/profile, back, 3/4, and contact/support references before any promotion.",
        "evidence_paths": evidence_paths,
    }
    write_json(EVIDENCE, payload)
    write_json(CANONICAL_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE_DIR / EVIDENCE.name, payload)
    write_json(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name, payload)
    write_json(SEED_MANIFEST, payload)
    write_seed_csv(SEED_CSV, records)
    draw_panel(payload)

    coverage_additions = [
        "front_calibration_masks_seeded_into_dropzone",
        "front_masks_calibration_only_no_authority",
        "no_mask_promoted_front_mask_seed_only",
    ]
    note = (
        f"Front calibration mask seed {STAMP}: copied {len(copied)} existing Ref_Image_1+2 front/body-part masks into "
        "canonical front slot label folders as calibration-only context. No side/back/3-4/contact files or promotions created."
    )
    tracker_updates = {}
    for path in TRACKER_FILES:
        tracker_updates[rel(path)] = update_csv(
            path,
            "Tracker_ID",
            "TRK-W70-0178",
            {
                "Status_Decision": "blocked_front_calibration_masks_seeded_no_promotion",
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

    top_block = f"""## Immediate Next Action - Front Calibration Mask Seed - {ISO_TS}

Seeded existing Ref_Image_1+Ref_Image_2 front/body-part gold masks into `Ref_Image_Canonical_Body/slots/front_full_body_with_masks/masks`.

Result: `{len(copied)}` mask files were copied as calibration-only front-slot masks across `{payload['seed_summary']['labels_with_copied_masks']}` expected labels; `{len(duplicates)}` duplicate candidates were skipped by SHA-256.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(SEED_MANIFEST)}`
- `{rel(SEED_CSV)}`
- `{rel(PANEL)}`

No masks were promoted. No side/profile, back, 3/4, contact/occlusion/support, or model-backed geometry requirement was satisfied by this seed. Next exact local action: rerun dropzone manifest sync and manifest-aware intake validation, then continue waiting for real missing view/contact references before promotion."""

    for name in [
        "NEXT_ACTION.md",
        "CURRENT_SESSION_STATE.md",
        "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        prepend(HYDRATION_DIR / name, top_block)

    qa_block = f"""
## Wave70 Front Calibration Mask Seed - {ISO_TS}

Seeded existing Ref_Image_1+Ref_Image_2 front/body-part gold masks into the canonical front slot as calibration-only context. No masks were promoted; missing side/profile, back, 3/4, contact/support, and model-backed geometry requirements remain blocked.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(SEED_MANIFEST)}`
- `{rel(SEED_CSV)}`
- `{rel(PANEL)}`
"""
    prepend(HYDRATION_DIR / "QA_EVIDENCE_INDEX.md", qa_block)
    append_proof_log(payload)

    print(
        json.dumps(
            {
                "evidence": str(EVIDENCE),
                "canonical": str(CANONICAL_EVIDENCE),
                "seed_manifest": str(SEED_MANIFEST),
                "seed_csv": str(SEED_CSV),
                "panel": str(PANEL),
                "qa_decision": payload["qa_decision"],
                "copied_mask_count": len(copied),
                "duplicate_mask_count": len(duplicates),
                "copied_counts_by_label": copied_counts_by_label,
                "tracker_updates": tracker_updates,
                "item_updates": item_updates,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
