from __future__ import annotations

import csv
import hashlib
import json
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
DROPZONE = PROJECT_ROOT / "Ref_Image_Canonical_Body"
MANIFEST_JSON = DROPZONE / "manifest.json"
MANIFEST_CSV = DROPZONE / "manifest.csv"
CHECKLIST_CSV = DROPZONE / "slot_checklist.csv"
AUDIT_CSV = DROPZONE / "slot_file_audit.csv"
TEMPLATE = PROJECT_ROOT / "Plan/Instructions/QA/Templates/WAVE70_CANONICAL_BODY_REFERENCE_PACKAGE_MANIFEST_TEMPLATE.json"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_canonical_reference_dropzone_manifest_sync" / STAMP

EVIDENCE = QA_DIR / f"W70_CANONICAL_REFERENCE_DROPZONE_MANIFEST_SYNC_{STAMP}.json"
CANONICAL_EVIDENCE = QA_DIR / "canonical_reference_dropzone_manifest_sync.json"
PANEL = RUNTIME_DIR / "canonical_reference_dropzone_manifest_sync_panel.png"

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


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def image_file_record(path: Path, slot_id: str, role: str, label: str = "") -> dict[str, object]:
    record: dict[str, object] = {
        "slot_id": slot_id,
        "role": role,
        "label": label,
        "path": rel(path),
        "sha256": file_sha256(path),
        "bytes": path.stat().st_size,
    }
    with Image.open(path) as img:
        record.update({"width": img.width, "height": img.height, "mode": img.mode})
    return record


def parse_labels(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(part).strip() for part in value if str(part).strip()]
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []
    separator = "|" if "|" in text else ","
    return [part.strip() for part in text.split(separator) if part.strip()]


def template_slots() -> list[dict[str, object]]:
    payload = read_json(TEMPLATE)
    rows = payload.get("required_slots", [])
    return [row for row in rows if isinstance(row, dict)]


def slot_source_dir(slot_id: str) -> Path:
    return DROPZONE / "slots" / slot_id / "source_images"


def slot_mask_root(slot_id: str) -> Path:
    return DROPZONE / "slots" / slot_id / "masks"


def scan_slot(slot: dict[str, object]) -> dict[str, object]:
    slot_id = str(slot["slot_id"])
    labels = parse_labels(slot.get("expected_mask_labels"))
    source_files = image_files(slot_source_dir(slot_id))
    mask_records: list[dict[str, object]] = []
    labels_with_files: list[str] = []
    missing_labels: list[str] = []
    for label in labels:
        files = image_files(slot_mask_root(slot_id) / label)
        if files:
            labels_with_files.append(label)
        else:
            missing_labels.append(label)
        for path in files:
            mask_records.append(image_file_record(path, slot_id, "mask", label))
    source_records = [image_file_record(path, slot_id, "source") for path in source_files]
    minimum_source_count = int(slot.get("minimum_source_count", 1))
    minimum_mask_label_count = int(slot.get("minimum_mask_label_count", 1))
    source_pass = len(source_records) >= minimum_source_count
    mask_pass = len(labels_with_files) >= minimum_mask_label_count
    required = bool(slot.get("required"))
    status = "pass_candidate_intake_only" if source_pass and mask_pass else "missing_required_files"
    if not required and status == "missing_required_files":
        status = "optional_missing"
    return {
        "slot_id": slot_id,
        "required": required,
        "source_image_dropzone": rel(slot_source_dir(slot_id)),
        "organized_mask_root": rel(slot_mask_root(slot_id)),
        "expected_mask_labels": labels,
        "minimum_source_count": minimum_source_count,
        "minimum_mask_label_count": minimum_mask_label_count,
        "source_image_count": len(source_records),
        "mask_image_count": len(mask_records),
        "mask_label_count": len(labels_with_files),
        "mask_labels_with_files": labels_with_files,
        "missing_mask_labels": missing_labels,
        "source_pass": source_pass,
        "mask_pass": mask_pass,
        "authority_complete": False,
        "status": status,
        "sample_source_images": [record["path"] for record in source_records[:8]],
        "sample_mask_images": [record["path"] for record in mask_records[:8]],
        "file_records": [*source_records, *mask_records],
    }


