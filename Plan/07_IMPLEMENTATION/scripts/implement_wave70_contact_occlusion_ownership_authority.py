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
EVIDENCE_ID = f"W70_CONTACT_OCCLUSION_OWNERSHIP_AUTHORITY_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_contact_occlusion_ownership_authority.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_contact_occlusion_ownership_authority" / RUN_STAMP

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


def contact_reference_summary() -> dict[str, object]:
    manifest = load_json(GOLD_STANDARD_MANIFEST)
    masks = manifest.get("extracted_masks", [])
    hand_tokens = ("hand", "finger", "thumb", "pinky")
    foot_tokens = ("feet", "foot", "toe")
    body_tokens = ("abdomen", "arm", "breast", "calf", "glute", "pelvic", "thigh")
    hand = [item for item in masks if any(token in str(item.get("label", "")).lower() for token in hand_tokens)]
    foot = [item for item in masks if any(token in str(item.get("label", "")).lower() for token in foot_tokens)]
    body = [item for item in masks if any(token in str(item.get("label", "")).lower() for token in body_tokens)]
    return {
        "manifest_path": rel(GOLD_STANDARD_MANIFEST),
        "manifest_exists": GOLD_STANDARD_MANIFEST.exists(),
        "all_gold_mask_count": len(masks),
        "hand_contact_actor_reference_count": len(hand),
        "foot_support_actor_reference_count": len(foot),
        "body_contact_surface_reference_count": len(body),
        "hand_reference_labels": [item.get("label", "") for item in hand],
        "foot_reference_labels": [item.get("label", "") for item in foot],
        "body_contact_surface_labels": [item.get("label", "") for item in body],
        "layout_interpretation": {
            "top_strip": "partial upper-body / one-third-body reference only; absent lower/full-body contact actors here are not failures",
            "lower_strip": "primary full-body body-part validation area; still not an automatic contact ownership solver",
        },
    }


def full_reference_summary() -> dict[str, object]:
    manifest = load_json(FULL_REFERENCE_MANIFEST)
    refs = manifest.get("full_body_references", [])
    near = [item for item in refs if "user_corrected_not_full_body" in item.get("coverage_limitations", [])]
    eligible_for_support = [item for item in refs if "user_corrected_not_full_body" not in item.get("coverage_limitations", [])]
    return {
        "manifest_path": rel(FULL_REFERENCE_MANIFEST),
        "manifest_exists": FULL_REFERENCE_MANIFEST.exists(),
        "recursive_image_count": len(refs),
        "support_contact_eligible_reference_count": len(eligible_for_support),
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
        "ref_image_1_contact_actor_categories_present": {
            "arms_hands_fingers": ref1.get("category_presence", {}).get("arms_hands_fingers", False),
            "legs_feet_toes": ref1.get("category_presence", {}).get("legs_feet_toes", False),
            "torso_abdomen": ref1.get("category_presence", {}).get("torso_abdomen", False),
        },
        "ref_image_2_contact_actor_categories_present": {
            "arms_hands_fingers": ref2.get("category_presence", {}).get("arms_hands_fingers", False),
            "legs_feet_toes": ref2.get("category_presence", {}).get("legs_feet_toes", False),
            "torso_abdomen": ref2.get("category_presence", {}).get("torso_abdomen", False),
        },
        "limited_reference_policy": "Ref_Image_1/Full/New folder is knees-to-head only and cannot prove support/feet/floor contact.",
    }


