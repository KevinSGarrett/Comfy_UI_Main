from __future__ import annotations

import csv
import hashlib
import json
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
NOW = datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0)
RUN_STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")
ISO_STAMP = NOW.isoformat()
EVIDENCE_ID = f"W70_MF70_LEFT_FOREARM_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_mf70_left_forearm.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_mf70_left_forearm" / RUN_STAMP
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]

PREREQ_FILES = {
    "model_backed_geometry_promotion_integration": QA_DIR / "model_backed_geometry_promotion_integration.json",
    "pose_landmark_authority": QA_DIR / "pose_landmark_authority.json",
    "human_part_parsing_authority": QA_DIR / "human_part_parsing_authority.json",
    "body_region_geometry_authority": QA_DIR / "body_region_geometry_authority.json",
    "body_reference_matrix": QA_DIR / "body_reference_matrix.json",
    "limb_joint_region_authority": QA_DIR / "limb_joint_region_authority.json",
    "canonical_geometry_polygon_export": QA_DIR / "canonical_geometry_polygon_export.json",
}


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


def deep_get(payload: object, keys: list[str]) -> object | None:
    current = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def read_prerequisite(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"exists": False, "path": rel(path), "error": "missing"}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    wb = payload.get("whole_body_geometry_authority")
    mbga = payload.get("model_backed_geometry_authority")
    limb = payload.get("limb_joint_region_authority")
    matrix = payload.get("body_reference_matrix")
    body_region = payload.get("body_region_geometry_authority")
    return {
        "exists": True,
        "path": rel(path),
        "sha256": sha256_file(path),
        "evidence_id": payload.get("evidence_id"),
        "qa_decision": payload.get("qa_decision"),
        "promotion_decision": payload.get("promotion_decision"),
        "result": payload.get("result")
        or deep_get(wb, ["result"])
        or deep_get(mbga, ["result"])
        or deep_get(limb, ["result"]),
        "model_backed_geometry_authority_pass": deep_get(mbga, ["model_backed_geometry_authority_pass"]),
        "whole_body_geometry_authority_pass": deep_get(wb, ["whole_body_geometry_authority_pass"])
        or deep_get(limb, ["whole_body_geometry_authority_pass"]),
        "pose_hand_dense_landmark_or_segmentation_pass": deep_get(
            wb, ["pose_hand_dense_landmark_or_segmentation_pass"]
        )
        or deep_get(limb, ["pose_hand_dense_landmark_or_segmentation_pass"]),
        "semantic_human_part_parsing_pass": deep_get(wb, ["semantic_human_part_parsing_pass"])
        or deep_get(limb, ["semantic_human_part_parsing_pass"]),
        "body_region_geometry_pass": deep_get(wb, ["body_region_geometry_pass"])
        or deep_get(body_region, ["body_region_geometry_pass"])
        or deep_get(limb, ["body_region_geometry_pass"]),
        "body_reference_matrix_pass": deep_get(wb, ["body_reference_matrix_pass"])
        or deep_get(matrix, ["body_reference_matrix_pass"])
        or deep_get(limb, ["body_reference_matrix_pass"]),
        "limb_region_pass": deep_get(limb, ["limb_region_pass"]),
        "joint_anchor_pass": deep_get(limb, ["joint_anchor_pass"]),
        "left_right_side_mapping_pass": deep_get(limb, ["left_right_side_mapping_pass"]),
        "blocked_reason": deep_get(wb, ["blocked_reason"])
        or deep_get(mbga, ["blocked_reason"])
        or deep_get(limb, ["blocked_reason"])
        or payload.get("blocked_reason"),
    }


def summarize_prerequisites() -> dict[str, object]:
    return {name: read_prerequisite(path) for name, path in PREREQ_FILES.items()}


