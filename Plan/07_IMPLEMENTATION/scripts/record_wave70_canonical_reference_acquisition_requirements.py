from __future__ import annotations

import csv
import json
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
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_canonical_reference_acquisition_requirements" / STAMP

REF1_ROOT = PROJECT_ROOT / "Ref_Image_1"
REF1_MAIN = REF1_ROOT / "725de85824bbe45ba4601dd4a7aed698.jpg"
REF1_FULL = REF1_ROOT / "Full"
REF1_KNEES_TO_HEAD = REF1_FULL / "New folder" / "8ead94ca6f2884fb1ae671fee89e8126.jpg"
REF2_ROOT = PROJECT_ROOT / "Ref_Image_2"
REF2_MAIN = REF2_ROOT / "97f30ff4819b8b8206e8ce30f2355800.jpg"
REF2_MANIFEST = REF2_ROOT / "manifest.csv"

SOURCE_EVIDENCE = {
    "canonical_body_geometry_prerequisite_gap": QA_DIR / "canonical_body_geometry_prerequisite_gap.json",
    "body_reference_matrix": QA_DIR / "body_reference_matrix.json",
    "ref_image_1_full_body_references": QA_DIR / "ref_image_1_full_body_references.json",
    "ref_image_1_body_mask_gold_standard": QA_DIR / "ref_image_1_body_mask_gold_standard.json",
    "ref_image_2_body_reference": QA_DIR / "ref_image_2_body_reference.json",
    "available_route_runtime_validation_alignment": QA_DIR / "available_route_runtime_validation_alignment.json",
    "whole_body_geometry_promotion_integration": QA_DIR / "whole_body_geometry_promotion_integration.json",
    "feet_toes_reentry_post_gates": QA_DIR / "feet_toes_reentry_post_gates.json",
}

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]

EVIDENCE = QA_DIR / f"W70_CANONICAL_REFERENCE_ACQUISITION_REQUIREMENTS_{STAMP}.json"
CANONICAL_EVIDENCE = QA_DIR / "canonical_reference_acquisition_requirements.json"
PANEL = RUNTIME_DIR / "canonical_reference_acquisition_requirements_panel.png"


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def image_info(path: Path) -> dict[str, object]:
    info: dict[str, object] = {
        "path": rel(path),
        "exists": path.exists(),
    }
    if not path.exists():
        return info
    with Image.open(path) as img:
        info.update({"width": img.width, "height": img.height, "mode": img.mode})
    info["bytes"] = path.stat().st_size
    return info


def image_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    exts = {".jpg", ".jpeg", ".png"}
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in exts)


