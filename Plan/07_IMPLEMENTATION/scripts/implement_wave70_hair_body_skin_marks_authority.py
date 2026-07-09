from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[3]
HISTORICAL_PORTRAIT_SOURCE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
GOLD_STANDARD_MANIFEST = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_body_mask_gold_standard.json"
FULL_REFERENCE_MANIFEST = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_full_body_references.json"
BODY_SKIN_COMPOSITE_MANIFEST = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/mf70_body_skin_visible_ref_image_1_gold_standard.json"
BODY_REFERENCE_MATRIX = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/body_reference_matrix.json"

RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_HAIR_BODY_SKIN_MARKS_AUTHORITY_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_hair_body_skin_marks_authority.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_hair_body_skin_marks_authority" / RUN_STAMP

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]


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


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def hair_body_skin_gold_refs() -> dict[str, object]:
    manifest = load_json(GOLD_STANDARD_MANIFEST)
    masks = manifest.get("extracted_masks", [])
    hair = [item for item in masks if "hair" in str(item.get("label", "")).lower()]
    body_skin_tokens = ("abdomen", "arm", "breast", "calf", "feet", "foot", "glute", "hand", "pelvic", "thigh")
    body_skin = [
        item
        for item in masks
        if any(token in str(item.get("label", "")).lower() for token in body_skin_tokens)
    ]
    return {
        "manifest_path": rel(GOLD_STANDARD_MANIFEST),
        "manifest_exists": GOLD_STANDARD_MANIFEST.exists(),
        "hair_reference_mask_count": len(hair),
        "body_skin_part_reference_mask_count": len(body_skin),
        "hair_reference_masks": [
            {
                "label": item.get("label", ""),
                "binary_mask_path": item.get("binary_mask_path", ""),
                "binary_mask_sha256": item.get("binary_mask_sha256", ""),
                "red_overlay_pixel_count": item.get("red_overlay_pixel_count", 0),
                "mask_type_candidates": item.get("mask_type_candidates", []),
            }
            for item in hair
        ],
        "body_skin_part_reference_labels": [item.get("label", "") for item in body_skin],
        "body_skin_composite_manifest": {
            "path": rel(BODY_SKIN_COMPOSITE_MANIFEST),
            "exists": BODY_SKIN_COMPOSITE_MANIFEST.exists(),
        },
        "layout_interpretation": {
            "top_strip": "partial upper-body / one-third-body reference only; absent lower/full-body skin parts here are not failures",
            "lower_strip": "primary full-body skin and body-mask validation area",
        },
    }


def full_reference_summary() -> dict[str, object]:
    manifest = load_json(FULL_REFERENCE_MANIFEST)
    refs = manifest.get("full_body_references", [])
    near = [item for item in refs if "user_corrected_not_full_body" in item.get("coverage_limitations", [])]
    return {
        "manifest_path": rel(FULL_REFERENCE_MANIFEST),
        "manifest_exists": FULL_REFERENCE_MANIFEST.exists(),
        "recursive_image_count": len(refs),
        "near_full_knees_to_head_reference_count": len(near),
        "contact_sheet": manifest.get("artifacts", {}).get("contact_sheet") if manifest else None,
        "near_full_limitations": [
            {
                "path": item.get("path", ""),
                "relative_to_full_dir": item.get("relative_to_full_dir", ""),
                "coverage_limitations": item.get("coverage_limitations", []),
            }
            for item in near
        ],
    }


def combined_reference_matrix_summary() -> dict[str, object]:
    matrix = load_json(BODY_REFERENCE_MATRIX)
    ref1 = matrix.get("ref_image_1_body_mask_gold_refs", {})
    ref2 = matrix.get("ref_image_2_body_mask_gold_refs", {})
    ref1_full = matrix.get("ref_image_1_full_body_references", {})
    summary = matrix.get("combined_body_reference_matrix", {})
    return {
        "manifest_path": rel(BODY_REFERENCE_MATRIX),
        "manifest_exists": BODY_REFERENCE_MATRIX.exists(),
        "evidence_id": matrix.get("evidence_id", ""),
        "qa_decision": matrix.get("qa_decision", ""),
        "ref_image_1_gold_mask_count": ref1.get("all_gold_mask_count", 0),
        "ref_image_2_gold_mask_count": ref2.get("all_gold_mask_count", 0),
        "combined_gold_mask_count": summary.get(
            "combined_gold_mask_count",
            int(ref1.get("all_gold_mask_count", 0) or 0) + int(ref2.get("all_gold_mask_count", 0) or 0),
        ),
        "ref_image_1_full_or_near_full_reference_count": ref1_full.get("static_pose_reference_count", 0),
        "ref_image_2_full_body_reference_count": 1 if ref2.get("main_reference", {}).get("exists") else 0,
        "combined_full_or_near_full_reference_count": summary.get(
            "combined_full_or_near_full_reference_count",
            int(ref1_full.get("static_pose_reference_count", 0) or 0) + (1 if ref2.get("main_reference", {}).get("exists") else 0),
        ),
        "ref_image_1_hair_category_present": ref1.get("category_presence", {}).get("hair", False),
        "ref_image_2_hair_category_present": ref2.get("category_presence", {}).get("hair", False),
        "limited_reference_policy": "Ref_Image_1/Full/New folder is knees-to-head only; usable for hair/scalp/upper-body skin context but not lower-leg/feet proof.",
    }


