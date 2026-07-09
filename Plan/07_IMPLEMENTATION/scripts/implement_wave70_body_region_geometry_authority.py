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
BODY_REFERENCE_MATRIX = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/body_reference_matrix.json"

RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_BODY_REGION_GEOMETRY_AUTHORITY_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_body_region_geometry_authority.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_body_region_geometry_authority" / RUN_STAMP

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


def body_region_reference_summary() -> dict[str, object]:
    manifest = load_json(GOLD_STANDARD_MANIFEST)
    masks = manifest.get("extracted_masks", [])
    body_tokens = (
        "abdomen",
        "arm",
        "breast",
        "calf",
        "feet",
        "foot",
        "glute",
        "hair",
        "hand",
        "pelvic",
        "thigh",
    )
    body = [item for item in masks if any(token in str(item.get("label", "")).lower() for token in body_tokens)]
    return {
        "manifest_path": rel(GOLD_STANDARD_MANIFEST),
        "manifest_exists": GOLD_STANDARD_MANIFEST.exists(),
        "all_gold_mask_count": len(masks),
        "body_region_reference_mask_count": len(body),
        "body_region_reference_labels": [item.get("label", "") for item in body],
        "layout_interpretation": {
            "top_strip": "partial upper-body / one-third-body reference only; absent lower/full-body regions here are not failures",
            "lower_strip": "primary full-body body-region validation area",
        },
    }


def full_reference_summary() -> dict[str, object]:
    manifest = load_json(FULL_REFERENCE_MANIFEST)
    refs = manifest.get("full_body_references", [])
    near = [item for item in refs if "user_corrected_not_full_body" in item.get("coverage_limitations", [])]
    lower_body_eligible = [item for item in refs if "user_corrected_not_full_body" not in item.get("coverage_limitations", [])]
    return {
        "manifest_path": rel(FULL_REFERENCE_MANIFEST),
        "manifest_exists": FULL_REFERENCE_MANIFEST.exists(),
        "recursive_image_count": len(refs),
        "full_body_lower_region_eligible_reference_count": len(lower_body_eligible),
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
        "ref_image_1_body_categories_present": ref1.get("category_presence", {}),
        "ref_image_2_body_categories_present": ref2.get("category_presence", {}),
        "limited_reference_policy": "Ref_Image_1/Full/New folder is knees-to-head only and is excluded from lower-leg/feet/support proof.",
    }


