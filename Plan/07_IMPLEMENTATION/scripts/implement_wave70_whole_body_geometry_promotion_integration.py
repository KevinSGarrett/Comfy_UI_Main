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
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
ISO_STAMP = datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0).isoformat()
EVIDENCE_ID = f"W70_WHOLE_BODY_GEOMETRY_PROMOTION_INTEGRATION_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_whole_body_geometry_promotion_integration.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_whole_body_geometry_promotion_integration" / RUN_STAMP
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"
BODY_REFERENCE_MATRIX = QA_DIR / "body_reference_matrix.json"
REDO_BODY_HAND_CONTACT = QA_DIR / "redo_existing_body_hand_contact_masks.json"
REF_IMAGE_2_MANIFEST = QA_DIR / "ref_image_2_body_reference.json"
GEOMETRY_GATE = QA_DIR / f"W70_MASK_GEOMETRY_HARD_GATE_POST_WHOLE_BODY_GEOMETRY_PROMOTION_INTEGRATION_REF_IMAGES_1_2_{RUN_STAMP}.json"
PROMOTION_GATE = QA_DIR / f"W70_MASK_PROMOTION_HARD_GATE_POST_WHOLE_BODY_GEOMETRY_PROMOTION_INTEGRATION_REF_IMAGES_1_2_{RUN_STAMP}.json"

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
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/body_reference_matrix.json",
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/redo_existing_body_hand_contact_masks.json",
]


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
    targets = [(path, "TRK-W70-0178") for path in TRACKER_FILES] + [(path, "ITEM-W70-0178") for path in ITEM_FILES]
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
                row["Status"] = "Blocked_Body_Geometry_Authority_Not_Integrated"
            if "Evidence_Path" in row:
                row["Evidence_Path"] = append_unique(row.get("Evidence_Path", ""), evidence_paths)
            if "Evidence_Required" in row:
                row["Evidence_Required"] = append_unique(row.get("Evidence_Required", ""), evidence_paths)
            if "Acceptance_Evidence" in row:
                row["Acceptance_Evidence"] = append_unique(row.get("Acceptance_Evidence", ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = "blocked_exact_local_whole_body_geometry_authority_not_integrated_ref_images_1_2_context_available"
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    [
                        "ref_images_1_2_body_reference_context_available",
                        "blocked_exact_local_whole_body_geometry_authority_not_integrated",
                        "whole_body_geometry_promotion_integration_no_promotion",
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
    matrix_payload = load_json(BODY_REFERENCE_MATRIX)
    analysis = matrix_payload.get("body_reference_matrix_analysis", {}) if isinstance(matrix_payload, dict) else {}
    ref2_payload = load_json(REF_IMAGE_2_MANIFEST)
    ref2_manifest = ref2_payload.get("manifest", {}) if isinstance(ref2_payload, dict) and isinstance(ref2_payload.get("manifest"), dict) else {}
    return {
        "body_reference_matrix_path": rel(BODY_REFERENCE_MATRIX),
        "body_reference_matrix_exists": BODY_REFERENCE_MATRIX.exists(),
        "body_reference_matrix_evidence_id": matrix_payload.get("evidence_id") if isinstance(matrix_payload, dict) else "",
        "body_reference_matrix_qa_decision": matrix_payload.get("qa_decision") if isinstance(matrix_payload, dict) else "",
        "body_reference_matrix_pass": bool(analysis.get("body_reference_matrix_pass", False)) if isinstance(analysis, dict) else False,
        "source_visibility_matrix_pass": bool(analysis.get("source_visibility_matrix_pass", False)) if isinstance(analysis, dict) else False,
        "combined_full_or_near_full_reference_count": analysis.get("full_body_reference_count", 0) if isinstance(analysis, dict) else 0,
        "combined_gold_mask_count": analysis.get("gold_mask_count", 0) if isinstance(analysis, dict) else 0,
        "ref_image_2_gold_mask_count": analysis.get("ref_image_2_gold_mask_count", ref2_manifest.get("located_overlay_count", 0)) if isinstance(analysis, dict) else ref2_manifest.get("located_overlay_count", 0),
        "ref_image_1_limited_reference_policy": "Ref_Image_1/Full/New folder remains knees-to-head only and is excluded from feet/toes/ankles/lower-calf/support proof.",
    }


def current_gate_integration_state() -> dict[str, object]:
    body_reference = load_json(BODY_REFERENCE_MATRIX)
    redo = load_json(REDO_BODY_HAND_CONTACT)
    wb = body_reference.get("whole_body_geometry_authority", {}) if isinstance(body_reference, dict) else {}
    reference_context = body_reference_context()
    redo_section = redo.get("redo_existing_body_hand_contact_masks", {}) if isinstance(redo, dict) else {}
    return {
        "body_reference_context_available": bool(reference_context["body_reference_matrix_exists"] and reference_context["source_visibility_matrix_pass"]),
        "body_reference_context": reference_context,
        "whole_body_geometry_authority_pass": bool(wb.get("whole_body_geometry_authority_pass", False)) if isinstance(wb, dict) else False,
        "pose_hand_dense_landmark_or_segmentation_pass": bool(wb.get("pose_hand_dense_landmark_or_segmentation_pass", False)) if isinstance(wb, dict) else False,
        "semantic_human_part_parsing_pass": bool(wb.get("semantic_human_part_parsing_pass", False)) if isinstance(wb, dict) else False,
        "contact_occlusion_ownership_pass": bool(wb.get("contact_occlusion_ownership_pass", False)) if isinstance(wb, dict) else False,
        "body_region_geometry_pass": bool(wb.get("body_region_geometry_pass", False)) if isinstance(wb, dict) else False,
        "body_reference_matrix_pass": bool(reference_context["body_reference_matrix_pass"]),
        "existing_body_hand_contact_masks_fail_closed": bool(redo_section.get("existing_body_hand_contact_masks_fail_closed", False)) if isinstance(redo_section, dict) else False,
        "mask_from_canonical_body_geometry_pass": bool(redo_section.get("mask_from_canonical_body_geometry_pass", False)) if isinstance(redo_section, dict) else False,
        "body_reference_matrix_evidence": rel(BODY_REFERENCE_MATRIX),
        "redo_existing_body_hand_contact_evidence": rel(REDO_BODY_HAND_CONTACT),
    }


def count_wave70_rows() -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in TRACKER_FILES + ITEM_FILES:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        counts[rel(path)] = len(rows)
    return counts


def make_blocker_panel(source: Image.Image) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "whole_body_geometry_promotion_integration_blocker_panel.png"
    width, height = source.size
    panel = Image.new("RGB", (width * 2, height), "white")
    panel.paste(source, (0, 0))

    marked = source.copy()
    draw = ImageDraw.Draw(marked)
    font = ImageFont.load_default()
    draw.rectangle([0, 0, width - 1, height - 1], outline=(230, 40, 40), width=6)
    draw.rectangle([20, 20, width - 20, 282], fill=(255, 255, 255), outline=(230, 40, 40), width=3)
    lines = [
        "TRK-W70-0178 blocked",
        "Ref_Image_1 + Ref_Image_2 context is available.",
        "Whole-body authority cannot be integrated as pass.",
        "Required authority gates are still blocked.",
        "Body reference matrix has context but has not passed.",
        "Canonical body redo is blocked.",
        "Promotion remains fail-closed.",
        "No scheduled QA pass integration emitted.",
        "No masks promoted.",
    ]
    y = 34
    for line in lines:
        draw.text((34, y), line, fill=(120, 0, 0), font=font)
        y += 28

    blocked_top = int(height * 0.52)
    draw.rectangle([22, blocked_top, width - 22, height - 22], outline=(230, 40, 40), width=4)
    draw.line([22, blocked_top, width - 22, height - 22], fill=(230, 40, 40), width=3)
    draw.line([width - 22, blocked_top, 22, height - 22], fill=(230, 40, 40), width=3)
    draw.text((34, blocked_top + 18), "integration blocked by prerequisite evidence", fill=(120, 0, 0), font=font)
    draw.text((34, blocked_top + 46), "hard gates still enforce fail-closed state", fill=(120, 0, 0), font=font)
    panel.paste(marked, (width, 0))
    panel.save(panel_path)
    return panel_path


def prepend(path: Path, heading: str, body: str) -> bool:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if heading in old[:12000]:
        return False
    path.write_text(f"{heading}\n\n{body.rstrip()}\n\n{old}", encoding="utf-8", newline="\n")
    return True


def update_hydration(evidence_paths: list[str], integration_state: dict[str, object]) -> None:
    context = integration_state["body_reference_context"]
    evidence_block = "\n".join(f"- `{path}`" for path in evidence_paths)
    body = f"""Re-evaluated `TRK-W70-0178` / `ITEM-W70-0178` whole-body promotion/scheduled-QA integration using Ref_Image_1 plus Ref_Image_2 context.

Reference context exists: `{context['combined_full_or_near_full_reference_count']}` full/near-full reference images and `{context['combined_gold_mask_count']}` combined gold masks are registered. Ref_Image_2 contributes `{context['ref_image_2_gold_mask_count']}` organized overlays. This is enough to remove the old missing-reference reason, but not enough to emit a promotion pass.

The row remains `Blocked_Body_Geometry_Authority_Not_Integrated`: whole-body authority, body-reference-matrix pass, canonical polygons, parser-backed ownership, and redo-from-canonical geometry are still not passing. Promotion and scheduled QA remain fail-closed. No masks were changed or promoted.

Expected post-0178 gates are:
- `{rel(GEOMETRY_GATE)}`
- `{rel(PROMOTION_GATE)}`

Evidence:

{evidence_block}"""
    prepend(
        HYDRATION_DIR / "CURRENT_SESSION_STATE.md",
        f"## Session State Update - 0178 Whole Body Promotion Integration Ref_Image_1 Ref_Image_2 Blocker - {ISO_STAMP}",
        body + "\n\nNext local action: inspect the next tracker/item row after `TRK-W70-0178`.",
    )
    prepend(
        HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md",
        f"## Current Pursuing Goal Update - 0178 Whole Body Promotion Integration Ref_Image_1 Ref_Image_2 Blocker - {ISO_STAMP}",
        body,
    )
    prepend(
        HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md",
        f"## Resume Update - 0178 Whole Body Promotion Integration Ref_Image_1 Ref_Image_2 Blocker - {ISO_STAMP}",
        body + "\n\nResume by selecting the next not-complete Wave70/project row after `TRK-W70-0178`.",
    )
    prepend(
        HYDRATION_DIR / "NEXT_ACTION.md",
        f"## Immediate Next Action - {ISO_STAMP} - Inspect Next Row After TRK-W70-0178",
        body + "\n\nNext exact local action: inspect tracker/item rows after `TRK-W70-0178` and continue with the next required local-first task.",
    )
    prepend(
        HYDRATION_DIR / "QA_EVIDENCE_INDEX.md",
        f"## Wave70 0178 Whole Body Promotion Integration Ref_Image_1 Ref_Image_2 Evidence - {ISO_STAMP}",
        body,
    )


def main() -> int:
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    width, height = source.size
    integration_state = current_gate_integration_state()
    row_counts = count_wave70_rows()
    panel_path = make_blocker_panel(source)

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "whole_body_geometry_promotion_integration.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "whole_body_geometry_promotion_integration.json"
    runtime_evidence_path = RUNTIME_DIR / "whole_body_geometry_promotion_integration.json"

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(panel_path),
        rel(BODY_REFERENCE_MATRIX),
        rel(REDO_BODY_HAND_CONTACT),
        rel(REF_IMAGE_2_MANIFEST),
        rel(GEOMETRY_GATE),
        rel(PROMOTION_GATE),
    ]
    note = (
        f"Whole-body geometry promotion integration {RUN_STAMP}: exact local blocker with Ref_Image_1 plus Ref_Image_2 context. "
        "Reference context exists, but whole-body authority cannot be integrated as pass because pose/hand/parser/contact/body/reference-matrix "
        "authority, canonical polygons, and redo-from-canonical geometry remain blocked. Promotion and scheduled QA must remain fail-closed. No masks promoted."
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note)

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "task": "Integrate or exactly block whole-body authority into Wave70 promotion and scheduled QA gates for TRK-W70-0178 / ITEM-W70-0178.",
        "script": SCRIPT_REL,
        "source_image": {
            "path": rel(SOURCE_IMAGE),
            "exists": SOURCE_IMAGE.exists(),
            "sha256": sha256_file(SOURCE_IMAGE),
            "dimensions": [width, height],
            "role": "historical_generated_source_not_decisive_for_ref_image_1_ref_image_2_body_reference_context",
        },
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": str(PROJECT_ROOT),
        },
        "prerequisite_evidence": PREREQUISITE_EVIDENCE,
        "wave70_row_counts": row_counts,
        "artifacts": {
            "blocker_panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
            "expected_post_integration_geometry_gate": rel(GEOMETRY_GATE),
            "expected_post_integration_promotion_gate": rel(PROMOTION_GATE),
        },
        "whole_body_geometry_authority": {
            "result": "blocked",
            "whole_body_geometry_authority_pass": False,
            "pose_hand_dense_landmark_or_segmentation_pass": False,
            "semantic_human_part_parsing_pass": False,
            "contact_occlusion_ownership_pass": False,
            "body_region_geometry_pass": False,
            "body_reference_context_available": bool(integration_state["body_reference_context_available"]),
            "body_reference_matrix_pass": False,
            "source_image": rel(SOURCE_IMAGE),
            "source_sha256": sha256_file(SOURCE_IMAGE),
            "source_dimensions": [width, height],
            "mask_type_id": "whole_body_geometry_promotion_integration",
            "matrix_slot_id": "BGA-017_whole_body_geometry_promotion_integration",
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
                "blocked_body_geometry_authority_not_integrated; ref_images_1_2_reference_context_available; "
                "prerequisite_whole_body_authority_gates_blocked; body_reference_matrix_not_passed; canonical_body_geometry_unavailable"
            ),
            "findings": [
                "Whole-body authority integration cannot be marked pass because required whole-body authority gates are false.",
                "Ref_Image_1 and Ref_Image_2 provide body reference context and organized gold masks, so the old missing-reference reason is superseded.",
                "The body reference matrix has source context but has not passed, and canonical body geometry redo is blocked.",
                "Wave70 promotion and scheduled QA must continue to require whole-body authority before body, hand, contact, support, soft-body, temporal, or generalized mask promotion.",
                "No generated-output stability, broad body mask, or prior mask artifact was promoted through this integration evidence.",
                "No mask artifact was changed or promoted.",
            ],
        },
        "whole_body_geometry_promotion_integration": {
            "result": "blocked",
            "blocker_status": "Blocked_Body_Geometry_Authority_Not_Integrated",
            "whole_body_geometry_authority_pass": False,
            "wave70_mask_geometry_gate_pass": False,
            "wave70_mask_promotion_gate_pass": False,
            "scheduled_qa_integration_pass": False,
            "promotion_gate_integration_pass": False,
            "prerequisite_gate_state": integration_state,
            "fail_closed_policy_confirmed": True,
            "masks_changed": [],
            "masks_promoted": [],
            "completion_allowed": False,
        },
        "qa_decision": "blocked_exact_local_whole_body_geometry_authority_not_integrated_ref_images_1_2_context_available",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_integration_blocked",
        "evidence_paths": evidence_rel_paths,
        "tracker_item_updates": row_updates,
        "next_step": "Return to the next local project task selected from Plan/Items and Plan/Tracker; Wave70 whole-body authority rows through BGA-017 are now fail-closed with evidence.",
    }
    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    update_hydration(evidence_rel_paths, integration_state)
    print(json.dumps({"evidence_id": EVIDENCE_ID, "result": payload["qa_decision"], "evidence": rel(qa_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