def make_panel(full_refs: dict[str, object], gold_refs: dict[str, object], combined_refs: dict[str, object]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "hair_body_skin_marks_authority_reference_route_panel.png"
    panel = Image.new("RGB", (1200, 720), "white")
    draw = ImageDraw.Draw(panel)
    font = ImageFont.load_default()
    contact_sheet_rel = full_refs.get("contact_sheet")
    if contact_sheet_rel:
        contact_sheet_path = PROJECT_ROOT / str(contact_sheet_rel)
        if contact_sheet_path.exists():
            sheet = Image.open(contact_sheet_path).convert("RGB")
            sheet.thumbnail((760, 620))
            panel.paste(sheet, (20, 80))
    draw.text((20, 20), "TRK-W70-0170 hair/body-skin authority", fill=(0, 0, 0), font=font)
    draw.text((20, 44), "Ref_Image_1+2 hair/body-skin refs available; parser/polygon route incomplete.", fill=(130, 0, 0), font=font)
    lines = [
        f"Full refs: {full_refs['recursive_image_count']}",
        f"Knees-to-head refs: {full_refs['near_full_knees_to_head_reference_count']}",
        f"Hair gold masks: {gold_refs['hair_reference_mask_count']}",
        f"Body-skin part refs: {gold_refs['body_skin_part_reference_mask_count']}",
        f"Body-skin composite exists: {gold_refs['body_skin_composite_manifest']['exists']}",
        f"Combined refs: {combined_refs['combined_full_or_near_full_reference_count']}",
        f"Combined gold masks: {combined_refs['combined_gold_mask_count']}",
        "No mask promoted.",
        "Still needed:",
        "- semantic hair/body/skin parser",
        "- skin-mark detector or verified mask route",
        "- scalp/body-hair ownership",
        "- canonical hair/body-skin polygons",
        "- row-level generated output and QA",
    ]
    y = 90
    for line in lines:
        draw.text((820, y), line, fill=(0, 0, 0), font=font)
        y += 34
    panel.save(panel_path)
    return panel_path


def update_wave70_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0170") for path in TRACKER_FILES] + [(path, "ITEM-W70-0170") for path in ITEM_FILES]
    for csv_path, target_id in targets:
        with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fieldnames = reader.fieldnames or []
        id_field = "Tracker_ID" if target_id.startswith("TRK-") else "Item_ID"
        changed = 0
        for row in rows:
            if row.get(id_field) != target_id:
                continue
            changed += 1
            if "Status" in row:
                row["Status"] = "Required_Not_Complete"
            if "Status_Decision" in row:
                row["Status_Decision"] = "ref_images_1_2_hair_body_skin_references_available_route_not_complete"
            for field in ("Evidence_Path", "Evidence_Required", "Acceptance_Evidence", "Acceptance_Criteria"):
                if field in row:
                    row[field] = append_unique(row.get(field, ""), evidence_paths)
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    [
                        "ref_image_1_hair_body_skin_references_available",
                        "ref_image_2_hair_body_skin_references_available",
                        "ref_images_1_2_combined_body_reference_matrix_available",
                        "hair_body_skin_route_not_complete_no_promotion",
                        "portrait_only_blocker_superseded_by_ref_image_1_gold_context",
                    ],
                )
            if "Notes" in row:
                row["Notes"] = append_unique(row.get("Notes", ""), [note])
        if changed:
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
        updated[rel(csv_path)] = changed
    return updated