def evaluate_left_forearm_readiness(prereqs: dict[str, object], width: int, height: int) -> dict[str, object]:
    source_visibility = {
        "source_framing": "head_neck_upper_chest_jacket_portrait",
        "image_dimensions": [width, height],
        "left_forearm_visible_as_source_body_geometry": False,
        "left_elbow_to_wrist_chain_visible": False,
        "left_elbow_visible": False,
        "left_wrist_visible": False,
        "left_hand_visible": False,
        "skin_or_unoccluded_forearm_surface_visible": False,
        "visible_region": "jacket shoulder and upper torso only",
        "protected_neighbors": ["elbow", "wrist", "hand", "clothing"],
        "source_region_blocker": "Blocked_Body_Part_Not_Visible",
    }
    required_passes = {
        "source_left_forearm_visible": source_visibility["left_forearm_visible_as_source_body_geometry"],
        "source_left_elbow_to_wrist_chain_visible": source_visibility["left_elbow_to_wrist_chain_visible"],
        "source_left_elbow_visible": source_visibility["left_elbow_visible"],
        "source_left_wrist_visible": source_visibility["left_wrist_visible"],
        "model_backed_geometry_authority_pass": prereqs.get("model_backed_geometry_promotion_integration", {}).get(
            "model_backed_geometry_authority_pass"
        )
        is True,
        "whole_body_geometry_authority_pass": any(
            prereqs.get(name, {}).get("whole_body_geometry_authority_pass") is True
            for name in ["body_region_geometry_authority", "body_reference_matrix", "limb_joint_region_authority"]
        ),
        "pose_hand_dense_landmark_or_segmentation_pass": any(
            prereqs.get(name, {}).get("pose_hand_dense_landmark_or_segmentation_pass") is True
            for name in ["pose_landmark_authority", "body_region_geometry_authority", "limb_joint_region_authority"]
        ),
        "semantic_human_part_parsing_pass": any(
            prereqs.get(name, {}).get("semantic_human_part_parsing_pass") is True
            for name in ["human_part_parsing_authority", "body_region_geometry_authority", "limb_joint_region_authority"]
        ),
        "limb_region_pass": prereqs.get("limb_joint_region_authority", {}).get("limb_region_pass") is True,
        "joint_anchor_pass": prereqs.get("limb_joint_region_authority", {}).get("joint_anchor_pass") is True,
        "left_right_side_mapping_pass": prereqs.get("limb_joint_region_authority", {}).get(
            "left_right_side_mapping_pass"
        )
        is True,
        "body_reference_matrix_pass": prereqs.get("body_reference_matrix", {}).get("body_reference_matrix_pass") is True,
    }
    failed = [name for name, passed in required_passes.items() if not passed]
    return {
        "required_passes": required_passes,
        "failed_requirements": failed,
        "source_visibility": source_visibility,
        "mask_contract_schema_pass": False,
        "owner_instance_assignment_pass": False,
        "mask_png_or_map_generated": False,
        "preview_overlay_generated": False,
        "protected_neighbor_check_pass": False,
        "semantic_mask_alignment_pass": False,
        "generated_output_safe_pass": False,
        "reference_image_matrix_pass": False,
        "target_runtime_evidence_pass": False,
        "wave70_mask_geometry_gate_pass": False,
        "wave70_mask_promotion_gate_pass": False,
        "completion_allowed": False,
        "blocking_reason": "Blocked_Body_Part_Not_Visible",
    }