def row_for_manifest(slot_state: dict[str, object]) -> dict[str, str]:
    return {
        "slot_id": str(slot_state["slot_id"]),
        "required": str(bool(slot_state["required"])).upper(),
        "source_image_dropzone": str(slot_state["source_image_dropzone"]),
        "organized_mask_root": str(slot_state["organized_mask_root"]),
        "expected_mask_labels": "|".join(str(label) for label in slot_state["expected_mask_labels"]),
        "minimum_source_count": str(slot_state["minimum_source_count"]),
        "minimum_mask_label_count": str(slot_state["minimum_mask_label_count"]),
        "current_status": str(slot_state["status"]),
        "current_image_count": str(slot_state["source_image_count"]),
        "current_mask_image_count": str(slot_state["mask_image_count"]),
        "current_mask_label_count": str(slot_state["mask_label_count"]),
        "missing_mask_labels": "|".join(str(label) for label in slot_state["missing_mask_labels"]),
        "authority_complete": "FALSE",
        "remaining_need": "model-backed canonical geometry stack" if slot_state["status"] == "pass_candidate_intake_only" else "source images and organized masks plus model-backed canonical geometry evidence",
        "notes": "",
    }


def write_manifest_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "slot_id",
        "required",
        "source_image_dropzone",
        "organized_mask_root",
        "expected_mask_labels",
        "minimum_source_count",
        "minimum_mask_label_count",
        "current_status",
        "current_image_count",
        "current_mask_image_count",
        "current_mask_label_count",
        "missing_mask_labels",
        "authority_complete",
        "remaining_need",
        "notes",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_audit_csv(path: Path, records: list[dict[str, object]]) -> None:
    fieldnames = ["slot_id", "role", "label", "path", "sha256", "bytes", "width", "height", "mode"]
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
        "Wave70 canonical reference dropzone manifest sync audit",
        "Synced Ref_Image_Canonical_Body manifest/checklist from actual files, wrote slot file audit, and kept canonical intake fail-closed because required slots still have no real source/mask files.",
        "; ".join(payload["evidence_paths"]),
        "python py_compile; dropzone scan; manifest CSV/JSON rewrite; slot file audit CSV; panel generation; tracker/item row verification",
        "CANONICAL_REFERENCE_DROPZONE_MANIFEST_SYNC_BLOCKED_NO_PROMOTION",
        rel(EVIDENCE),
        "Add real same-character missing view files to the manifest-routed dropzone, rerun sync, then rerun intake validation.",
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
    img = Image.new("RGB", (1700, 1040), (248, 248, 246))
    draw = ImageDraw.Draw(img)
    title_font = load_font(36)
    head_font = load_font(24)
    body_font = load_font(20)
    small_font = load_font(16)

    draw.rectangle([0, 0, 1700, 92], fill=(42, 55, 72))
    draw.text((34, 26), "Wave70 Canonical Reference Dropzone Manifest Sync", fill=(255, 255, 255), font=title_font)
    draw.text((36, 124), f"Decision: {payload['qa_decision']}", fill=(35, 35, 35), font=head_font)
    draw.text((36, 162), "Manifest/checklist synced from filesystem. No masks changed. No promotion.", fill=(125, 38, 28), font=body_font)

    summary = payload["sync_summary"]
    rows = [
        f"Slots scanned: {summary['slot_count']}",
        f"Required slots: {summary['required_slot_count']}",
        f"Required slots with source pass: {summary['required_source_pass_count']}",
        f"Required slots with mask pass: {summary['required_mask_pass_count']}",
        f"Dropzone source images: {summary['source_image_count']}",
        f"Dropzone mask images: {summary['mask_image_count']}",
        f"Required slots blocked: {summary['blocked_required_slot_count']}",
    ]
    y = 225
    draw.text((36, y), "Sync Summary", fill=(42, 55, 72), font=head_font)
    y += 42
    for row in rows:
        draw.text((62, y), "- " + row, fill=(35, 35, 35), font=body_font)
        y += 31

    y += 20
    draw.text((36, y), "Blocked Required Slots", fill=(42, 55, 72), font=head_font)
    y += 42
    for slot in payload["slot_states"]:
        if not slot["required"] or slot["status"] == "pass_candidate_intake_only":
            continue
        draw.text(
            (62, y),
            f"- {slot['slot_id']}: sources {slot['source_image_count']}, mask labels {slot['mask_label_count']}",
            fill=(35, 35, 35),
            font=body_font,
        )
        y += 29

    draw.rectangle([36, 890, 1664, 990], outline=(160, 55, 45), width=3)
    draw.text((60, 914), "Fail-closed policy", fill=(120, 40, 30), font=head_font)
    draw.text((60, 952), "Syncing the manifest is not evidence of body geometry authority; real files and model-backed gates are still required.", fill=(35, 35, 35), font=small_font)
    draw.text((60, 976), f"Evidence: {rel(EVIDENCE)}", fill=(35, 35, 35), font=small_font)
    img.save(PANEL)