def make_panel(full_refs: dict[str, object], body_refs: dict[str, object], combined_refs: dict[str, object]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "body_region_geometry_authority_reference_route_panel.png"
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
    draw.text((20, 20), "TRK-W70-0172 body region geometry", fill=(0, 0, 0), font=font)
    draw.text((20, 44), "Ref_Image_1+2 body refs exist; parser/canonical polygon route incomplete.", fill=(130, 0, 0), font=font)
    lines = [
        f"Full refs: {full_refs['recursive_image_count']}",
        f"Lower-region eligible refs: {full_refs['full_body_lower_region_eligible_reference_count']}",
        f"Knees-to-head refs: {full_refs['near_full_knees_to_head_reference_count']}",
        f"Gold body-region masks: {body_refs['body_region_reference_mask_count']}",
        f"Combined refs: {combined_refs['combined_full_or_near_full_reference_count']}",
        f"Combined gold masks: {combined_refs['combined_gold_mask_count']}",
        "No mask promoted.",
        "Still needed:",
        "- semantic body-part parser",
        "- source-derived body-region polygons",
        "- clothing/body ownership",
        "- visibility/occlusion confidence",
        "- consensus metrics and row QA",
    ]
    y = 90
    for line in lines:
        draw.text((820, y), line, fill=(0, 0, 0), font=font)
        y += 34
    panel.save(panel_path)
    return panel_path


def update_wave70_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0172") for path in TRACKER_FILES] + [(path, "ITEM-W70-0172") for path in ITEM_FILES]
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
                row["Status_Decision"] = "ref_images_1_2_body_region_references_available_route_not_complete"
            for field in ("Evidence_Path", "Evidence_Required", "Acceptance_Evidence", "Acceptance_Criteria"):
                if field in row:
                    row[field] = append_unique(row.get(field, ""), evidence_paths)
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    [
                        "ref_image_1_body_region_references_available",
                        "ref_image_2_body_region_references_available",
                        "ref_images_1_2_combined_body_reference_matrix_available",
                        "body_region_geometry_route_not_complete_no_promotion",
                        "portrait_only_body_region_blocker_superseded_by_ref_images_1_2_context",
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
    body_refs = body_region_reference_summary()
    combined_refs = combined_reference_matrix_summary()
    panel_path = make_panel(full_refs, body_refs, combined_refs)
    body_reference_matrix_pass = bool(
        full_refs["recursive_image_count"] > 0 and body_refs["body_region_reference_mask_count"] > 0
        and combined_refs["combined_gold_mask_count"] >= body_refs["all_gold_mask_count"]
    )

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "body_region_geometry_authority.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "body_region_geometry_authority.json"
    runtime_evidence_path = RUNTIME_DIR / "body_region_geometry_authority.json"

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(FULL_REFERENCE_MANIFEST),
        rel(GOLD_STANDARD_MANIFEST),
        rel(BODY_REFERENCE_MATRIX),
        rel(panel_path),
    ]
    note = (
        f"Body region geometry authority {RUN_STAMP}: Ref_Image_1 gold standard provides "
        f"{body_refs['body_region_reference_mask_count']} body-region masks and Ref_Image_1/Full provides "
        f"{full_refs['recursive_image_count']} body context references. Ref_Image_2 is attached through the combined body reference matrix, "
        f"bringing combined context to {combined_refs['combined_full_or_near_full_reference_count']} full/near-full references and "
        f"{combined_refs['combined_gold_mask_count']} gold masks. The old portrait-only body-region blocker is superseded for this reference evaluation. "
        "Row remains Required_Not_Complete because semantic body-part parser output, source-derived body-region polygons, clothing/body ownership, "
        "visibility/occlusion confidence, consensus metrics, generated output, visual QA, and promotion evidence are incomplete. No masks promoted."
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note)

    payload = {
        "schema_version": "1.1",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "task": "Implement body region geometry resolver with blockers for TRK-W70-0172 / ITEM-W70-0172 using Ref_Image_1 gold masks and Full reference context.",
        "script": SCRIPT_REL,
        "historical_portrait_source": {
            "path": rel(HISTORICAL_PORTRAIT_SOURCE),
            "exists": HISTORICAL_PORTRAIT_SOURCE.exists(),
            "sha256": sha256_file(HISTORICAL_PORTRAIT_SOURCE) if HISTORICAL_PORTRAIT_SOURCE.exists() else None,
            "role": "historical_prior_active_source_not_decisive_for_current_body_reference_evaluation",
        },
        "ref_image_1_full_body_references": full_refs,
        "ref_image_1_body_region_gold_refs": body_refs,
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
        "whole_body_geometry_authority": {
            "result": "required_not_complete",
            "reference_source_available": full_refs["recursive_image_count"] > 0,
            "body_region_gold_refs_available": body_refs["body_region_reference_mask_count"] > 0,
            "body_reference_matrix_pass": body_reference_matrix_pass,
            "source_visibility_blocker_superseded": True,
            "production_route_pass": False,
            "whole_body_geometry_authority_pass": False,
            "pose_hand_dense_landmark_or_segmentation_pass": False,
            "semantic_human_part_parsing_pass": False,
            "contact_occlusion_ownership_pass": False,
            "body_region_geometry_pass": False,
            "source_derived_landmark_or_segmentation_pass": False,
            "model_consensus_geometry_pass": False,
            "visibility_occlusion_confidence_pass": False,
            "no_symmetry_guessing_pass": True,
            "canonical_polygon_export_pass": False,
            "blocked_reason": (
                "reference_body_region_masks_available_but_production_route_missing_semantic_body_part_parser_"
                "source_derived_body_region_polygons_clothing_body_ownership_visibility_confidence_consensus_metrics_and_promotion_evidence"
            ),
            "findings": [
                "Ref_Image_1 gold-standard masks include body-region references across torso, limbs, hands, feet, hair, pelvis, glutes, and breasts.",
                "Ref_Image_1/Full supplies full/near-full body context, with the knees-to-head image still limited for lower-body proof.",
                "Ref_Image_2 is attached through the combined body reference matrix and contributes additional body-region mask context.",
                "The prior portrait-only body-region blocker is superseded for this reference evaluation.",
                "Reference masks do not by themselves prove parser-backed body-region ownership, canonical polygons, generated output, visual QA, or promotion evidence.",
                "No body-region polygon, segmentation map, or mask promotion was produced from this evidence.",
            ],
        },
        "body_region_geometry_authority": {
            "result": "required_not_complete",
            "source_visibility_pass": True,
            "body_region_geometry_pass": False,
            "protected_neighbor_pass": False,
            "canonical_polygon_export_pass": False,
            "blocked_reason": "body_region_references_available_but_parser_backed_canonical_geometry_route_not_complete",
        },
        "qa_decision": "ref_images_1_2_body_region_references_available_route_not_complete",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_body_region_geometry_route_not_complete",
        "tracker_item_updates": row_updates,
        "next_step": "Run Wave70 geometry and promotion hard gates, attach gate evidence to TRK-W70-0172 / ITEM-W70-0172, then continue to TRK-W70-0173 model consensus geometry validator.",
    }
    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    print(
        json.dumps(
            {
                "evidence_id": EVIDENCE_ID,
                "result": payload["qa_decision"],
                "full_reference_count": full_refs["recursive_image_count"],
                "body_region_gold_mask_count": body_refs["body_region_reference_mask_count"],
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