def top_level_full_refs() -> list[Path]:
    if not REF1_FULL.exists():
        return []
    return sorted(path for path in REF1_FULL.glob("*") if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png"})


def category_counts(root: Path) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for path in image_files(root):
        if path == REF1_MAIN or path == REF2_MAIN:
            continue
        rel_parts = path.relative_to(root).parts
        if not rel_parts:
            continue
        if rel_parts[0].lower() in {"full", "face"} and len(rel_parts) > 1:
            counts[rel_parts[0]] += 1
        elif rel_parts[0].lower() not in {"readme.txt", "manifest.csv"}:
            counts[rel_parts[0]] += 1
    return dict(sorted(counts.items()))


def manifest_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def source_summary() -> dict[str, object]:
    ref1_full_top = top_level_full_refs()
    ref1_full_all = image_files(REF1_FULL)
    ref1_gold = [p for p in image_files(REF1_ROOT) if REF1_FULL not in p.parents and p != REF1_MAIN]
    ref2_images = image_files(REF2_ROOT)
    ref2_overlays = [p for p in ref2_images if p != REF2_MAIN and "_overlay" in p.name]
    return {
        "ref_image_1": {
            "main_reference": image_info(REF1_MAIN),
            "main_reference_layout_policy": "Top section has partial one-third-body images; lower section contains the full body-part mask panels. Top section is not used as proof that all body parts are masked.",
            "full_folder_top_level_image_count": len(ref1_full_top),
            "full_folder_recursive_image_count": len(ref1_full_all),
            "full_folder_top_level_images": [rel(path) for path in ref1_full_top],
            "excluded_knees_to_head_reference": {
                **image_info(REF1_KNEES_TO_HEAD),
                "exclusion_policy": "Exclude from feet/toes/ankles/lower-calf/support proof because user identified it as knees-to-head only.",
            },
            "organized_gold_mask_image_count": len(ref1_gold),
            "organized_gold_mask_category_counts": category_counts(REF1_ROOT),
        },
        "ref_image_2": {
            "main_reference": image_info(REF2_MAIN),
            "manifest_path": rel(REF2_MANIFEST) if REF2_MANIFEST.exists() else "",
            "manifest_row_count": manifest_count(REF2_MANIFEST),
            "overlay_image_count": len(ref2_overlays),
            "organized_overlay_category_counts": category_counts(REF2_ROOT),
        },
    }


def evidence_summary() -> dict[str, object]:
    summary: dict[str, object] = {}
    for key, path in SOURCE_EVIDENCE.items():
        if path.exists():
            payload = read_json(path)
            summary[key] = {
                "path": rel(path),
                "evidence_id": payload.get("evidence_id"),
                "qa_decision": payload.get("qa_decision"),
                "decision": payload.get("decision"),
                "next_active_row": payload.get("next_active_row"),
            }
        else:
            summary[key] = {"path": rel(path), "exists": False}
    return summary


def requirement_matrix() -> list[dict[str, object]]:
    return [
        {
            "requirement_id": "front_full_body_with_masks",
            "current_status": "available_calibration_only",
            "current_evidence": "Ref_Image_1 and Ref_Image_2 provide front/full-body and organized mask context.",
            "missing_for_authority": "Model-backed canonical pose/human parsing/contact/canonical polygons still missing.",
        },
        {
            "requirement_id": "left_side_or_profile_full_body",
            "current_status": "missing_not_proven",
            "needed": "Full body left side or near-profile source, head through feet visible, with organized body-part masks.",
        },
        {
            "requirement_id": "right_side_or_profile_full_body",
            "current_status": "missing_not_proven",
            "needed": "Full body right side or near-profile source, head through feet visible, with organized body-part masks.",
        },
        {
            "requirement_id": "back_full_body",
            "current_status": "missing_not_proven",
            "needed": "Back-view full body source and masks for hair, back, shoulders, arms, glutes, thighs, calves, and feet.",
        },
        {
            "requirement_id": "three_quarter_left_and_right",
            "current_status": "missing_not_proven",
            "needed": "3/4 left and 3/4 right full-body sources to validate side transitions, limb overlap, and protected neighbors.",
        },
        {
            "requirement_id": "contact_occlusion_support_case",
            "current_status": "missing_not_proven",
            "needed": "Full-body case with hand-over-body, limb-over-limb, object/support surface, floor contact, or similar owner/contact boundaries.",
        },
        {
            "requirement_id": "multi_person_owner_separation_case",
            "current_status": "required_for_multi_character_contact_generalization",
            "needed": "At least one multi-person or clear owner-separation case with masks if multi-character/contact scopes remain in certification scope.",
        },
        {
            "requirement_id": "model_backed_canonical_geometry_stack",
            "current_status": "blocked_locally",
            "needed": "Pose, hand, human-part parsing, person-instance segmentation, promptable refinement, contact ownership, canonical polygon export, and coordinate transform evidence.",
        },
    ]


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
        "Wave70 canonical reference acquisition requirements recorded",
        "Recorded current Ref_Image_1+2 filesystem inventory and exact missing canonical side/back/3-4/contact/occlusion/support/model-backed geometry prerequisites; no masks changed or promoted and no hard gates rerun.",
        "; ".join(payload["evidence_paths"]),
        "python py_compile; reference filesystem inventory; JSON validation; panel generation; CSV row verification",
        "CANONICAL_REFERENCE_ACQUISITION_REQUIREMENTS_RECORDED_NO_PROMOTION",
        rel(EVIDENCE),
        "Acquire or integrate the missing canonical whole-body geometry package before promotion or Wave71+ activation.",
    ]
    with proof_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(line)


