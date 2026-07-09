from __future__ import annotations

import csv
import hashlib
import json
import textwrap
from collections import Counter
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
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_canonical_reference_slot_ledger" / STAMP

REF1_ROOT = PROJECT_ROOT / "Ref_Image_1"
REF1_MAIN = REF1_ROOT / "725de85824bbe45ba4601dd4a7aed698.jpg"
REF1_FULL = REF1_ROOT / "Full"
REF1_KNEES_TO_HEAD = REF1_FULL / "New folder" / "8ead94ca6f2884fb1ae671fee89e8126.jpg"
REF2_ROOT = PROJECT_ROOT / "Ref_Image_2"
REF2_MAIN = REF2_ROOT / "97f30ff4819b8b8206e8ce30f2355800.jpg"

EVIDENCE = QA_DIR / f"W70_CANONICAL_REFERENCE_SLOT_LEDGER_{STAMP}.json"
CANONICAL_EVIDENCE = QA_DIR / "canonical_reference_slot_ledger.json"
LEDGER_CSV = QA_DIR / f"W70_CANONICAL_REFERENCE_SLOT_LEDGER_{STAMP}.csv"
CANONICAL_LEDGER_CSV = QA_DIR / "canonical_reference_slot_ledger.csv"
PANEL = RUNTIME_DIR / "canonical_reference_slot_ledger_panel.png"

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

REQUIRED_SLOTS = [
    "front_full_body_with_masks",
    "left_side_or_profile_full_body",
    "right_side_or_profile_full_body",
    "back_full_body",
    "three_quarter_left_full_body",
    "three_quarter_right_full_body",
    "contact_occlusion_support_case",
]


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
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTS)


def all_reference_images() -> list[Path]:
    files: list[Path] = []
    for root in [REF1_ROOT, REF2_ROOT]:
        files.extend(image_files(root))
    return sorted(files)


