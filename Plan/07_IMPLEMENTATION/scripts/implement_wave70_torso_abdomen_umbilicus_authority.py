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

RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_TORSO_ABDOMEN_UMBILICUS_AUTHORITY_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_torso_abdomen_umbilicus_authority.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_torso_abdomen_umbilicus_authority" / RUN_STAMP

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]

PREREQUISITE_EVIDENCE = [
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_POSE_LANDMARK_AUTHORITY_20260708T141735-0500.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_HUMAN_PART_PARSING_AUTHORITY_20260708T142544-0500.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_HAND_FINGER_LANDMARK_AUTHORITY_20260708T142210-0500.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_body_mask_gold_standard.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_full_body_references.json",
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


def torso_gold_masks() -> dict[str, object]:
    manifest = load_json(GOLD_STANDARD_MANIFEST)
    masks = []
    labels = ("abdomen", "stomach", "belly", "pelvic", "breast", "glute", "chest")
    for item in manifest.get("extracted_masks", []):
        label = str(item.get("label", "")).lower()
        if any(token in label for token in labels):
            masks.append(
                {
                    "label": item.get("label", ""),
                    "binary_mask_path": item.get("binary_mask_path", ""),
                    "binary_mask_sha256": item.get("binary_mask_sha256", ""),
                    "red_overlay_pixel_count": item.get("red_overlay_pixel_count", 0),
                    "mask_type_candidates": item.get("mask_type_candidates", []),
                    "gold_standard_use": item.get("gold_standard_use", ""),
                }
            )
    return {
        "manifest_path": rel(GOLD_STANDARD_MANIFEST),
        "manifest_exists": GOLD_STANDARD_MANIFEST.exists(),
        "torso_reference_mask_count": len(masks),
        "torso_reference_masks": masks,
        "layout_interpretation": {
            "top_strip": "partial upper-body / one-third-body reference only; absent lower/full-body parts here are not failures",
            "lower_strip": "primary full-body pose/body-mask validation area",
        },
    }


def full_reference_summary() -> dict[str, object]:
    manifest = load_json(FULL_REFERENCE_MANIFEST)
    refs = manifest.get("full_body_references", [])
    full_like = []
    near_limited = []
    for item in refs:
        limitations = item.get("coverage_limitations", [])
        if "user_corrected_not_full_body" in limitations:
            near_limited.append(item)
        else:
            full_like.append(item)
    return {
        "manifest_path": rel(FULL_REFERENCE_MANIFEST),
        "manifest_exists": FULL_REFERENCE_MANIFEST.exists(),
        "recursive_image_count": len(refs),
        "full_or_near_full_body_reference_count": len(full_like),
        "near_full_knees_to_head_reference_count": len(near_limited),
        "near_full_limitations": [
            {
                "path": item.get("path", ""),
                "relative_to_full_dir": item.get("relative_to_full_dir", ""),
                "coverage_scope": item.get("coverage_scope", ""),
                "coverage_limitations": item.get("coverage_limitations", []),
            }
            for item in near_limited
        ],
        "contact_sheet": manifest.get("artifacts", {}).get("contact_sheet") if manifest else None,
        "references": refs,
    }


def route_status(full_refs: dict[str, object], gold_masks: dict[str, object]) -> dict[str, object]:
    refs_available = full_refs["recursive_image_count"] > 0
    torso_masks_available = gold_masks["torso_reference_mask_count"] > 0
    return {
        "reference_source_available": refs_available,
        "torso_gold_masks_available": torso_masks_available,
        "body_reference_matrix_pass": bool(refs_available and torso_masks_available),
        "source_visibility_blocker_superseded": True,
        "source_visibility_decision": (
            "Ref_Image_1/Full is now the primary body-row reference source; the older portrait crop is historical "
            "context and is not the decisive torso visibility blocker for this reference evaluation."
        ),
        "production_route_pass": False,
        "whole_body_geometry_authority_pass": False,
        "pose_hand_dense_landmark_or_segmentation_pass": False,
        "semantic_human_part_parsing_pass": False,
        "contact_occlusion_ownership_pass": False,
        "body_region_geometry_pass": False,
        "canonical_polygon_export_pass": False,
        "protected_neighbor_pass": False,
        "torso_region_pass": False,
        "abdomen_region_pass": False,
        "belly_button_umbilicus_pass": False,
        "blocked_reason": (
            "reference_sources_and_gold_masks_available_but_production_route_missing_full_body_parser_contact_ownership_"
            "canonical_polygon_and_row_level_promotion_evidence"
        ),
    }


def make_reference_route_panel(full_refs: dict[str, object], gold_masks: dict[str, object], status: dict[str, object]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "torso_abdomen_umbilicus_authority_reference_route_panel.png"
    contact_sheet_rel = full_refs.get("contact_sheet")
    base = Image.new("RGB", (1200, 720), "white")
    draw = ImageDraw.Draw(base)
    font = ImageFont.load_default()

    if contact_sheet_rel:
        contact_sheet_path = PROJECT_ROOT / str(contact_sheet_rel)
        if contact_sheet_path.exists():
            sheet = Image.open(contact_sheet_path).convert("RGB")
            sheet.thumbnail((760, 620))
            base.paste(sheet, (20, 80))

    draw.text((20, 20), "TRK-W70-0167 torso/abdomen/umbilicus authority", fill=(0, 0, 0), font=font)
    draw.text((20, 44), "Full references available; production geometry route remains incomplete.", fill=(130, 0, 0), font=font)

    x = 820
    y = 90
    lines = [
        f"Full refs: {full_refs['recursive_image_count']}",
        f"Near-full knees-to-head exceptions: {full_refs['near_full_knees_to_head_reference_count']}",
        f"Torso gold masks: {gold_masks['torso_reference_mask_count']}",
        f"Body reference matrix pass: {status['body_reference_matrix_pass']}",
        "Top strip rule: partial upper body only",
        "Lower strip: primary full-body mask validation",
        "No mask promoted.",
        "Still needed:",
        "- semantic human-part parsing route",
        "- contact/occlusion ownership",
        "- canonical torso/body polygons",
        "- row-level generated output and QA",
    ]
    for line in lines:
        draw.text((x, y), line, fill=(0, 0, 0), font=font)
        y += 34

    base.save(panel_path)
    return panel_path


def update_wave70_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0167") for path in TRACKER_FILES] + [(path, "ITEM-W70-0167") for path in ITEM_FILES]
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
                row["Status_Decision"] = "ref_image_1_full_body_torso_references_available_route_not_complete"
            for field in ("Evidence_Path", "Evidence_Required", "Acceptance_Evidence", "Acceptance_Criteria"):
                if field in row:
                    row[field] = append_unique(row.get(field, ""), evidence_paths)
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    [
                        "ref_image_1_full_body_torso_references_available",
                        "torso_route_not_complete_no_promotion",
                        "portrait_visibility_blocker_superseded_by_full_reference_source",
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
    gold_masks = torso_gold_masks()
    status = route_status(full_refs, gold_masks)
    panel_path = make_reference_route_panel(full_refs, gold_masks, status)

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "torso_abdomen_umbilicus_authority.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "torso_abdomen_umbilicus_authority.json"
    runtime_evidence_path = RUNTIME_DIR / "torso_abdomen_umbilicus_authority.json"

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(FULL_REFERENCE_MANIFEST),
        rel(GOLD_STANDARD_MANIFEST),
        rel(panel_path),
    ]
    note = (
        f"Torso abdomen umbilicus authority {RUN_STAMP}: Ref_Image_1/Full provides "
        f"{full_refs['recursive_image_count']} full/near-full body references, with "
        f"{full_refs['near_full_knees_to_head_reference_count']} user-corrected knees-to-head near-full exception. "
        f"Ref_Image_1 gold standard provides {gold_masks['torso_reference_mask_count']} torso/abdomen/pelvic/glute/breast masks. "
        "The old portrait visibility blocker is superseded for this reference evaluation. Row remains Required_Not_Complete "
        "because semantic human-part parsing, contact ownership, canonical torso polygons, row-level generated output, visual QA, "
        "and promotion evidence are still not complete. No masks promoted."
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note)

    payload = {
        "schema_version": "1.1",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "task": "Implement torso chest abdomen belly-button waist hips and back authority for TRK-W70-0167 / ITEM-W70-0167 using Ref_Image_1/Full references and Ref_Image_1 gold masks.",
        "script": SCRIPT_REL,
        "historical_portrait_source": {
            "path": rel(HISTORICAL_PORTRAIT_SOURCE),
            "exists": HISTORICAL_PORTRAIT_SOURCE.exists(),
            "sha256": sha256_file(HISTORICAL_PORTRAIT_SOURCE) if HISTORICAL_PORTRAIT_SOURCE.exists() else None,
            "role": "historical_prior_active_source_not_decisive_for_current_body_reference_evaluation",
        },
        "ref_image_1_full_body_references": full_refs,
        "ref_image_1_torso_gold_masks": gold_masks,
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": str(PROJECT_ROOT),
        },
        "prerequisite_evidence": PREREQUISITE_EVIDENCE,
        "artifacts": {
            "reference_route_panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
        },
        "torso_abdomen_umbilicus_authority": {
            "result": "required_not_complete",
            **status,
            "findings": [
                "Ref_Image_1/Full is now recorded as the primary full/near-full body reference set for body authority rows.",
                "The image under Ref_Image_1/Full/New folder is explicitly limited to knees-to-head coverage and is not used as feet/toes/ankles/lower-calf proof.",
                "Ref_Image_1 gold-standard masks include torso/abdomen/pelvic/glute/breast mask references.",
                "The prior portrait-only visibility blocker is superseded for this reference evaluation.",
                "Reference availability does not by itself create source-derived parser output, contact ownership, canonical polygons, generated output, visual QA, or promotion proof.",
                "No mask geometry was generated, changed, or promoted from this evidence.",
            ],
        },
        "qa_decision": "ref_image_1_full_body_torso_references_available_route_not_complete",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_torso_route_not_complete",
        "tracker_item_updates": row_updates,
        "next_step": "Run Wave70 geometry and promotion hard gates, attach gate evidence to TRK-W70-0167 / ITEM-W70-0167, then continue to TRK-W70-0168 limb joint authority using Ref_Image_1/Full plus gold masks.",
    }
    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    print(
        json.dumps(
            {
                "evidence_id": EVIDENCE_ID,
                "result": payload["qa_decision"],
                "full_reference_count": full_refs["recursive_image_count"],
                "near_full_knees_to_head_count": full_refs["near_full_knees_to_head_reference_count"],
                "torso_gold_mask_count": gold_masks["torso_reference_mask_count"],
                "evidence": rel(qa_evidence_path),
                "panel": rel(panel_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
