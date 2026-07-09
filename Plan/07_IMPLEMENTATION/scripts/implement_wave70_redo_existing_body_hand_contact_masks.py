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
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
REF_IMAGE_1_MAIN = PROJECT_ROOT / "Ref_Image_1/725de85824bbe45ba4601dd4a7aed698.jpg"
REF_IMAGE_2_MAIN = PROJECT_ROOT / "Ref_Image_2/97f30ff4819b8b8206e8ce30f2355800.jpg"
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
ISO_STAMP = datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0).isoformat()
EVIDENCE_ID = f"W70_REDO_EXISTING_BODY_HAND_CONTACT_MASKS_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_redo_existing_body_hand_contact_masks.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_redo_existing_body_hand_contact_masks" / RUN_STAMP
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"
BODY_REFERENCE_MATRIX = QA_DIR / "body_reference_matrix.json"
REF_IMAGE_1_FULL_MANIFEST = QA_DIR / "ref_image_1_full_body_references.json"
REF_IMAGE_1_GOLD_MANIFEST = QA_DIR / "ref_image_1_body_mask_gold_standard.json"
REF_IMAGE_2_MANIFEST = QA_DIR / "ref_image_2_body_reference.json"
GEOMETRY_GATE = QA_DIR / f"W70_MASK_GEOMETRY_HARD_GATE_POST_REDO_EXISTING_BODY_HAND_CONTACT_REF_IMAGES_1_2_{RUN_STAMP}.json"
PROMOTION_GATE = QA_DIR / f"W70_MASK_PROMOTION_HARD_GATE_POST_REDO_EXISTING_BODY_HAND_CONTACT_REF_IMAGES_1_2_{RUN_STAMP}.json"

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]

PREREQUISITE_EVIDENCE = [
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/body_geometry_dependency_probe.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/person_instance_owner_authority.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/pose_landmark_authority.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/hand_finger_landmark_authority.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/human_part_parsing_authority.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/contact_occlusion_ownership_authority.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/body_region_geometry_authority.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/soft_body_anchor_geometry_authority.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/body_reference_matrix.json",
]

AFFECTED_TERMS = (
    "body",
    "hand",
    "finger",
    "contact",
    "support",
    "soft-body",
    "soft body",
    "torso",
    "limb",
    "feet",
    "toe",
    "skin",
    "hair",
    "clothing",
)


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


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


