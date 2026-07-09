from __future__ import annotations

import csv
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
TEMPLATE = PROJECT_ROOT / "Plan/Instructions/QA/Templates/WAVE70_CANONICAL_BODY_REFERENCE_PACKAGE_MANIFEST_TEMPLATE.json"
SLOT_LEDGER = QA_DIR / "canonical_reference_slot_ledger.json"
DROPZONE = PROJECT_ROOT / "Ref_Image_Canonical_Body"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_canonical_reference_package_dropzone" / STAMP

EVIDENCE = QA_DIR / f"W70_CANONICAL_REFERENCE_PACKAGE_DROPZONE_{STAMP}.json"
CANONICAL_EVIDENCE = QA_DIR / "canonical_reference_package_dropzone.json"
PANEL = RUNTIME_DIR / "canonical_reference_package_dropzone_panel.png"

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text_if_missing(path: Path, text: str) -> str:
    if path.exists():
        return "already_exists"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return "created"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def slot_root(slot_id: str) -> Path:
    return DROPZONE / "slots" / slot_id


def mask_label_dir(slot_id: str, label: str) -> Path:
    return slot_root(slot_id) / "masks" / label


def source_dir(slot_id: str) -> Path:
    return slot_root(slot_id) / "source_images"


def create_keep(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    keep = path / ".keep"
    if keep.exists():
        return "already_exists"
    keep.write_text("", encoding="utf-8")
    return "created"


def manifest_rows(template: dict[str, object], slot_ledger: dict[str, object]) -> list[dict[str, object]]:
    current_by_slot = {
        row["slot_id"]: row
        for row in slot_ledger.get("slot_statuses", [])
        if isinstance(row, dict) and row.get("slot_id")
    }
    rows: list[dict[str, object]] = []
    for slot in template.get("required_slots", []):
        if not isinstance(slot, dict):
            continue
        slot_id = str(slot["slot_id"])
        current = current_by_slot.get(slot_id, {})
        labels = slot.get("expected_mask_labels", [])
        rows.append(
            {
                "slot_id": slot_id,
                "required": str(bool(slot.get("required"))).upper(),
                "source_image_dropzone": rel(source_dir(slot_id)),
                "organized_mask_root": rel(slot_root(slot_id) / "masks"),
                "expected_mask_labels": "|".join(str(label) for label in labels),
                "minimum_source_count": str(slot.get("minimum_source_count", "")),
                "minimum_mask_label_count": str(slot.get("minimum_mask_label_count", "")),
                "current_status": str(current.get("status", "not_scanned_yet")),
                "current_image_count": str(current.get("current_image_count", 0)),
                "authority_complete": "FALSE",
                "remaining_need": str(current.get("remaining_need", "full-body source plus organized masks and model-backed geometry evidence")),
                "notes": "",
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
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
        "authority_complete",
        "remaining_need",
        "notes",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def slot_readme(slot: dict[str, object]) -> str:
    slot_id = str(slot["slot_id"])
    labels = [str(label) for label in slot.get("expected_mask_labels", [])]
    required = "required" if slot.get("required") else "optional"
    return f"""# {slot_id}

Status: {required}

Place source images for this slot in `source_images/`.

Place organized mask overlays in `masks/<label>/` using the expected labels below:

{chr(10).join(f"- {label}" for label in labels)}

Requirements:
- Source image must show the same character and the required view/case for this slot.
- Full body must be visible for required full-body slots.
- Crops, top-only composites, knees-to-head images, and generated-output stability cannot prove this slot.
- Gold masks are calibration evidence only until model-backed canonical geometry evidence also passes.
"""


def root_readme(rows: list[dict[str, object]]) -> str:
    required_missing = [row["slot_id"] for row in rows if row["required"] == "TRUE" and row["authority_complete"] == "FALSE"]
    return f"""# Wave70 Canonical Body Reference Package

This folder is the local intake dropzone for the Wave70 canonical body reference package.

Generated: {ISO_TS}

Current use:
- Add missing same-character full-body references into the matching `slots/<slot_id>/source_images` folder.
- Add organized body-part masks into the matching `slots/<slot_id>/masks/<label>` folders.
- Update `manifest.csv` or `manifest.json` when new images are added.
- Rerun `Plan/07_IMPLEMENTATION/scripts/validate_wave70_canonical_reference_package_intake.py` after adding a real reference package.

Required slots still not authority-complete:
{chr(10).join(f"- {slot_id}" for slot_id in required_missing)}

Fail-closed policy:
- Do not use Ref_Image_1 top-section partial bodies as proof of full-body slots.
- Do not use `Ref_Image_1/Full/New folder/8ead94ca6f2884fb1ae671fee89e8126.jpg` for feet/toes/ankles/lower-calf/support proof.
- Do not promote masks from this folder until the intake validator and model-backed geometry authority both pass.
"""


def load_font(size: int) -> ImageFont.ImageFont:
    for candidate in [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"]:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def draw_panel(payload: dict[str, object]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1700, 1050), (248, 248, 246))
    draw = ImageDraw.Draw(img)
    title_font = load_font(36)
    head_font = load_font(24)
    body_font = load_font(20)
    small_font = load_font(16)

    draw.rectangle([0, 0, 1700, 92], fill=(42, 55, 72))
    draw.text((34, 26), "Wave70 Canonical Reference Package Dropzone", fill=(255, 255, 255), font=title_font)
    draw.text((36, 124), f"Decision: {payload['qa_decision']}", fill=(35, 35, 35), font=head_font)
    draw.text((36, 162), "Scaffold only. No masks changed. No promotion. No hard-gate rerun.", fill=(125, 38, 28), font=body_font)

    summary = payload["dropzone_summary"]
    rows = [
        f"Package root: {payload['dropzone_root']}",
        f"Slots scaffolded: {summary['slot_count']}",
        f"Required slots scaffolded: {summary['required_slot_count']}",
        f"Mask label folders scaffolded: {summary['mask_label_folder_count']}",
        f"Manifest CSV: {payload['dropzone_files']['manifest_csv']}",
        f"Manifest JSON: {payload['dropzone_files']['manifest_json']}",
    ]
    y = 230
    draw.text((36, y), "Created Structure", fill=(42, 55, 72), font=head_font)
    y += 42
    for row in rows:
        draw.text((62, y), "- " + row, fill=(35, 35, 35), font=body_font)
        y += 31

    y += 24
    draw.text((36, y), "Required Slots Still Awaiting Real References", fill=(42, 55, 72), font=head_font)
    y += 42
    for slot in payload["required_slots"]:
        draw.text((62, y), f"- {slot['slot_id']}: {slot['current_status']}", fill=(35, 35, 35), font=body_font)
        y += 29

    draw.rectangle([36, 880, 1664, 990], outline=(160, 55, 45), width=3)
    draw.text((60, 904), "Fail-closed policy", fill=(120, 40, 30), font=head_font)
    draw.text((60, 944), "The scaffold makes intake easier; it does not satisfy any missing view or model-backed geometry gate.", fill=(35, 35, 35), font=small_font)
    draw.text((60, 970), f"Evidence: {rel(EVIDENCE)}", fill=(35, 35, 35), font=small_font)
    img.save(PANEL)


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
        "Wave70 canonical reference package dropzone scaffolded",
        "Created Ref_Image_Canonical_Body dropzone with per-slot source and mask folders, manifest CSV/JSON, README, and fail-closed evidence; no masks changed or promoted.",
        "; ".join(payload["evidence_paths"]),
        "python py_compile; dropzone folder verification; manifest CSV/JSON validation; panel generation; tracker/item row verification",
        "CANONICAL_REFERENCE_PACKAGE_DROPZONE_SCAFFOLDED_NO_PROMOTION",
        rel(EVIDENCE),
        "Place real missing same-character side/profile, back, 3/4, and contact/support references in the scaffold, then rerun intake validation.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def main() -> None:
    template = read_json(TEMPLATE)
    slot_ledger = read_json(SLOT_LEDGER)
    rows = manifest_rows(template, slot_ledger)
    slots = [slot for slot in template.get("required_slots", []) if isinstance(slot, dict)]
    created_dirs: list[str] = []
    file_status: dict[str, str] = {}

    for slot in slots:
        slot_id = str(slot["slot_id"])
        created_dirs.append(rel(source_dir(slot_id)))
        create_keep(source_dir(slot_id))
        created_dirs.append(rel(slot_root(slot_id) / "masks"))
        create_keep(slot_root(slot_id) / "masks")
        for label in slot.get("expected_mask_labels", []):
            label_dir = mask_label_dir(slot_id, str(label))
            created_dirs.append(rel(label_dir))
            create_keep(label_dir)
        file_status[rel(slot_root(slot_id) / "README.md")] = write_text_if_missing(
            slot_root(slot_id) / "README.md",
            slot_readme(slot),
        )

    manifest_payload = {
        **template,
        "created_at_local": ISO_TS,
        "package_root": rel(DROPZONE),
        "generated_by": rel(Path(__file__)),
        "current_authority_status": "scaffold_only_missing_required_references_and_model_backed_geometry",
        "completion_allowed": False,
        "slots": rows,
    }
    manifest_json = DROPZONE / "manifest.json"
    manifest_csv = DROPZONE / "manifest.csv"
    checklist_csv = DROPZONE / "slot_checklist.csv"
    readme = DROPZONE / "README.md"
    write_json(manifest_json, manifest_payload)
    write_csv(manifest_csv, rows)
    write_csv(checklist_csv, rows)
    write_text(readme, root_readme(rows))

    required_rows = [row for row in rows if row["required"] == "TRUE"]
    label_folder_count = sum(len(str(row["expected_mask_labels"]).split("|")) for row in rows if row["expected_mask_labels"])
    evidence_paths = [
        rel(EVIDENCE),
        rel(CANONICAL_EVIDENCE),
        rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name),
        rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name),
        rel(manifest_json),
        rel(manifest_csv),
        rel(checklist_csv),
        rel(readme),
        rel(PANEL),
    ]
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"W70_CANONICAL_REFERENCE_PACKAGE_DROPZONE_{STAMP}",
        "created_iso": ISO_TS,
        "task": "Create a local canonical body reference package dropzone aligned with the Wave70 intake manifest template.",
        "dropzone_root": rel(DROPZONE),
        "dropzone_files": {
            "manifest_json": rel(manifest_json),
            "manifest_csv": rel(manifest_csv),
            "slot_checklist_csv": rel(checklist_csv),
            "readme": rel(readme),
        },
        "dropzone_summary": {
            "slot_count": len(rows),
            "required_slot_count": len(required_rows),
            "mask_label_folder_count": label_folder_count,
            "directory_count": len(set(created_dirs)),
            "created_or_verified_directory_count": len(set(created_dirs)),
        },
        "required_slots": required_rows,
        "file_status": file_status,
        "policy": {
            "scaffold_only": True,
            "new_reference_images_added": False,
            "new_route_implementation_added": False,
            "mask_promotion_allowed": False,
            "wave71_activation_allowed": False,
            "ref_image_1_top_partial_context_only": True,
            "knees_to_head_reference_excluded_for_lower_body_proof": True,
        },
        "gate_policy": {
            "hard_gate_rerun_performed": False,
            "reason": "The dropzone scaffold creates folders and manifests only; it does not add real references, route implementation, canonical polygons, pass-like rows, or a complete reference package.",
        },
        "qa_decision": "canonical_reference_package_dropzone_scaffolded_missing_references_no_promotion",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_dropzone_only",
        "next_step": "Place real missing same-character side/profile, back, 3/4, and contact/occlusion/support references in the scaffold, then rerun canonical reference package intake validation.",
        "evidence_paths": evidence_paths,
    }
    write_json(EVIDENCE, payload)
    write_json(CANONICAL_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE_DIR / EVIDENCE.name, payload)
    write_json(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name, payload)
    draw_panel(payload)

    coverage_additions = [
        "canonical_reference_package_dropzone_scaffolded",
        "manifest_aligned_reference_slot_dropzone_ready",
        "no_mask_promoted_dropzone_only",
    ]
    note = (
        f"Canonical reference package dropzone {STAMP}: created Ref_Image_Canonical_Body slot scaffold, manifest CSV/JSON, "
        "slot checklist, and README aligned to intake template. No real missing references added, no masks promoted, no hard gates rerun."
    )
    tracker_updates = {}
    for path in TRACKER_FILES:
        tracker_updates[rel(path)] = update_csv(
            path,
            "Tracker_ID",
            "TRK-W70-0178",
            {
                "Status_Decision": "blocked_canonical_reference_package_dropzone_scaffolded_missing_references_no_promotion",
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

    top_block = f"""## Immediate Next Action - Canonical Reference Package Dropzone - {ISO_TS}

Created the Wave70 canonical body reference package dropzone at `{rel(DROPZONE)}`.

The scaffold contains per-slot source-image folders, organized mask-label folders, `manifest.json`, `manifest.csv`, `slot_checklist.csv`, and a package README aligned to `Plan/Instructions/QA/Templates/WAVE70_CANONICAL_BODY_REFERENCE_PACKAGE_MANIFEST_TEMPLATE.json`.

This is scaffold-only progress: no new real side/profile, back, 3/4, or contact/occlusion/support references were added; no masks changed or promoted; no hard gates were rerun. Ref_Image_1 top partial-body context and the knees-to-head lower-body exclusion remain pinned.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(manifest_json)}`
- `{rel(manifest_csv)}`
- `{rel(checklist_csv)}`
- `{rel(readme)}`
- `{rel(PANEL)}`

Next exact local action: place real missing same-character side/profile, back, 3/4, and contact/occlusion/support references into the scaffold, update the manifest rows, then rerun canonical reference package intake validation before any Wave70 promotion gate rerun or Wave71 activation."""

    for name in [
        "NEXT_ACTION.md",
        "CURRENT_SESSION_STATE.md",
        "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        prepend(HYDRATION_DIR / name, top_block)

    qa_block = f"""
## Wave70 Canonical Reference Package Dropzone - {ISO_TS}

Created the local canonical reference package scaffold at `{rel(DROPZONE)}` with per-slot source folders, mask-label folders, manifest CSV/JSON, slot checklist, and README. This did not add real references, promote masks, or rerun hard gates.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(manifest_json)}`
- `{rel(manifest_csv)}`
- `{rel(checklist_csv)}`
- `{rel(readme)}`
- `{rel(PANEL)}`
"""
    prepend(HYDRATION_DIR / "QA_EVIDENCE_INDEX.md", qa_block)
    append_proof_log(payload)

    print(
        json.dumps(
            {
                "evidence": str(EVIDENCE),
                "canonical": str(CANONICAL_EVIDENCE),
                "dropzone": str(DROPZONE),
                "manifest_json": str(manifest_json),
                "manifest_csv": str(manifest_csv),
                "panel": str(PANEL),
                "qa_decision": payload["qa_decision"],
                "slot_count": len(rows),
                "required_slot_count": len(required_rows),
                "mask_label_folder_count": label_folder_count,
                "tracker_updates": tracker_updates,
                "item_updates": item_updates,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
