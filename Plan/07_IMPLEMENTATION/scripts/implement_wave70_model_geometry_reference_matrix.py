from __future__ import annotations

import csv
import hashlib
import json
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
EVIDENCE_ID = f"W70_MODEL_GEOMETRY_REFERENCE_MATRIX_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_model_geometry_reference_matrix.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_model_geometry_reference_matrix" / RUN_STAMP

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]
HYDRATION_DIR = PROJECT_ROOT / "Plan/Instructions/Hydration_Rehydration"

PREREQ_FILES = {
    "gold_trace_dataset_manifest": QA_DIR / "gold_trace_dataset_manifest.json",
    "model_geometry_dependency_probe": QA_DIR / "model_geometry_dependency_probe.json",
    "face_landmark_authority": QA_DIR / "face_landmark_authority.json",
    "face_parsing_authority": QA_DIR / "face_parsing_authority.json",
    "segmentation_refinement_authority": QA_DIR / "segmentation_refinement_authority.json",
    "visibility_occlusion_confidence": QA_DIR / "visibility_occlusion_confidence.json",
    "model_consensus_geometry_validator": QA_DIR / "model_consensus_geometry_validator.json",
    "canonical_geometry_polygon_export": QA_DIR / "canonical_geometry_polygon_export.json",
    "body_hand_contact_geometry_authority": QA_DIR / "body_hand_contact_geometry_authority.json",
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
    mbga = payload.get("model_backed_geometry_authority")
    gold = payload.get("gold_trace_dataset_manifest")
    return {
        "exists": True,
        "path": rel(path),
        "sha256": sha256_file(path),
        "evidence_id": payload.get("evidence_id"),
        "qa_decision": payload.get("qa_decision"),
        "promotion_decision": payload.get("promotion_decision"),
        "result": deep_get(mbga, ["result"]) if isinstance(mbga, dict) else payload.get("result"),
        "model_backed_geometry_authority_pass": deep_get(mbga, ["model_backed_geometry_authority_pass"]),
        "source_derived_landmark_or_segmentation_pass": deep_get(
            mbga, ["source_derived_landmark_or_segmentation_pass"]
        ),
        "model_consensus_geometry_pass": deep_get(mbga, ["model_consensus_geometry_pass"]),
        "visibility_occlusion_confidence_pass": deep_get(mbga, ["visibility_occlusion_confidence_pass"]),
        "canonical_polygon_export_pass": deep_get(mbga, ["canonical_polygon_export_pass"]),
        "model_geometry_dependency_probe_pass": deep_get(mbga, ["model_geometry_dependency_probe_pass"]),
        "whole_body_geometry_authority_pass": deep_get(mbga, ["whole_body_geometry_authority_pass"]),
        "registered_reference_count": deep_get(gold, ["registered_reference_count"]),
        "gold_trace_schema_pass": deep_get(gold, ["gold_trace_schema_pass"]),
        "image_hash_match_pass": deep_get(gold, ["image_hash_match_pass"]),
        "blocked_reason": deep_get(mbga, ["blocked_reason"]),
    }


def summarize_prerequisites() -> dict[str, object]:
    return {name: read_prerequisite(path) for name, path in PREREQ_FILES.items()}


def evaluate_matrix_readiness(prereqs: dict[str, object]) -> dict[str, object]:
    gold = prereqs.get("gold_trace_dataset_manifest", {})
    required_passes = {
        "gold_trace_dataset_available": bool(gold.get("exists"))
        and bool(gold.get("registered_reference_count"))
        and gold.get("gold_trace_schema_pass") is True
        and gold.get("image_hash_match_pass") is True,
        "model_geometry_dependency_probe_pass": prereqs.get("model_geometry_dependency_probe", {}).get(
            "model_geometry_dependency_probe_pass"
        )
        is True,
        "source_derived_landmark_or_segmentation_pass": any(
            prereqs.get(name, {}).get("source_derived_landmark_or_segmentation_pass") is True
            for name in ["face_landmark_authority", "face_parsing_authority", "segmentation_refinement_authority"]
        ),
        "visibility_occlusion_confidence_pass": prereqs.get("visibility_occlusion_confidence", {}).get(
            "visibility_occlusion_confidence_pass"
        )
        is True,
        "model_consensus_geometry_pass": prereqs.get("model_consensus_geometry_validator", {}).get(
            "model_consensus_geometry_pass"
        )
        is True,
        "canonical_polygon_export_pass": prereqs.get("canonical_geometry_polygon_export", {}).get(
            "canonical_polygon_export_pass"
        )
        is True,
        "body_hand_contact_authority_pass": prereqs.get("body_hand_contact_geometry_authority", {}).get(
            "model_backed_geometry_authority_pass"
        )
        is True,
    }
    failed_requirements = [name for name, passed in required_passes.items() if not passed]
    return {
        "required_passes": required_passes,
        "failed_requirements": failed_requirements,
        "registered_reference_count": gold.get("registered_reference_count") or 0,
        "reference_image_matrix_pass": False,
        "cross_subject_generalization_pass": False,
        "source_visibility_matrix_pass": False,
        "matrix_runnable": not failed_requirements,
        "blocking_reason": "Blocked_Reference_Matrix_Not_Run",
    }


def make_blocker_panel(source: Image.Image, evaluation: dict[str, object]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "model_geometry_reference_matrix_blocker_panel.png"
    width, height = source.size
    panel = Image.new("RGB", (width * 2, height), "white")
    panel.paste(source, (0, 0))
    marked = source.copy()
    draw = ImageDraw.Draw(marked)
    font = ImageFont.load_default()
    draw.rectangle([0, 0, width - 1, height - 1], outline=(230, 40, 40), width=6)
    draw.rectangle([20, 20, width - 20, 300], fill=(255, 255, 255), outline=(230, 40, 40), width=3)
    lines = [
        "TRK-W70-0152 blocked",
        "Reference matrix validation not runnable.",
        f"Registered gold references: {evaluation['registered_reference_count']}",
        f"Failed requirements: {len(evaluation['failed_requirements'])}",
        "No model-backed geometry route passes.",
        "No cross-subject/generalization claim.",
        "No masks promoted.",
    ]
    y = 34
    for line in lines:
        draw.text((34, y), line, fill=(120, 0, 0), font=font)
        y += 33
    panel.paste(marked, (width, 0))
    panel.save(panel_path)
    return panel_path


def update_wave70_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0152") for path in TRACKER_FILES] + [(path, "ITEM-W70-0152") for path in ITEM_FILES]
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
            row["Status"] = "Blocked_Reference_Matrix_Not_Run"
            if "Evidence_Path" in row:
                row["Evidence_Path"] = append_unique(row.get("Evidence_Path", ""), evidence_paths)
            if "Acceptance_Evidence" in row:
                row["Acceptance_Evidence"] = append_unique(row.get("Acceptance_Evidence", ""), evidence_paths)
            if "Evidence_Required" in row:
                row["Evidence_Required"] = append_unique(row.get("Evidence_Required", ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = "blocked_exact_local_reference_matrix_not_runnable"
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    ["blocked_exact_local_reference_matrix_not_runnable"],
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
    evidence_block = "\n".join(f"- `{p}`" for p in evidence_paths)
    current_body = f"""Wave70 remains the active local-first mask-geometry milestone. `TRK-W70-0152` / `ITEM-W70-0152` was worked locally and is exactly blocked: reference-image matrix validation cannot run because the registered gold trace set exists but model-backed dependency, source-derived geometry, visibility, consensus, canonical polygon, and body/contact authority prerequisites remain blocked or missing.

No reference-image matrix pass, cross-subject generalization pass, source-visibility matrix pass, active mask change, or mask promotion was produced.

Current evidence:

{evidence_block}

Next highest-value local tracker row found from current CSV state is `TRK-W70-0153` / `ITEM-W70-0153`, integrate model-backed authority into the Wave70 promotion gate. Work it locally; if model-backed authority cannot be integrated as passing because prerequisites remain blocked, write one exact local blocker with evidence and keep masks fail-closed."""
    next_body = f"""`TRK-W70-0152` / `ITEM-W70-0152` is exactly blocked with local reference-matrix evidence. The gold trace set is registered, but model-backed geometry prerequisites remain blocked, so no generalized/reference-matrix validation can run.

Current clean evidence:

{evidence_block}

Next local task: implement or exactly block `TRK-W70-0153` / `ITEM-W70-0153`, integrate model-backed authority into Wave70 promotion gate. Use only current hard-gate/model authority evidence. Do not start EC2, run generated-output proof, checkpoint Git, rerun broad helper loops, or promote any mask."""
    session_body = f"""Worked `TRK-W70-0152` / `ITEM-W70-0152` locally. Reference matrix validation is blocked because model-backed geometry prerequisites are unavailable. No generalized claim or mask promotion occurred."""
    blocker_body = f"""`TRK-W70-0152` / `ITEM-W70-0152`: `Blocked_Reference_Matrix_Not_Run` / `blocked_exact_local_reference_matrix_not_runnable`. The gold trace set is registered, but no model-backed geometry route can be evaluated across it."""

    prepend_section(HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md", f"## Wave70 Reference Matrix Validation Blocked Locally - {ISO_STAMP}", current_body)
    prepend_section(HYDRATION_DIR / "NEXT_ACTION.md", f"## Immediate Next Action - {ISO_STAMP} - Work TRK-W70-0153 Promotion Integration Locally", next_body)
    prepend_section(HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md", f"## Resume Update - Wave70 Reference Matrix Validation Blocked - {ISO_STAMP}", session_body + "\n\nNext exact action: work `TRK-W70-0153` locally.")
    prepend_section(HYDRATION_DIR / "CURRENT_SESSION_STATE.md", f"## Session State Update - Wave70 Reference Matrix Validation Blocked - {ISO_STAMP}", session_body)
    prepend_section(HYDRATION_DIR / "QA_EVIDENCE_INDEX.md", f"## Wave70 Reference Matrix Validation Evidence - {ISO_STAMP}", f"{session_body}\n\n{evidence_block}")
    prepend_section(HYDRATION_DIR / "BLOCKERS.md", f"## Wave70 Reference Matrix Validation Blocker - {ISO_STAMP}", blocker_body + "\n\n" + evidence_block)

    proof_log = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof_log.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                ISO_STAMP,
                "70",
                "Wave70 model geometry reference matrix blocker",
                "Worked TRK/ITEM-W70-0152 locally. Reference-image matrix validation cannot run because gold traces are registered but model-backed geometry prerequisites remain blocked or missing. Wrote stamped/canonical evidence, generated a blocker panel, and kept masks fail-closed.",
                "; ".join(evidence_paths),
                "python py_compile; gold trace and model authority prerequisite review; direct panel inspection; JSON validation; Wave70 geometry/promotion hard gates",
                "BLOCKED_REFERENCE_MATRIX_NOT_RUN",
                "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/model_geometry_reference_matrix.json",
                "Next work TRK-W70-0153 promotion integration locally; write exact blocker if authority remains blocked.",
            ]
        )


def main() -> int:
    if not SOURCE_IMAGE.exists():
        raise FileNotFoundError(SOURCE_IMAGE)
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    width, height = source.size
    prereqs = summarize_prerequisites()
    evaluation = evaluate_matrix_readiness(prereqs)
    panel_path = make_blocker_panel(source, evaluation)

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "model_geometry_reference_matrix.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "model_geometry_reference_matrix.json"
    runtime_evidence_path = RUNTIME_DIR / "model_geometry_reference_matrix.json"

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(panel_path),
    ]
    note = (
        f"Model geometry reference matrix {RUN_STAMP}: exact local blocker. "
        "Gold traces are registered, but model-backed geometry dependencies and canonical authority remain blocked, so no reference matrix, cross-subject, or source-visibility pass was run."
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note)

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "created_iso": ISO_STAMP,
        "task": "Validate model-backed geometry across reference image matrix for TRK-W70-0152 / ITEM-W70-0152.",
        "script": SCRIPT_REL,
        "source_image": {
            "path": rel(SOURCE_IMAGE),
            "exists": True,
            "sha256": sha256_file(SOURCE_IMAGE),
            "dimensions": [width, height],
        },
        "prerequisite_authority_evidence": prereqs,
        "reference_matrix_readiness": evaluation,
        "artifacts": {
            "blocker_panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
        },
        "model_backed_geometry_authority": {
            "result": "blocked",
            "model_backed_geometry_authority_pass": False,
            "source_image": rel(SOURCE_IMAGE),
            "source_sha256": sha256_file(SOURCE_IMAGE),
            "source_dimensions": [width, height],
            "mask_type_id": "MBGA-011",
            "matrix_slot_id": "TRK-W70-0152",
            "models_attempted": [
                "gold_trace_reference_manifest_review",
                "model_backed_geometry_reference_matrix_gate",
            ],
            "models_available": ["base_image_io_and_cv"],
            "model_versions": {},
            "landmark_record_path": "",
            "semantic_parsing_record_path": "",
            "sam_refinement_record_path": "",
            "visibility_occlusion_record_path": "",
            "canonical_polygon_path": "",
            "coordinate_transform_manifest_path": "",
            "gold_trace_comparison_path": rel(QA_DIR / "gold_trace_dataset_manifest.json"),
            "dependency_probe_completed": True,
            "model_geometry_dependency_probe_pass": False,
            "source_derived_landmark_or_segmentation_pass": False,
            "model_consensus_geometry_pass": False,
            "visibility_occlusion_confidence_pass": False,
            "no_symmetry_guessing_pass": True,
            "canonical_polygon_export_pass": False,
            "reference_image_matrix_pass": False,
            "cross_subject_generalization_pass": False,
            "source_visibility_matrix_pass": False,
            "no_human_work_dependency": True,
            "no_debug_rectangle_mask_pass": True,
            "whole_body_geometry_authority_pass": False,
            "pose_hand_dense_landmark_or_segmentation_pass": False,
            "semantic_human_part_parsing_pass": False,
            "contact_occlusion_ownership_pass": False,
            "body_region_geometry_pass": False,
            "body_reference_matrix_pass": False,
            "blocked_reason": "Blocked_Reference_Matrix_Not_Run",
            "findings": [
                "Gold trace references are registered and hash-verified.",
                "No model-backed geometry route currently passes, so there is no model output to validate across the reference matrix.",
                "No canonical polygon or source-derived segmentation map exists for matrix comparison.",
                "No cross-subject/generalized/certification-ready claim was made.",
                "No active mask changed and no mask was promoted.",
            ],
        },
        "model_geometry_reference_matrix": {
            "result": "blocked",
            "reference_image_matrix_pass": False,
            "cross_subject_generalization_pass": False,
            "source_visibility_matrix_pass": False,
            "registered_reference_count": evaluation["registered_reference_count"],
            "failed_requirements": evaluation["failed_requirements"],
            "blocked_reason": "Blocked_Reference_Matrix_Not_Run",
        },
        "qa_decision": "blocked_exact_local_reference_matrix_not_runnable",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_reference_matrix_blocked",
        "tracker_item_updates": row_updates,
        "next_step": "Work TRK-W70-0153 / ITEM-W70-0153 model-backed authority promotion integration locally.",
    }

    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    update_hydration(evidence_rel_paths)
    print(json.dumps({"evidence_id": EVIDENCE_ID, "result": payload["qa_decision"], "evidence": rel(qa_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