def update_wave70_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0177") for path in TRACKER_FILES] + [(path, "ITEM-W70-0177") for path in ITEM_FILES]
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
                row["Status"] = "Blocked_Wave70_Mask_Geometry_Gate_Not_Passed"
            if "Evidence_Path" in row:
                row["Evidence_Path"] = append_unique(row.get("Evidence_Path", ""), evidence_paths)
            if "Evidence_Required" in row:
                row["Evidence_Required"] = append_unique(row.get("Evidence_Required", ""), evidence_paths)
            if "Acceptance_Evidence" in row:
                row["Acceptance_Evidence"] = append_unique(row.get("Acceptance_Evidence", ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = "blocked_exact_local_canonical_body_geometry_unavailable_ref_images_1_2_context_available"
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    [
                        "ref_images_1_2_body_reference_context_available",
                        "blocked_exact_local_canonical_body_geometry_unavailable",
                        "redo_existing_body_hand_contact_masks_no_promotion",
                    ],
                )
            if "Notes" in row:
                row["Notes"] = append_unique(row.get("Notes", ""), [note])
        if changed:
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                writer.writerows(rows)
        updated[rel(csv_path)] = changed
    return updated


def load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"exists": False}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def body_reference_context() -> dict[str, object]:
    matrix = load_json(BODY_REFERENCE_MATRIX)
    analysis = matrix.get("body_reference_matrix_analysis", {}) if isinstance(matrix, dict) else {}
    ref2 = load_json(REF_IMAGE_2_MANIFEST)
    ref2_manifest = ref2.get("manifest", {}) if isinstance(ref2, dict) and isinstance(ref2.get("manifest"), dict) else {}
    return {
        "body_reference_matrix_path": rel(BODY_REFERENCE_MATRIX),
        "body_reference_matrix_exists": BODY_REFERENCE_MATRIX.exists(),
        "body_reference_matrix_evidence_id": matrix.get("evidence_id") if isinstance(matrix, dict) else "",
        "body_reference_matrix_qa_decision": matrix.get("qa_decision") if isinstance(matrix, dict) else "",
        "body_reference_matrix_pass": bool(analysis.get("body_reference_matrix_pass", False)) if isinstance(analysis, dict) else False,
        "source_visibility_matrix_pass": bool(analysis.get("source_visibility_matrix_pass", False)) if isinstance(analysis, dict) else False,
        "ref_image_1_full_or_near_full_reference_count": analysis.get("ref_image_1_full_body_reference_count", 0) if isinstance(analysis, dict) else 0,
        "ref_image_2_full_body_reference_count": analysis.get("ref_image_2_full_body_reference_count", 0) if isinstance(analysis, dict) else 0,
        "combined_full_or_near_full_reference_count": analysis.get("full_body_reference_count", 0) if isinstance(analysis, dict) else 0,
        "ref_image_1_gold_mask_count": analysis.get("ref_image_1_gold_mask_count", 0) if isinstance(analysis, dict) else 0,
        "ref_image_2_gold_mask_count": analysis.get("ref_image_2_gold_mask_count", ref2_manifest.get("located_overlay_count", 0)) if isinstance(analysis, dict) else ref2_manifest.get("located_overlay_count", 0),
        "combined_gold_mask_count": analysis.get("gold_mask_count", 0) if isinstance(analysis, dict) else 0,
        "ref_image_2_manifest_path": rel(REF_IMAGE_2_MANIFEST),
        "ref_image_2_manifest_exists": REF_IMAGE_2_MANIFEST.exists(),
        "ref_image_2_located_overlay_count": ref2_manifest.get("located_overlay_count", 0),
        "ref_image_1_limited_reference_policy": "Ref_Image_1/Full/New folder remains knees-to-head only and is excluded from feet/toes/ankles/lower-calf/support proof.",
    }


def affected_wave70_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    tracker_path = TRACKER_FILES[0]
    with tracker_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            haystack = " ".join(
                row.get(field, "")
                for field in ["Tracker_ID", "Task_Name", "Workstream", "Detailed_Action", "Validation_Method", "Status", "Source_Key"]
            ).lower()
            if any(term in haystack for term in AFFECTED_TERMS):
                rows.append(
                    {
                        "tracker_id": row.get("Tracker_ID", ""),
                        "status": row.get("Status", ""),
                        "task_name": row.get("Task_Name", ""),
                        "source_key": row.get("Source_Key", ""),
                    }
                )
    return rows


def redo_analysis() -> dict[str, object]:
    body_reference = load_json(QA_DIR / "body_reference_matrix.json")
    whole_body = body_reference.get("whole_body_geometry_authority", {}) if isinstance(body_reference, dict) else {}
    reference_context = body_reference_context()
    affected_rows = affected_wave70_rows()
    return {
        "canonical_body_geometry_available": False,
        "canonical_polygon_path": "",
        "canonical_segmentation_map_path": "",
        "body_reference_context_available": bool(reference_context["body_reference_matrix_exists"] and reference_context["source_visibility_matrix_pass"]),
        "body_reference_context": reference_context,
        "body_reference_matrix_pass": bool(reference_context["body_reference_matrix_pass"]),
        "whole_body_geometry_authority_pass": bool(whole_body.get("whole_body_geometry_authority_pass", False)) if isinstance(whole_body, dict) else False,
        "pose_hand_dense_landmark_or_segmentation_pass": bool(whole_body.get("pose_hand_dense_landmark_or_segmentation_pass", False)) if isinstance(whole_body, dict) else False,
        "semantic_human_part_parsing_pass": bool(whole_body.get("semantic_human_part_parsing_pass", False)) if isinstance(whole_body, dict) else False,
        "contact_occlusion_ownership_pass": bool(whole_body.get("contact_occlusion_ownership_pass", False)) if isinstance(whole_body, dict) else False,
        "body_region_geometry_pass": bool(whole_body.get("body_region_geometry_pass", False)) if isinstance(whole_body, dict) else False,
        "affected_rows_count": len(affected_rows),
        "affected_rows_sample": affected_rows[:80],
        "existing_body_hand_contact_masks_fail_closed": True,
        "mask_from_canonical_body_geometry_pass": False,
        "no_generated_output_only_promotion": True,
    }