def make_panel(full_refs: dict[str, object], contact_refs: dict[str, object], combined_refs: dict[str, object]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "contact_occlusion_ownership_authority_reference_route_panel.png"
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
    draw.text((20, 20), "TRK-W70-0171 contact occlusion ownership", fill=(0, 0, 0), font=font)
    draw.text((20, 44), "Ref_Image_1+2 actors exist; contact ownership solver route incomplete.", fill=(130, 0, 0), font=font)
    lines = [
        f"Full refs: {full_refs['recursive_image_count']}",
        f"Support-contact eligible refs: {full_refs['support_contact_eligible_reference_count']}",
        f"Knees-to-head refs: {full_refs['near_full_knees_to_head_reference_count']}",
        f"Hand actor masks: {contact_refs['hand_contact_actor_reference_count']}",
        f"Foot/support actor masks: {contact_refs['foot_support_actor_reference_count']}",
        f"Body surface masks: {contact_refs['body_contact_surface_reference_count']}",
        f"Combined refs: {combined_refs['combined_full_or_near_full_reference_count']}",
        f"Combined gold masks: {combined_refs['combined_gold_mask_count']}",
        "No mask promoted.",
        "Still needed:",
        "- contact pair/owner graph",
        "- parser-backed body/object ownership",
        "- occlusion transfer proof",
        "- protected/owner overlap metrics",
        "- canonical contact polygons",
    ]
    y = 90
    for line in lines:
        draw.text((820, y), line, fill=(0, 0, 0), font=font)
        y += 34
    panel.save(panel_path)
    return panel_path


def update_wave70_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0171") for path in TRACKER_FILES] + [(path, "ITEM-W70-0171") for path in ITEM_FILES]
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
                row["Status_Decision"] = "ref_images_1_2_contact_actor_references_available_route_not_complete"
            for field in ("Evidence_Path", "Evidence_Required", "Acceptance_Evidence", "Acceptance_Criteria"):
                if field in row:
                    row[field] = append_unique(row.get(field, ""), evidence_paths)
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    [
                        "ref_image_1_contact_actor_references_available",
                        "ref_image_2_contact_actor_references_available",
                        "ref_images_1_2_combined_body_reference_matrix_available",
                        "contact_occlusion_ownership_route_not_complete_no_promotion",
                        "portrait_only_contact_blocker_superseded_by_ref_images_1_2_context",
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
    contact_refs = contact_reference_summary()
    combined_refs = combined_reference_matrix_summary()
    panel_path = make_panel(full_refs, contact_refs, combined_refs)
    body_reference_matrix_pass = bool(
        full_refs["recursive_image_count"] > 0
        and contact_refs["hand_contact_actor_reference_count"] > 0
        and contact_refs["body_contact_surface_reference_count"] > 0
        and combined_refs["combined_gold_mask_count"] >= contact_refs["all_gold_mask_count"]
    )

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "contact_occlusion_ownership_authority.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "contact_occlusion_ownership_authority.json"
    runtime_evidence_path = RUNTIME_DIR / "contact_occlusion_ownership_authority.json"

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
        f"Contact occlusion ownership authority {RUN_STAMP}: Ref_Image_1 gold standard provides "
        f"{contact_refs['hand_contact_actor_reference_count']} hand/finger actor masks, "
        f"{contact_refs['foot_support_actor_reference_count']} foot/support actor masks, and "
        f"{contact_refs['body_contact_surface_reference_count']} body surface masks; Ref_Image_1/Full provides "
        f"{full_refs['recursive_image_count']} body context references. Ref_Image_2 is attached through the combined body reference matrix, "
        f"bringing combined context to {combined_refs['combined_full_or_near_full_reference_count']} full/near-full references and "
        f"{combined_refs['combined_gold_mask_count']} gold masks. The old portrait-only contact blocker is superseded for this reference evaluation. "
        "Row remains Required_Not_Complete because contact pair/owner graph, parser-backed body/object ownership, occlusion transfer proof, "
        "protected/owner overlap metrics, canonical contact polygons, generated output, visual QA, and promotion evidence are incomplete. No masks promoted."
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note)

    payload = {
        "schema_version": "1.1",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "task": "Implement contact occlusion ownership resolver for TRK-W70-0171 / ITEM-W70-0171 using Ref_Image_1 gold masks and Full reference context.",
        "script": SCRIPT_REL,
        "historical_portrait_source": {
            "path": rel(HISTORICAL_PORTRAIT_SOURCE),
            "exists": HISTORICAL_PORTRAIT_SOURCE.exists(),
            "sha256": sha256_file(HISTORICAL_PORTRAIT_SOURCE) if HISTORICAL_PORTRAIT_SOURCE.exists() else None,
            "role": "historical_prior_active_source_not_decisive_for_current_body_reference_evaluation",
        },
        "ref_image_1_full_body_references": full_refs,
        "ref_image_1_contact_actor_gold_refs": contact_refs,
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
        "contact_occlusion_ownership_authority": {
            "result": "required_not_complete",
            "reference_source_available": full_refs["recursive_image_count"] > 0,
            "contact_actor_gold_refs_available": contact_refs["hand_contact_actor_reference_count"] > 0,
            "body_surface_gold_refs_available": contact_refs["body_contact_surface_reference_count"] > 0,
            "body_reference_matrix_pass": body_reference_matrix_pass,
            "source_visibility_blocker_superseded": True,
            "production_route_pass": False,
            "contact_occlusion_ownership_pass": False,
            "protected_overlap_threshold_pass": False,
            "owner_overlap_error_pass": False,
            "whole_body_geometry_authority_pass": False,
            "pose_hand_dense_landmark_or_segmentation_pass": False,
            "semantic_human_part_parsing_pass": False,
            "body_region_geometry_pass": False,
            "canonical_polygon_export_pass": False,
            "blocked_reason": (
                "reference_contact_actors_available_but_production_route_missing_contact_pair_owner_graph_parser_backed_"
                "body_object_ownership_occlusion_transfer_proof_overlap_metrics_canonical_polygons_and_promotion_evidence"
            ),
            "findings": [
                "Ref_Image_1 gold-standard masks include hand/finger, foot/toe, and body-surface reference actors.",
                "Ref_Image_1/Full supplies full/near-full body context for contact/occlusion authority rows.",
                "Ref_Image_2 is attached through the combined body reference matrix and contributes additional contact actor/body surface context.",
                "The prior portrait-only contact blocker is superseded for this reference evaluation.",
                "Reference actors do not by themselves prove contact ownership, occlusion transfer, protected-overlap thresholds, owner-overlap metrics, generated output, visual QA, or promotion evidence.",
                "No contact, hand, body, object, support, or broad mask geometry was generated, changed, or promoted from this evidence.",
            ],
        },
        "qa_decision": "ref_images_1_2_contact_actor_references_available_route_not_complete",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_contact_occlusion_ownership_route_not_complete",
        "tracker_item_updates": row_updates,
        "next_step": "Run Wave70 geometry and promotion hard gates, attach gate evidence to TRK-W70-0171 / ITEM-W70-0171, then continue to TRK-W70-0172 body region geometry resolver.",
    }
    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    print(
        json.dumps(
            {
                "evidence_id": EVIDENCE_ID,
                "result": payload["qa_decision"],
                "full_reference_count": full_refs["recursive_image_count"],
                "hand_actor_mask_count": contact_refs["hand_contact_actor_reference_count"],
                "foot_actor_mask_count": contact_refs["foot_support_actor_reference_count"],
                "body_surface_mask_count": contact_refs["body_contact_surface_reference_count"],
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