def main() -> int:
    full_refs = full_reference_summary()
    gold_refs = hair_body_skin_gold_refs()
    combined_refs = combined_reference_matrix_summary()
    panel_path = make_panel(full_refs, gold_refs, combined_refs)
    body_reference_matrix_pass = bool(
        full_refs["recursive_image_count"] > 0
        and (gold_refs["hair_reference_mask_count"] > 0 or gold_refs["body_skin_part_reference_mask_count"] > 0)
        and combined_refs["combined_gold_mask_count"] >= gold_refs["body_skin_part_reference_mask_count"]
    )

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "hair_body_skin_marks_authority.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "hair_body_skin_marks_authority.json"
    runtime_evidence_path = RUNTIME_DIR / "hair_body_skin_marks_authority.json"

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(FULL_REFERENCE_MANIFEST),
        rel(GOLD_STANDARD_MANIFEST),
        rel(BODY_SKIN_COMPOSITE_MANIFEST),
        rel(BODY_REFERENCE_MATRIX),
        rel(panel_path),
    ]
    note = (
        f"Hair body skin marks authority {RUN_STAMP}: Ref_Image_1 gold standard provides "
        f"{gold_refs['hair_reference_mask_count']} hair reference masks and "
        f"{gold_refs['body_skin_part_reference_mask_count']} body-skin part references; "
        f"Ref_Image_1/Full provides {full_refs['recursive_image_count']} body context references. "
        f"Ref_Image_2 is attached through the combined body reference matrix, bringing combined context to "
        f"{combined_refs['combined_full_or_near_full_reference_count']} full/near-full references and "
        f"{combined_refs['combined_gold_mask_count']} gold masks. "
        "The old portrait-only authority blocker is superseded for this reference evaluation. Row remains Required_Not_Complete "
        "because semantic hair/body/skin parsing, skin-mark detection, scalp/body-hair ownership, canonical polygons, "
        "row-level generated output, visual QA, and promotion evidence are still incomplete. No masks promoted."
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note)

    payload = {
        "schema_version": "1.1",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "task": "Implement hair body hair scalp skin marks and body skin authority for TRK-W70-0170 / ITEM-W70-0170 using Ref_Image_1 gold masks and Full reference context.",
        "script": SCRIPT_REL,
        "historical_portrait_source": {
            "path": rel(HISTORICAL_PORTRAIT_SOURCE),
            "exists": HISTORICAL_PORTRAIT_SOURCE.exists(),
            "sha256": sha256_file(HISTORICAL_PORTRAIT_SOURCE) if HISTORICAL_PORTRAIT_SOURCE.exists() else None,
            "role": "historical_prior_active_source_not_decisive_for_current_body_reference_evaluation",
        },
        "ref_image_1_full_body_references": full_refs,
        "ref_image_1_hair_body_skin_gold_refs": gold_refs,
        "ref_images_1_2_combined_body_reference_matrix": combined_refs,
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": str(PROJECT_ROOT),
        },
        "artifacts": {
            "reference_route_panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
        },
        "hair_body_skin_marks_authority": {
            "result": "required_not_complete",
            "reference_source_available": full_refs["recursive_image_count"] > 0,
            "hair_gold_masks_available": gold_refs["hair_reference_mask_count"] > 0,
            "body_skin_gold_refs_available": gold_refs["body_skin_part_reference_mask_count"] > 0,
            "body_reference_matrix_pass": body_reference_matrix_pass,
            "source_visibility_blocker_superseded": True,
            "production_route_pass": False,
            "hair_skin_region_pass": False,
            "body_hair_region_pass": False,
            "skin_mark_boundary_pass": False,
            "whole_body_geometry_authority_pass": False,
            "pose_hand_dense_landmark_or_segmentation_pass": False,
            "semantic_human_part_parsing_pass": False,
            "contact_occlusion_ownership_pass": False,
            "body_region_geometry_pass": False,
            "canonical_polygon_export_pass": False,
            "blocked_reason": (
                "reference_hair_and_body_skin_masks_available_but_production_route_missing_semantic_hair_body_skin_parser_"
                "skin_mark_detection_scalp_body_hair_ownership_canonical_polygons_and_promotion_evidence"
            ),
            "findings": [
                "Ref_Image_1 gold-standard masks include a hair reference and broad body-skin/body-part references.",
                "Ref_Image_1/Full supplies full/near-full body context for skin/hair authority rows.",
                "Ref_Image_2 is attached through the combined body reference matrix and contributes additional full-body hair/skin mask context.",
                "The prior portrait-only authority blocker is superseded for this reference evaluation.",
                "Reference availability does not by itself create semantic parser output, skin-mark detection, scalp/body-hair ownership, canonical polygons, generated output, visual QA, or promotion proof.",
                "No mask geometry was generated, changed, or promoted from this evidence.",
            ],
        },
        "qa_decision": "ref_images_1_2_hair_body_skin_references_available_route_not_complete",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_hair_body_skin_route_not_complete",
        "tracker_item_updates": row_updates,
        "next_step": "Run Wave70 geometry and promotion hard gates, attach gate evidence to TRK-W70-0170 / ITEM-W70-0170, then continue to TRK-W70-0171 contact occlusion ownership authority.",
    }
    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    print(
        json.dumps(
            {
                "evidence_id": EVIDENCE_ID,
                "result": payload["qa_decision"],
                "full_reference_count": full_refs["recursive_image_count"],
                "hair_reference_mask_count": gold_refs["hair_reference_mask_count"],
                "body_skin_part_reference_mask_count": gold_refs["body_skin_part_reference_mask_count"],
                "body_skin_composite_exists": gold_refs["body_skin_composite_manifest"]["exists"],
                "combined_full_or_near_full_reference_count": combined_refs["combined_full_or_near_full_reference_count"],
                "combined_gold_mask_count": combined_refs["combined_gold_mask_count"],
                "evidence": rel(qa_evidence_path),
                "panel": rel(panel_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