def make_blocker_panel(source: Image.Image) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "redo_existing_body_hand_contact_masks_blocker_panel.png"
    width, height = source.size
    panel = Image.new("RGB", (width * 2, height), "white")
    panel.paste(source, (0, 0))

    marked = source.copy()
    draw = ImageDraw.Draw(marked)
    font = ImageFont.load_default()
    draw.rectangle([0, 0, width - 1, height - 1], outline=(230, 40, 40), width=6)
    draw.rectangle([20, 20, width - 20, 282], fill=(255, 255, 255), outline=(230, 40, 40), width=3)
    lines = [
        "TRK-W70-0177 blocked",
        "Ref_Image_1 + Ref_Image_2 context is available.",
        "Redo still requires canonical body geometry.",
        "No canonical body polygons are available.",
        "Body reference matrix has context but has not passed.",
        "Pose/hand/parser/contact/body dependencies blocked.",
        "Existing body/hand/contact masks remain fail-closed.",
        "No generated-output-only promotion.",
        "No masks changed.",
    ]
    y = 34
    for line in lines:
        draw.text((34, y), line, fill=(120, 0, 0), font=font)
        y += 28

    blocked_top = int(height * 0.52)
    draw.rectangle([22, blocked_top, width - 22, height - 22], outline=(230, 40, 40), width=4)
    draw.line([22, blocked_top, width - 22, height - 22], fill=(230, 40, 40), width=3)
    draw.line([width - 22, blocked_top, 22, height - 22], fill=(230, 40, 40), width=3)
    draw.text((34, blocked_top + 18), "canonical geometry missing", fill=(120, 0, 0), font=font)
    draw.text((34, blocked_top + 46), "redo cannot be performed safely", fill=(120, 0, 0), font=font)
    panel.paste(marked, (width, 0))
    panel.save(panel_path)
    return panel_path


def prepend(path: Path, heading: str, body: str) -> bool:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if heading in old[:12000]:
        return False
    path.write_text(f"{heading}\n\n{body.rstrip()}\n\n{old}", encoding="utf-8", newline="\n")
    return True


def update_hydration(evidence_paths: list[str], analysis: dict[str, object]) -> None:
    context = analysis["body_reference_context"]
    evidence_block = "\n".join(f"- `{path}`" for path in evidence_paths)
    body = f"""Re-evaluated `TRK-W70-0177` / `ITEM-W70-0177` using the corrected Ref_Image_1 plus Ref_Image_2 body-reference context.

Reference context now exists: `{context['combined_full_or_near_full_reference_count']}` full/near-full reference images and `{context['combined_gold_mask_count']}` combined gold masks are registered. Ref_Image_2 contributes `{context['ref_image_2_gold_mask_count']}` organized overlays, and the Ref_Image_1 `Full/New folder` image remains excluded from lower-leg/feet/support proof because it is knees-to-head only.

The row remains `Blocked_Wave70_Mask_Geometry_Gate_Not_Passed`: existing body/hand/contact/support/soft-body masks cannot be safely redone until canonical body geometry, parser-backed ownership, and canonical polygons exist. No masks were changed or promoted.

Expected post-0177 gates are:
- `{rel(GEOMETRY_GATE)}`
- `{rel(PROMOTION_GATE)}`

Evidence:

{evidence_block}"""
    prepend(
        HYDRATION_DIR / "CURRENT_SESSION_STATE.md",
        f"## Session State Update - 0177 Redo Body Hand Contact Ref_Image_1 Ref_Image_2 Blocker - {ISO_STAMP}",
        body + "\n\nNext local action: `TRK-W70-0178` / `ITEM-W70-0178`.",
    )
    prepend(
        HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md",
        f"## Current Pursuing Goal Update - 0177 Redo Body Hand Contact Ref_Image_1 Ref_Image_2 Blocker - {ISO_STAMP}",
        body,
    )
    prepend(
        HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md",
        f"## Resume Update - 0177 Redo Body Hand Contact Ref_Image_1 Ref_Image_2 Blocker - {ISO_STAMP}",
        body + "\n\nResume at `TRK-W70-0178` / `ITEM-W70-0178`.",
    )
    prepend(
        HYDRATION_DIR / "NEXT_ACTION.md",
        f"## Immediate Next Action - {ISO_STAMP} - Work TRK-W70-0178",
        body + "\n\nNext exact local action: implement or exactly block `TRK-W70-0178` / `ITEM-W70-0178`.",
    )
    prepend(
        HYDRATION_DIR / "QA_EVIDENCE_INDEX.md",
        f"## Wave70 0177 Redo Body Hand Contact Ref_Image_1 Ref_Image_2 Evidence - {ISO_STAMP}",
        body,
    )