def load_font(size: int) -> ImageFont.ImageFont:
    for candidate in [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
    ]:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def draw_panel(payload: dict[str, object]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1600, 1000), (248, 248, 246))
    draw = ImageDraw.Draw(img)
    title_font = load_font(38)
    head_font = load_font(25)
    body_font = load_font(21)
    small_font = load_font(18)

    draw.rectangle([0, 0, 1600, 88], fill=(42, 55, 72))
    draw.text((36, 24), "Wave70 Canonical Reference Acquisition Requirements", fill=(255, 255, 255), font=title_font)

    draw.text((36, 120), f"Decision: {payload['qa_decision']}", fill=(35, 35, 35), font=head_font)
    draw.text((36, 158), "No masks changed. No promotion. No hard-gate rerun: no new route implementation or new reference package.", fill=(120, 40, 30), font=body_font)

    source = payload["current_reference_inventory"]
    ref1 = source["ref_image_1"]
    ref2 = source["ref_image_2"]
    rows = [
        f"Ref_Image_1 full-folder top-level images: {ref1['full_folder_top_level_image_count']} (knees-to-head nested exclusion preserved)",
        f"Ref_Image_1 organized gold mask images: {ref1['organized_gold_mask_image_count']}",
        f"Ref_Image_2 overlay images: {ref2['overlay_image_count']} / manifest rows: {ref2['manifest_row_count']}",
        "Top strip in Ref_Image_1 is partial-body context, not full body-part proof.",
    ]
    y = 220
    draw.text((36, y), "Current Provided Reference Context", fill=(42, 55, 72), font=head_font)
    y += 42
    for row in rows:
        draw.text((60, y), "- " + row, fill=(35, 35, 35), font=body_font)
        y += 34

    y += 18
    draw.text((36, y), "Still Needed Before Canonical Body Geometry Can Pass", fill=(42, 55, 72), font=head_font)
    y += 42
    missing = [
        "Left and right side/profile full-body views with masks",
        "Back full-body view with masks",
        "3/4 left and 3/4 right full-body views",
        "Contact / occlusion / support-surface cases with owner masks",
        "Multi-person owner separation if contact/multi-character scope remains",
        "Model-backed pose, hand, human parsing, instance, contact, canonical polygon stack",
    ]
    for row in missing:
        draw.text((60, y), "- " + row, fill=(35, 35, 35), font=body_font)
        y += 34

    draw.rectangle([36, 820, 1564, 932], outline=(160, 55, 45), width=3)
    draw.text((60, 845), "Fail-closed policy", fill=(120, 40, 30), font=head_font)
    draw.text((60, 884), "Gold overlays calibrate targets, but they are not canonical polygon authority without the model-backed geometry stack.", fill=(35, 35, 35), font=small_font)
    draw.text((60, 912), f"Evidence: {rel(EVIDENCE)}", fill=(35, 35, 35), font=small_font)
    img.save(PANEL)