def main() -> None:
    slots = template_slots()
    slot_states = [scan_slot(slot) for slot in slots]
    manifest_rows = [row_for_manifest(slot) for slot in slot_states]
    file_records = [record for slot in slot_states for record in slot["file_records"]]

    required = [slot for slot in slot_states if slot["required"]]
    blocked_required = [slot for slot in required if slot["status"] != "pass_candidate_intake_only"]
    source_image_count = sum(int(slot["source_image_count"]) for slot in slot_states)
    mask_image_count = sum(int(slot["mask_image_count"]) for slot in slot_states)

    write_manifest_csv(MANIFEST_CSV, manifest_rows)
    write_manifest_csv(CHECKLIST_CSV, manifest_rows)
    write_audit_csv(AUDIT_CSV, file_records)

    existing_manifest = read_json(MANIFEST_JSON) if MANIFEST_JSON.exists() else {}
    updated_manifest = {
        **existing_manifest,
        "created_at_local": existing_manifest.get("created_at_local", ISO_TS),
        "last_synced_at_local": ISO_TS,
        "package_root": rel(DROPZONE),
        "generated_by": existing_manifest.get("generated_by", "Plan/07_IMPLEMENTATION/scripts/prepare_wave70_canonical_reference_package_dropzone.py"),
        "last_synced_by": rel(Path(__file__)),
        "current_authority_status": "dropzone_manifest_synced_missing_required_files_and_model_backed_geometry",
        "completion_allowed": False,
        "slots": manifest_rows,
        "slot_file_records": file_records,
    }
    write_json(MANIFEST_JSON, updated_manifest)

    evidence_paths = [
        rel(EVIDENCE),
        rel(CANONICAL_EVIDENCE),
        rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name),
        rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name),
        rel(MANIFEST_JSON),
        rel(MANIFEST_CSV),
        rel(CHECKLIST_CSV),
        rel(AUDIT_CSV),
        rel(PANEL),
    ]
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"W70_CANONICAL_REFERENCE_DROPZONE_MANIFEST_SYNC_{STAMP}",
        "created_iso": ISO_TS,
        "task": "Synchronize Wave70 canonical reference dropzone manifest/checklist from actual filesystem files.",
        "dropzone_root": rel(DROPZONE),
        "sync_summary": {
            "slot_count": len(slot_states),
            "required_slot_count": len(required),
            "required_source_pass_count": sum(1 for slot in required if slot["source_pass"]),
            "required_mask_pass_count": sum(1 for slot in required if slot["mask_pass"]),
            "source_image_count": source_image_count,
            "mask_image_count": mask_image_count,
            "file_record_count": len(file_records),
            "blocked_required_slot_count": len(blocked_required),
            "intake_ready_from_dropzone_files": len(blocked_required) == 0,
        },
        "slot_states": [
            {key: value for key, value in slot.items() if key != "file_records"}
            for slot in slot_states
        ],
        "file_records": file_records,
        "policy": {
            "manifest_synced_from_actual_files": True,
            "scaffold_files_ignored_as_evidence": True,
            "mask_promotion_allowed": False,
            "wave71_activation_allowed": False,
            "hard_gate_rerun_allowed": False,
        },
        "gate_policy": {
            "hard_gate_rerun_performed": False,
            "reason": "Manifest sync does not add route implementation, canonical polygons, pass-like rows, or complete model-backed geometry authority.",
        },
        "qa_decision": "canonical_reference_dropzone_manifest_synced_missing_required_files_no_promotion",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_manifest_sync_only",
        "next_step": "Add real same-character source and mask files to the missing manifest-routed slots, rerun this sync, then rerun canonical intake validation.",
        "evidence_paths": evidence_paths,
    }
    write_json(EVIDENCE, payload)
    write_json(CANONICAL_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE_DIR / EVIDENCE.name, payload)
    write_json(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name, payload)
    draw_panel(payload)

    coverage_additions = [
        "canonical_reference_dropzone_manifest_sync_written",
        "canonical_reference_dropzone_actual_file_audit_recorded",
        "no_mask_promoted_manifest_sync_only",
    ]
    note = (
        f"Canonical reference dropzone manifest sync {STAMP}: manifest/checklist rewritten from actual files; "
        f"{source_image_count} source images and {mask_image_count} mask images found in dropzone; required slots remain blocked. No hard gates rerun."
    )
    tracker_updates = {}
    for path in TRACKER_FILES:
        tracker_updates[rel(path)] = update_csv(
            path,
            "Tracker_ID",
            "TRK-W70-0178",
            {
                "Status_Decision": "blocked_canonical_reference_dropzone_manifest_synced_missing_required_files_no_promotion",
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

    top_block = f"""## Immediate Next Action - Canonical Reference Dropzone Manifest Sync - {ISO_TS}

Synced the Wave70 canonical reference dropzone manifest/checklist from actual files in `{rel(DROPZONE)}`.

Result: the dropzone manifest is now filesystem-derived. It found `{source_image_count}` source images and `{mask_image_count}` mask images in the dropzone; required side/profile, back, 3/4, and contact/occlusion/support slots remain missing. `slot_file_audit.csv` was written for hash/dimension proof when real files are added.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(MANIFEST_JSON)}`
- `{rel(MANIFEST_CSV)}`
- `{rel(CHECKLIST_CSV)}`
- `{rel(AUDIT_CSV)}`
- `{rel(PANEL)}`

No masks changed or promoted. No hard gates were rerun because this sync only audits actual dropzone files and does not introduce model-backed geometry authority. Next exact local action: add real same-character source and mask files to the missing manifest-routed slots, rerun this sync, then rerun canonical intake validation."""

    for name in [
        "NEXT_ACTION.md",
        "CURRENT_SESSION_STATE.md",
        "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        prepend(HYDRATION_DIR / name, top_block)

    qa_block = f"""
## Wave70 Canonical Reference Dropzone Manifest Sync - {ISO_TS}

Synced `Ref_Image_Canonical_Body` manifest/checklist from actual filesystem files and wrote `slot_file_audit.csv`. Current dropzone file counts remain insufficient for required slots. No masks changed or promoted; hard gates were not rerun.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(MANIFEST_JSON)}`
- `{rel(MANIFEST_CSV)}`
- `{rel(CHECKLIST_CSV)}`
- `{rel(AUDIT_CSV)}`
- `{rel(PANEL)}`
"""
    prepend(HYDRATION_DIR / "QA_EVIDENCE_INDEX.md", qa_block)
    append_proof_log(payload)

    print(
        json.dumps(
            {
                "evidence": str(EVIDENCE),
                "canonical": str(CANONICAL_EVIDENCE),
                "manifest_json": str(MANIFEST_JSON),
                "manifest_csv": str(MANIFEST_CSV),
                "audit_csv": str(AUDIT_CSV),
                "panel": str(PANEL),
                "qa_decision": payload["qa_decision"],
                "source_image_count": source_image_count,
                "mask_image_count": mask_image_count,
                "blocked_required_slot_count": len(blocked_required),
                "tracker_updates": tracker_updates,
                "item_updates": item_updates,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