def main() -> int:
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    width, height = source.size
    analysis = redo_analysis()
    panel_path = make_blocker_panel(source)

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "redo_existing_body_hand_contact_masks.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "redo_existing_body_hand_contact_masks.json"
    runtime_evidence_path = RUNTIME_DIR / "redo_existing_body_hand_contact_masks.json"

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(panel_path),
        rel(BODY_REFERENCE_MATRIX),
        rel(REF_IMAGE_1_FULL_MANIFEST),
        rel(REF_IMAGE_1_GOLD_MANIFEST),
        rel(REF_IMAGE_2_MANIFEST),
        rel(GEOMETRY_GATE),
        rel(PROMOTION_GATE),
    ]
    note = (
        f"Redo existing body/hand/contact masks {RUN_STAMP}: exact local blocker with Ref_Image_1 plus Ref_Image_2 context. "
        "Reference context exists, but canonical body geometry, pose/hand/parser/contact/body authority, and canonical polygons "
        "are unavailable, so existing body/hand/contact/support/soft-body masks remain fail-closed. No mask changed or promoted."
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note)

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "task": "Redo or exactly block existing body, hand, contact, support, and soft-body masks for TRK-W70-0177 / ITEM-W70-0177.",
        "script": SCRIPT_REL,
        "source_image": {
            "path": rel(SOURCE_IMAGE),
            "exists": SOURCE_IMAGE.exists(),
            "sha256": sha256_file(SOURCE_IMAGE),
            "dimensions": [width, height],
            "role": "historical_generated_source_not_decisive_for_ref_image_1_ref_image_2_body_reference_context",
        },
        "ref_image_1_main_reference": {
            "path": rel(REF_IMAGE_1_MAIN),
            "exists": REF_IMAGE_1_MAIN.exists(),
            "sha256": sha256_file(REF_IMAGE_1_MAIN) if REF_IMAGE_1_MAIN.exists() else "",
        },
        "ref_image_2_main_reference": {
            "path": rel(REF_IMAGE_2_MAIN),
            "exists": REF_IMAGE_2_MAIN.exists(),
            "sha256": sha256_file(REF_IMAGE_2_MAIN) if REF_IMAGE_2_MAIN.exists() else "",
        },
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": str(PROJECT_ROOT),
        },
        "prerequisite_evidence": PREREQUISITE_EVIDENCE,
        "redo_existing_body_hand_contact_analysis": analysis,
        "artifacts": {
            "blocker_panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
            "expected_post_redo_geometry_gate": rel(GEOMETRY_GATE),
            "expected_post_redo_promotion_gate": rel(PROMOTION_GATE),
        },
        "whole_body_geometry_authority": {
            "result": "blocked",
            "whole_body_geometry_authority_pass": False,
            "pose_hand_dense_landmark_or_segmentation_pass": False,
            "semantic_human_part_parsing_pass": False,
            "contact_occlusion_ownership_pass": False,
            "body_region_geometry_pass": False,
            "body_reference_context_available": bool(analysis["body_reference_context_available"]),
            "body_reference_matrix_pass": False,
            "source_image": rel(SOURCE_IMAGE),
            "source_sha256": sha256_file(SOURCE_IMAGE),
            "source_dimensions": [width, height],
            "mask_type_id": "redo_existing_body_hand_contact_masks",
            "matrix_slot_id": "BGA-016_redo_existing_body_hand_contact_masks",
            "person_instance_id": "",
            "subject_side_mapping": {},
            "models_attempted": [],
            "models_available": [],
            "pose_landmark_record_path": PREREQUISITE_EVIDENCE[2],
            "hand_landmark_record_path": PREREQUISITE_EVIDENCE[3],
            "human_part_parsing_record_path": PREREQUISITE_EVIDENCE[4],
            "sam_refinement_record_path": "",
            "contact_occlusion_record_path": PREREQUISITE_EVIDENCE[5],
            "visibility_occlusion_record_path": rel(runtime_evidence_path),
            "canonical_polygon_path": "",
            "coordinate_transform_manifest_path": "",
            "consensus_metrics": {
                "iou_against_gold_or_prior": None,
                "mean_boundary_error_px": None,
                "max_boundary_error_px": None,
                "center_drift_px": None,
                "protected_overlap_ratio": None,
                "owner_overlap_error_ratio": None,
            },
            "confidence": {
                "pose_confidence": None,
                "hand_confidence": None,
                "human_parsing_confidence": None,
                "refinement_confidence": None,
                "contact_ownership_confidence": None,
                "visibility_confidence": 0.0,
                "overall_confidence": 0.0,
            },
            "blocked_reason": (
                "blocked_wave70_mask_geometry_gate_not_passed; ref_images_1_2_reference_context_available; "
                "canonical_body_geometry_unavailable; body_reference_matrix_not_passed; upstream_whole_body_geometry_dependencies_blocked"
            ),
            "findings": [
                "This row requires existing body, hand, contact, support, and soft-body masks to be regenerated from canonical body geometry.",
                "Ref_Image_1 and Ref_Image_2 now provide body reference context and organized gold masks, so the old no-full-body-reference reason is superseded.",
                "No canonical body-part polygon or segmentation map is available for the active source or a passing reference-matrix slot.",
                "The body reference matrix has source context but has not passed, and upstream pose, hand, human-part parsing, contact ownership, and body-region evidence is blocked or insufficient.",
                "Affected body/hand/contact/support/soft-body rows therefore remain fail-closed instead of being redrawn from guessed geometry.",
                "No generated-output stability or prior broad mask was used as promotion evidence, and no mask artifact was changed.",
            ],
        },
        "redo_existing_body_hand_contact_masks": {
            "result": "blocked",
            "existing_body_hand_contact_masks_fail_closed": True,
            "mask_from_canonical_body_geometry_pass": False,
            "no_generated_output_only_promotion": True,
            "canonical_body_geometry_available": False,
            "canonical_polygon_path": "",
            "masks_changed": [],
            "masks_promoted": [],
            "blocker_status": "Blocked_Wave70_Mask_Geometry_Gate_Not_Passed",
        },
        "qa_decision": "blocked_exact_local_canonical_body_geometry_unavailable_ref_images_1_2_context_available",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_redo_blocked",
        "evidence_paths": evidence_rel_paths,
        "tracker_item_updates": row_updates,
        "next_step": "Work TRK-W70-0178 whole-body authority promotion integration locally, or provide passing canonical body geometry artifacts.",
    }
    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    update_hydration(evidence_rel_paths, analysis)
    print(json.dumps({"evidence_id": EVIDENCE_ID, "result": payload["qa_decision"], "evidence": rel(qa_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