def main() -> None:
    source = source_summary()
    source_evidence = evidence_summary()
    requirements = requirement_matrix()
    evidence_paths = [
        rel(EVIDENCE),
        rel(CANONICAL_EVIDENCE),
        rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name),
        rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name),
        rel(PANEL),
    ]
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_id": f"W70_CANONICAL_REFERENCE_ACQUISITION_REQUIREMENTS_{STAMP}",
        "created_iso": ISO_TS,
        "task": "Record exact current reference inventory and missing canonical whole-body acquisition requirements after Wave70 terminal prerequisite gap.",
        "current_reference_inventory": source,
        "source_evidence": source_evidence,
        "canonical_requirements": requirements,
        "policy_findings": {
            "ref_image_1_top_section_partial_body_policy_recorded": True,
            "ref_image_1_full_new_folder_knees_to_head_excluded_for_lower_body_proof": True,
            "ref_image_2_full_body_reference_included": True,
            "gold_overlays_are_calibration_not_canonical_authority": True,
            "wave71_activation_allowed": False,
            "mask_promotion_allowed": False,
        },
        "current_authority_state": {
            "body_reference_matrix_pass": False,
            "whole_body_geometry_authority_pass": False,
            "canonical_polygon_export_pass": False,
            "contact_ownership_pass": False,
            "model_backed_stack_available": False,
        },
        "gate_policy": {
            "hard_gate_rerun_performed": False,
            "reason": "This artifact records reference acquisition requirements only; no mask, pass-like row, route implementation, or new reference package was introduced.",
        },
        "promotion_decision": "no_mask_promoted_no_active_input_changed_reference_requirements_only",
        "qa_decision": "canonical_reference_acquisition_requirements_recorded_no_promotion",
        "next_step": "Acquire or integrate left/right side-profile, back, 3/4, contact/occlusion/support, optional multi-person owner-separation, and model-backed canonical geometry evidence before promotion or Wave71+ activation.",
        "evidence_paths": evidence_paths,
    }
    write_json(EVIDENCE, payload)
    write_json(CANONICAL_EVIDENCE, payload)
    write_json(TRACKER_EVIDENCE_DIR / EVIDENCE.name, payload)
    write_json(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name, payload)
    draw_panel(payload)

    evidence_additions = [
        rel(EVIDENCE),
        rel(CANONICAL_EVIDENCE),
        rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name),
        rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name),
        rel(PANEL),
    ]
    coverage_additions = [
        "canonical_reference_acquisition_requirements_recorded",
        "side_back_three_quarter_contact_support_model_backed_prerequisites_missing",
        "no_mask_promoted_reference_requirements_only",
    ]
    note = (
        f"Canonical reference acquisition requirements {STAMP}: Ref_Image_1+2 inventory recorded; side/profile, back, "
        "3/4, contact/occlusion/support, optional multi-person owner separation, and model-backed canonical geometry remain required. "
        "No masks changed or promoted; no hard gates rerun."
    )
    tracker_updates = {}
    for path in TRACKER_FILES:
        tracker_updates[rel(path)] = update_csv(
            path,
            "Tracker_ID",
            "TRK-W70-0178",
            {
                "Status_Decision": "blocked_canonical_reference_acquisition_requirements_recorded_no_promotion",
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

    top_block = f"""## Immediate Next Action - Canonical Reference Acquisition Requirements - {ISO_TS}

Recorded current Ref_Image_1+Ref_Image_2 reference inventory and exact missing canonical whole-body geometry prerequisites for the Wave70 terminal gap.

Current reference context remains useful but not promotable: Ref_Image_1 and Ref_Image_2 provide front/full-body and organized mask calibration context; Ref_Image_1 top section is partial one-third-body context and not full body-part proof; `Ref_Image_1/Full/New folder/8ead94ca6f2884fb1ae671fee89e8126.jpg` remains excluded from feet/toes/ankles/lower-calf/support proof. Gold overlays calibrate targets but are not canonical polygon authority.

Still required before body/hand/contact/support/soft-body promotion or Wave71+ activation: left and right side/profile full-body views, back full-body view, 3/4 left and right full-body views, contact/occlusion/support-surface owner cases, optional multi-person owner-separation case for multi-character/contact scope, and a model-backed canonical geometry stack with pose, hands, human parsing, person-instance ownership, contact ownership, canonical polygons, and coordinate transforms.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(PANEL)}`

No masks changed or promoted. No hard gates were rerun because this is a reference-requirements artifact, not a new route implementation or new reference package."""

    for name in [
        "NEXT_ACTION.md",
        "CURRENT_SESSION_STATE.md",
        "CURRENT_PURSUING_GOAL.md",
        "RESUME_HERE_NEXT_CODEX_SESSION.md",
    ]:
        prepend(HYDRATION_DIR / name, top_block)

    qa_block = f"""
## Wave70 Canonical Reference Acquisition Requirements - {ISO_TS}

Recorded the exact current reference inventory and missing canonical whole-body geometry acquisition requirements. Ref_Image_1+2 remain calibration/context evidence only until side/back/3-4/contact/support/owner-separation references and model-backed canonical geometry are available. No masks changed or promoted; hard gates were not rerun.

Evidence:
- `{rel(EVIDENCE)}`
- `{rel(CANONICAL_EVIDENCE)}`
- `{rel(TRACKER_EVIDENCE_DIR / EVIDENCE.name)}`
- `{rel(TRACKER_EVIDENCE_DIR / CANONICAL_EVIDENCE.name)}`
- `{rel(PANEL)}`
"""
    prepend(HYDRATION_DIR / "QA_EVIDENCE_INDEX.md", qa_block)
    append_proof_log(payload)

    print(json.dumps({
        "evidence": str(EVIDENCE),
        "canonical": str(CANONICAL_EVIDENCE),
        "panel": str(PANEL),
        "tracker_updates": tracker_updates,
        "item_updates": item_updates,
        "qa_decision": payload["qa_decision"],
        "hard_gate_rerun_performed": False,
    }, indent=2))


if __name__ == "__main__":
    main()