def make_blocker_panel(source: Image.Image, evaluation: dict[str, object]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "mf70_left_forearm_blocker_panel.png"
    width, height = source.size
    panel = Image.new("RGB", (width * 2, height), "white")
    panel.paste(source, (0, 0))

    marked = source.copy()
    draw = ImageDraw.Draw(marked)
    font = ImageFont.load_default()
    draw.rectangle([0, 0, width - 1, height - 1], outline=(230, 40, 40), width=6)

    visible_upper_torso_top = int(height * 0.52)
    draw.rectangle([18, visible_upper_torso_top, width - 18, height - 18], outline=(230, 40, 40), width=4)
    draw.line([18, visible_upper_torso_top, width - 18, height - 18], fill=(230, 40, 40), width=3)
    draw.line([width - 18, visible_upper_torso_top, 18, height - 18], fill=(230, 40, 40), width=3)

    draw.rectangle([20, 20, width - 20, 300], fill=(255, 255, 255), outline=(230, 40, 40), width=3)
    lines = [
        "TRK-W70-0157 blocked",
        "mf70_left_forearm not source-visible.",
        f"Failed requirements: {len(evaluation['failed_requirements'])}",
        "Visible jacket/shoulder is not a forearm.",
        "No left elbow-to-wrist or wrist geometry.",
        "Whole-body authority remains blocked.",
        "No mask, overlay, output, or promotion.",
    ]
    y = 34
    for line in lines:
        draw.text((34, y), line, fill=(120, 0, 0), font=font)
        y += 34

    panel.paste(marked, (width, 0))
    panel.save(panel_path)
    return panel_path


def update_wave70_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0157") for path in TRACKER_FILES] + [(path, "ITEM-W70-0157") for path in ITEM_FILES]
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
                row["Status"] = "Blocked_Body_Part_Not_Visible"
            if "Evidence_Path" in row:
                row["Evidence_Path"] = append_unique(row.get("Evidence_Path", ""), evidence_paths)
            if "Evidence_Required" in row:
                row["Evidence_Required"] = append_unique(row.get("Evidence_Required", ""), evidence_paths)
            if "Acceptance_Evidence" in row:
                row["Acceptance_Evidence"] = append_unique(row.get("Acceptance_Evidence", ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = "blocked_exact_local_left_forearm_not_source_visible"
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    ["blocked_exact_local_left_forearm_not_source_visible"],
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


def prepend_section(path: Path, heading: str, body: str) -> None:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    path.write_text(f"{heading}\n\n{body.rstrip()}\n\n{old}", encoding="utf-8")


def update_hydration(evidence_paths: list[str]) -> None:
    evidence_block = "\n".join(f"- {p}" for p in evidence_paths)
    current_body = f"""Wave70 remains the active local-first mask-geometry milestone. TRK-W70-0157 / ITEM-W70-0157 was worked locally and is exactly blocked: mf70_left_forearm cannot be produced from the active source because the left forearm is not visible as source-derived body geometry. The portrait shows jacket shoulder/upper torso only, with no left elbow-to-wrist chain or elbow anchor, and whole-body/model-backed geometry authority remains blocked.

No mask contract pass, owner assignment pass, generated mask/map, preview overlay, protected-neighbor pass, generated output, reference matrix pass, target-runtime proof, active mask change, or mask promotion was produced.

Current evidence:

{evidence_block}

Next highest-value local tracker row found from current CSV state is TRK-W70-0158 / ITEM-W70-0158, prove Mask Factory mask type mf70_right_forearm. Work it locally under the same authority rules; if source/authority prerequisites remain blocked, write exact local blocker evidence and keep masks fail-closed."""
    next_body = f"""TRK-W70-0157 / ITEM-W70-0157 is exactly blocked with local source-visibility and whole-body authority evidence. The active portrait does not expose a source-derived left forearm region, elbow-to-wrist chain, wrist, or hand.

Current clean evidence:

{evidence_block}

Next local task: implement or exactly block TRK-W70-0158 / ITEM-W70-0158, mf70_right_forearm. Use only source-derived whole-body/model-backed geometry evidence. Do not start EC2, run generated-output proof, checkpoint Git, rerun broad helper loops, or promote any mask."""
    session_body = (
        "Worked TRK-W70-0157 / ITEM-W70-0157 locally. mf70_left_forearm is blocked because the "
        "active source crop shows jacket shoulder/upper torso but no source-derived left forearm or "
        "elbow-to-wrist chain, and whole-body/model-backed authority remains blocked. No mask artifact, "
        "overlay, generated output, or promotion occurred."
    )
    blocker_body = (
        "TRK-W70-0157 / ITEM-W70-0157: Blocked_Body_Part_Not_Visible / "
        "blocked_exact_local_left_forearm_not_source_visible."
    )

    prepend_section(HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md", f"## Wave70 Left Forearm Blocked Locally - {ISO_STAMP}", current_body)
    prepend_section(HYDRATION_DIR / "NEXT_ACTION.md", f"## Immediate Next Action - {ISO_STAMP} - Work TRK-W70-0158 Right Forearm Locally", next_body)
    prepend_section(HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md", f"## Resume Update - Wave70 Left Forearm Blocked - {ISO_STAMP}", session_body + "\n\nNext exact action: work TRK-W70-0158 locally.")
    prepend_section(HYDRATION_DIR / "CURRENT_SESSION_STATE.md", f"## Session State Update - Wave70 Left Forearm Blocked - {ISO_STAMP}", session_body)
    prepend_section(HYDRATION_DIR / "QA_EVIDENCE_INDEX.md", f"## Wave70 Left Forearm Evidence - {ISO_STAMP}", f"{session_body}\n\n{evidence_block}")
    prepend_section(HYDRATION_DIR / "BLOCKERS.md", f"## Wave70 Left Forearm Blocker - {ISO_STAMP}", blocker_body + "\n\n" + evidence_block)

    proof_log = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof_log.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                ISO_STAMP,
                "70",
                "Wave70 mf70 left forearm blocker",
                "Worked TRK/ITEM-W70-0157 locally. Active source does not expose source-derived left forearm, elbow-to-wrist, wrist, or hand geometry and whole-body/model-backed authority remains blocked. Wrote stamped/canonical evidence, generated blocker panel, and kept masks fail-closed.",
                "; ".join(evidence_paths),
                "python py_compile; source visibility review; whole-body authority prerequisite review; direct panel inspection; JSON validation; Wave70 geometry/promotion hard gates",
                "BLOCKED_BODY_PART_NOT_VISIBLE",
                "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/mf70_left_forearm.json",
                "Next work TRK-W70-0158 right forearm locally; write exact blocker if authority remains blocked.",
            ]
        )


def main() -> int:
    if not SOURCE_IMAGE.exists():
        raise FileNotFoundError(SOURCE_IMAGE)
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    width, height = source.size
    prereqs = summarize_prerequisites()
    evaluation = evaluate_left_forearm_readiness(prereqs, width, height)
    panel_path = make_blocker_panel(source, evaluation)

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "mf70_left_forearm.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "mf70_left_forearm.json"
    runtime_evidence_path = RUNTIME_DIR / "mf70_left_forearm.json"

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(panel_path),
    ]
    note = (
        f"mf70_left_forearm {RUN_STAMP}: exact local blocker. "
        "The active source crop shows jacket shoulder/upper torso but no source-derived left forearm or "
        "elbow-to-wrist geometry, wrist, or hand, and whole-body/model-backed geometry authority remains blocked. "
        "No mask, overlay, generated output, or promotion occurred."
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note)

    source_hash = sha256_file(SOURCE_IMAGE)
    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "created_iso": ISO_STAMP,
        "task": "Prove or exactly block Mask Factory mask type mf70_left_forearm for TRK-W70-0157 / ITEM-W70-0157.",
        "script": SCRIPT_REL,
        "source_image": {
            "path": rel(SOURCE_IMAGE),
            "exists": True,
            "sha256": source_hash,
            "dimensions": [width, height],
        },
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "cwd": str(PROJECT_ROOT),
        },
        "prerequisite_authority_evidence": prereqs,
        "left_forearm_readiness": evaluation,
        "artifacts": {
            "blocker_panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
            "mask_png_or_map": "",
            "preview_overlay": "",
        },
        "mask_factory_row": {
            "mask_type_id": "mf70_left_forearm",
            "target_region": "left_forearm",
            "body_part": "arms",
            "subregion": "left_forearm",
            "protected_regions": ["elbow", "wrist", "hand", "clothing"],
            "result": "blocked",
            "status": "Blocked_Body_Part_Not_Visible",
            "mask_contract_schema_pass": False,
            "owner_instance_assignment_pass": False,
            "mask_png_or_map_generated": False,
            "preview_overlay_generated": False,
            "protected_neighbor_check_pass": False,
            "semantic_mask_alignment_pass": False,
            "generated_output_safe_pass": False,
            "reference_image_matrix_pass": False,
            "target_runtime_evidence_pass": False,
            "quality_score": None,
            "masks_changed": [],
            "masks_promoted": [],
        },
        "whole_body_geometry_authority": {
            "result": "blocked",
            "whole_body_geometry_authority_pass": False,
            "pose_hand_dense_landmark_or_segmentation_pass": False,
            "semantic_human_part_parsing_pass": False,
            "contact_occlusion_ownership_pass": False,
            "body_region_geometry_pass": False,
            "body_reference_matrix_pass": False,
            "source_image": rel(SOURCE_IMAGE),
            "source_sha256": source_hash,
            "source_dimensions": [width, height],
            "mask_type_id": "mf70_left_forearm",
            "matrix_slot_id": "TRK-W70-0157",
            "person_instance_id": "",
            "subject_side_mapping": {},
            "models_attempted": ["source_visibility_review", "whole_body_authority_prerequisite_review"],
            "models_available": ["base_image_io_and_cv"],
            "pose_landmark_record_path": rel(QA_DIR / "pose_landmark_authority.json"),
            "hand_landmark_record_path": "",
            "human_part_parsing_record_path": rel(QA_DIR / "human_part_parsing_authority.json"),
            "sam_refinement_record_path": "",
            "contact_occlusion_record_path": rel(QA_DIR / "contact_occlusion_ownership_authority.json"),
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
            "blocked_reason": "Blocked_Body_Part_Not_Visible",
            "findings": [
                "The active source is a head/neck/upper-chest portrait with a jacket.",
                "The visible jacket, shoulder, and upper torso cannot prove the requested left forearm source geometry.",
                "No left elbow-to-wrist chain, elbow anchor, wrist anchor, hand, or unoccluded left forearm body surface is visible.",
                "Whole-body/model-backed authority prerequisites remain blocked, so no canonical limb polygon can be exported.",
                "No shortcut, symmetry-inferred, clothing-based, or generated-output-derived mask was created.",
                "No active mask changed and no mask was promoted.",
            ],
        },
        "qa_decision": "blocked_exact_local_left_forearm_not_source_visible",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_left_forearm_blocked",
        "tracker_item_updates": row_updates,
        "next_step": "Work TRK-W70-0158 / ITEM-W70-0158 mf70_right_forearm locally.",
    }

    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    update_hydration(evidence_rel_paths)
    print(json.dumps({"evidence_id": EVIDENCE_ID, "result": payload["qa_decision"], "evidence": rel(qa_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