def normalized(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix().lower().replace("_", " ").replace("-", " ")


def path_category(path: Path) -> str:
    try:
        parts = path.relative_to(PROJECT_ROOT).parts
    except ValueError:
        return "outside_project"
    if len(parts) <= 1:
        return "root"
    if parts[0] in {"Ref_Image_1", "Ref_Image_2"}:
        return parts[1] if len(parts) > 2 else "root"
    return parts[0]


def classify(path: Path) -> dict[str, str]:
    text = normalized(path)
    if path == REF1_MAIN:
        return {
            "reference_root": "Ref_Image_1",
            "reference_role": "main_composite_partial_top_and_lower_mask_panels",
            "slot_mapping": "front_full_body_with_masks",
            "slot_status": "calibration_context_only",
            "proof_policy": "top_section_partial_body_not_full_body_proof",
            "exclusion_reason": "",
        }
    if path == REF2_MAIN:
        return {
            "reference_root": "Ref_Image_2",
            "reference_role": "main_full_body_reference",
            "slot_mapping": "front_full_body_with_masks",
            "slot_status": "calibration_context_only",
            "proof_policy": "front_full_body_context_not_canonical_authority",
            "exclusion_reason": "",
        }
    if path == REF1_KNEES_TO_HEAD:
        return {
            "reference_root": "Ref_Image_1",
            "reference_role": "near_full_body_knees_to_head_reference",
            "slot_mapping": "front_or_pose_context_only",
            "slot_status": "excluded_for_lower_body_proof",
            "proof_policy": "not_usable_for_feet_toes_ankles_lower_calf_or_support_proof",
            "exclusion_reason": "user_confirmed_knees_to_head_only",
        }
    if REF1_FULL in path.parents and path.parent == REF1_FULL:
        return {
            "reference_root": "Ref_Image_1",
            "reference_role": "full_folder_top_level_body_reference",
            "slot_mapping": "front_full_body_with_masks",
            "slot_status": "calibration_context_only",
            "proof_policy": "full_or_near_full_context_requires_masks_and_model_backed_geometry_before_authority",
            "exclusion_reason": "",
        }
    if "overlay" in text and "ref image 2" in text:
        return {
            "reference_root": "Ref_Image_2",
            "reference_role": "organized_body_part_overlay",
            "slot_mapping": "front_full_body_with_masks",
            "slot_status": "gold_mask_calibration_only",
            "proof_policy": "overlay_calibrates_body_part_target_not_canonical_polygon_authority",
            "exclusion_reason": "",
        }
    if path.suffix.lower() == ".png" and "chatgpt image" in text and "ref image 1" in text:
        return {
            "reference_root": "Ref_Image_1",
            "reference_role": "organized_body_part_gold_mask",
            "slot_mapping": "front_full_body_with_masks",
            "slot_status": "gold_mask_calibration_only",
            "proof_policy": "mask_panel_calibrates_body_part_target_not_canonical_polygon_authority",
            "exclusion_reason": "",
        }
    if REF1_FULL in path.parents:
        return {
            "reference_root": "Ref_Image_1",
            "reference_role": "nested_full_folder_reference_context",
            "slot_mapping": "front_or_pose_context_only",
            "slot_status": "not_promotable_without_slot_manifest",
            "proof_policy": "nested_full_folder_context_requires explicit slot manifest and model-backed geometry",
            "exclusion_reason": "",
        }
    return {
        "reference_root": path.relative_to(PROJECT_ROOT).parts[0],
        "reference_role": "unclassified_reference_context",
        "slot_mapping": "unassigned",
        "slot_status": "not_promotable_without_slot_manifest",
        "proof_policy": "requires explicit slot manifest and model-backed geometry",
        "exclusion_reason": "",
    }


def image_row(path: Path) -> dict[str, object]:
    with Image.open(path) as img:
        width, height, mode = img.width, img.height, img.mode
    classification = classify(path)
    return {
        "path": rel(path),
        "sha256": file_sha256(path),
        "bytes": path.stat().st_size,
        "width": width,
        "height": height,
        "mode": mode,
        "category": path_category(path),
        **classification,
    }


def write_ledger_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "path",
        "sha256",
        "bytes",
        "width",
        "height",
        "mode",
        "category",
        "reference_root",
        "reference_role",
        "slot_mapping",
        "slot_status",
        "proof_policy",
        "exclusion_reason",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def slot_statuses(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    front_count = sum(1 for row in rows if row["slot_mapping"] == "front_full_body_with_masks")
    statuses = []
    for slot in REQUIRED_SLOTS:
        if slot == "front_full_body_with_masks":
            statuses.append(
                {
                    "slot_id": slot,
                    "status": "available_calibration_only",
                    "current_image_count": front_count,
                    "authority_complete": False,
                    "remaining_need": "model-backed canonical geometry stack plus manifest-confirmed masks",
                }
            )
        else:
            statuses.append(
                {
                    "slot_id": slot,
                    "status": "missing_not_proven",
                    "current_image_count": 0,
                    "authority_complete": False,
                    "remaining_need": "full-body reference plus organized masks and model-backed geometry evidence",
                }
            )
    return statuses


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
        "Wave70 canonical reference slot ledger recorded",
        "Recorded per-image Ref_Image_1+2 slot ledger, pinned partial/composite/exclusion policies, and kept body geometry authority fail-closed with no promotion or gate rerun.",
        "; ".join(payload["evidence_paths"]),
        "python py_compile; image inventory hash/dimension scan; CSV ledger generation; JSON validation; panel generation; tracker/item row verification",
        "CANONICAL_REFERENCE_SLOT_LEDGER_RECORDED_NO_PROMOTION",
        rel(EVIDENCE),
        "Use the ledger plus manifest template when adding missing side/profile, back, 3/4, contact/occlusion/support references.",
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


def thumb(img: Image.Image, box: tuple[int, int]) -> Image.Image:
    copy = img.convert("RGB")
    copy.thumbnail(box, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", box, (232, 232, 228))
    x = (box[0] - copy.width) // 2
    y = (box[1] - copy.height) // 2
    canvas.paste(copy, (x, y))
    return canvas


def sample_panel_images(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    wanted_roles = [
        "main_composite_partial_top_and_lower_mask_panels",
        "main_full_body_reference",
        "full_folder_top_level_body_reference",
        "near_full_body_knees_to_head_reference",
        "organized_body_part_gold_mask",
        "organized_body_part_overlay",
    ]
    samples: list[dict[str, object]] = []
    seen_roles: set[str] = set()
    for role in wanted_roles:
        for row in rows:
            if row["reference_role"] == role and role not in seen_roles:
                samples.append(row)
                seen_roles.add(role)
                break
    return samples[:6]


def draw_panel(payload: dict[str, object], rows: list[dict[str, object]]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1800, 1250), (248, 248, 246))
    draw = ImageDraw.Draw(img)
    title_font = load_font(36)
    head_font = load_font(24)
    body_font = load_font(19)
    small_font = load_font(15)

    draw.rectangle([0, 0, 1800, 92], fill=(42, 55, 72))
    draw.text((34, 26), "Wave70 Canonical Reference Slot Ledger", fill=(255, 255, 255), font=title_font)
    draw.text((36, 122), f"Decision: {payload['qa_decision']}", fill=(35, 35, 35), font=head_font)
    draw.text((36, 158), "No masks changed. No promotion. No hard-gate rerun.", fill=(125, 38, 28), font=body_font)

    summary = payload["ledger_summary"]
    summary_lines = [
        f"Images inventoried: {summary['image_count']}",
        f"Ref_Image_1 images: {summary['by_root'].get('Ref_Image_1', 0)}",
        f"Ref_Image_2 images: {summary['by_root'].get('Ref_Image_2', 0)}",
        f"Front/full calibration images: {summary['front_calibration_image_count']}",
        f"Images excluded for lower-body proof: {summary['lower_body_exclusion_count']}",
    ]
    y = 215
    draw.text((36, y), "Inventory Summary", fill=(42, 55, 72), font=head_font)
    y += 38
    for line in summary_lines:
        draw.text((60, y), "- " + line, fill=(35, 35, 35), font=body_font)
        y += 30

    x0, y0 = 36, 430
    draw.text((x0, y0 - 40), "Representative Reference Roles", fill=(42, 55, 72), font=head_font)
    samples = sample_panel_images(rows)
    cell_w = 280
    for idx, row in enumerate(samples):
        x = x0 + idx * cell_w
        path = PROJECT_ROOT / row["path"]
        try:
            with Image.open(path) as source:
                img.paste(thumb(source, (230, 260)), (x, y0))
        except OSError:
            draw.rectangle([x, y0, x + 230, y0 + 260], fill=(220, 220, 220))
        draw.rectangle([x, y0, x + 230, y0 + 260], outline=(90, 90, 90), width=2)
        label = str(row["reference_role"]).replace("_", " ")
        status = str(row["slot_status"]).replace("_", " ")
        text_y = y0 + 272
        for line in textwrap.wrap(label, width=24)[:3]:
            draw.text((x, text_y), line, fill=(35, 35, 35), font=small_font)
            text_y += 19
        draw.text((x, text_y + 4), status, fill=(125, 38, 28), font=small_font)

    y = 825
    draw.text((36, y), "Blocked Required Slots", fill=(42, 55, 72), font=head_font)
    y += 40
    for slot in payload["slot_statuses"]:
        if slot["slot_id"] == "front_full_body_with_masks":
            continue
        line = f"{slot['slot_id']}: {slot['status']}"
        draw.text((62, y), "- " + line, fill=(35, 35, 35), font=body_font)
        y += 29

    draw.rectangle([36, 1120, 1764, 1210], outline=(160, 55, 45), width=3)
    draw.text((60, 1142), "Fail-closed policy", fill=(120, 40, 30), font=head_font)
    draw.text((60, 1180), "Use this ledger to add missing slots; current gold masks remain calibration, not promotion authority.", fill=(35, 35, 35), font=body_font)
    img.save(PANEL)


def main() -> None:
    rows = [image_row(path) for path in all_reference_images()]
    statuses = slot_statuses(rows)
    by_root = Counter(str(row["reference_root"]) for row in rows)
    by_role = Counter(str(row["reference_role"]) for row in rows)
    by_status = Counter(str(row["slot_status"]) for row in rows)
    evidence_paths = [
        rel(EVIDENCE),
        rel(CANONICAL_EVIDENCE),
        rel(LEDGER_CSV),
        rel(CANONICAL_LEDGER_CSV),
        rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name),
        rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name),
        rel(TRACKER_EVIDENCE_DIR / LEDGER_CSV.name),
        rel(TRACKER_EVIDENCE_DIR / CANONICAL_LEDGER_CSV.name),
        rel(PANEL),
    ]
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"W70_CANONICAL_REFERENCE_SLOT_LEDGER_{STAMP}",
        "created_iso": ISO_TS,
        "task": "Record per-image canonical reference slot ledger for Ref_Image_1 and Ref_Image_2.",
        "ledger_paths": {
            "timestamped_csv": rel(LEDGER_CSV),
            "canonical_csv": rel(CANONICAL_LEDGER_CSV),
        },
        "ledger_summary": {
            "image_count": len(rows),
            "by_root": dict(sorted(by_root.items())),
            "by_role": dict(sorted(by_role.items())),
            "by_slot_status": dict(sorted(by_status.items())),
            "front_calibration_image_count": sum(1 for row in rows if row["slot_mapping"] == "front_full_body_with_masks"),
            "lower_body_exclusion_count": sum(1 for row in rows if row["slot_status"] == "excluded_for_lower_body_proof"),
        },
        "slot_statuses": statuses,
        "policies": {
            "ref_image_1_top_section_partial_body_policy_recorded": True,
            "ref_image_1_lower_section_mask_panels_are_calibration_only": True,
            "ref_image_1_full_new_folder_knees_to_head_excluded_for_lower_body_proof": True,
            "ref_image_2_main_reference_included_as_front_full_body_calibration": True,
            "gold_masks_are_not_canonical_polygon_authority": True,
            "wave71_activation_allowed": False,
            "mask_promotion_allowed": False,
        },
        "qa_decision": "canonical_reference_slot_ledger_recorded_missing_slots_no_promotion",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_slot_ledger_only",
        "gate_policy": {
            "hard_gate_rerun_performed": False,
            "reason": "The slot ledger records and classifies existing references only; it does not add a route implementation, canonical polygon, pass-like row, or complete reference package.",
        },
        "next_step": "Use the ledger plus manifest template to add missing side/profile, back, 3/4, and contact/occlusion/support full-body references before rerunning intake validation.",
        "evidence_paths": evidence_paths,
    }

    write_ledger_csv(LEDGER_CSV, rows)
    write_ledger_csv(CANONICAL_LEDGER_CSV, rows)
    write_ledger_csv(TRACKER_EVIDENCE_DIR / LEDGER_CSV.name, rows)
    write_ledger_csv(TRACKER_EVIDENCE_DIR / CANONICAL_LEDGER_CSV.name, rows)
    write_json(EVIDENCE, payload)
    write_json(CANONICAL_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE_DIR / EVIDENCE.name, payload)
    write_json(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name, payload)
    draw_panel(payload, rows)

    evidence_additions = evidence_paths
    coverage_additions = [
        "canonical_reference_slot_ledger_recorded",
        "ref_image_1_top_partial_policy_pinned",
        "knees_to_head_reference_lower_body_exclusion_pinned",
        "no_mask_promoted_slot_ledger_only",
    ]
    note = (
        f"Canonical reference slot ledger {STAMP}: recorded per-image Ref_Image_1+2 ledger with hash, dimensions, role, slot status, "
        "partial composite policy, and knees-to-head lower-body exclusion. No masks changed or promoted; no hard gates rerun."
    )
    tracker_updates = {}
    for path in TRACKER_FILES:
        tracker_updates[rel(path)] = update_csv(
            path,
            "Tracker_ID",
            "TRK-W70-0178",
            {
                "Status_Decision": "blocked_canonical_reference_slot_ledger_recorded_missing_slots_no_promotion",
                "Evidence_Path": evidence_additions,
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
                "Evidence_Required": evidence_additions,
                "Coverage_Audit_Status": coverage_additions,
                "Notes": [note],
            },
        )

    top_block = f"""## Immediate Next Action - Canonical Reference Slot Ledger - {ISO_TS}

Recorded a per-image Wave70 canonical reference slot ledger for Ref_Image_1 and Ref_Image_2.

Result: current references are now classified by role, slot status, dimensions, hash, proof policy, and exclusion reason. Ref_Image_1 main composite is explicitly pinned as partial top-section context plus lower mask panels; Ref_Image_1/Full/New folder/8ead94ca6f2884fb1ae671fee89e8126.jpg is explicitly excluded from feet/toes/ankles/lower-calf/support proof. Ref_Image_2 remains included as front/full-body calibration context.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(LEDGER_CSV)}`
- `{rel(CANONICAL_LEDGER_CSV)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / LEDGER_CSV.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_LEDGER_CSV.name)}`
- `{rel(PANEL)}`

No masks changed or promoted. No hard gates were rerun because this ledger only classifies existing references. Next exact local action: add or integrate missing canonical side/profile, back, 3/4, and contact/occlusion/support references using the manifest template, then rerun intake validation before any promotion or Wave71 activation."""

    for name in [
        "NEXT_ACTION.md",
        "CURRENT_SESSION_STATE.md",
        "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        prepend(HYDRATION_DIR / name, top_block)

    qa_block = f"""
## Wave70 Canonical Reference Slot Ledger - {ISO_TS}

Recorded a per-image reference slot ledger for Ref_Image_1 and Ref_Image_2. The ledger pins the partial top-section policy, the lower-body exclusion for the knees-to-head image, and the current calibration-only status of all existing gold/reference masks. No masks changed or promoted; hard gates were not rerun.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(LEDGER_CSV)}`
- `{rel(CANONICAL_LEDGER_CSV)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / LEDGER_CSV.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_LEDGER_CSV.name)}`
- `{rel(PANEL)}`
"""
    prepend(HYDRATION_DIR / "QA_EVIDENCE_INDEX.md", qa_block)
    append_proof_log(payload)

    print(
        json.dumps(
            {
                "evidence": str(EVIDENCE),
                "canonical": str(CANONICAL_EVIDENCE),
                "ledger_csv": str(LEDGER_CSV),
                "panel": str(PANEL),
                "qa_decision": payload["qa_decision"],
                "image_count": len(rows),
                "slot_statuses": statuses,
                "tracker_updates": tracker_updates,
                "item_updates": item_updates,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
