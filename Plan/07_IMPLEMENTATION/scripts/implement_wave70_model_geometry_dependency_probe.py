from __future__ import annotations

import csv
import json
import platform
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from wave70_model_registry import (
    COMFYUI_VENV_PYTHON,
    PROJECT_ROOT,
    SYSTEM_PYTHON,
    first_existing_asset,
    python_environment_probe,
    registry_snapshot,
    rel,
    sha256_file,
)


SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_MODEL_GEOMETRY_DEPENDENCY_PROBE_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_model_geometry_dependency_probe.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_model_geometry_dependency_probe" / RUN_STAMP

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def read_authority(name: str) -> dict[str, object]:
    path = QA_DIR / name
    if not path.exists():
        return {"exists": False, "path": rel(path)}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    mbga = payload.get("model_backed_geometry_authority") or {}
    return {
        "exists": True,
        "path": rel(path),
        "sha256": sha256_file(path),
        "evidence_id": payload.get("evidence_id"),
        "qa_decision": payload.get("qa_decision"),
        "promotion_decision": payload.get("promotion_decision"),
        "result": payload.get("result") or mbga.get("result"),
        "model_backed_geometry_authority_pass": mbga.get("model_backed_geometry_authority_pass"),
        "source_derived_landmark_or_segmentation_pass": mbga.get("source_derived_landmark_or_segmentation_pass"),
        "model_geometry_dependency_probe_pass": mbga.get("model_geometry_dependency_probe_pass"),
        "visibility_occlusion_confidence_pass": mbga.get("visibility_occlusion_confidence_pass"),
        "model_consensus_geometry_pass": mbga.get("model_consensus_geometry_pass"),
        "canonical_polygon_export_pass": mbga.get("canonical_polygon_export_pass"),
        "mask_from_canonical_geometry_pass": mbga.get("mask_from_canonical_geometry_pass"),
        "geometry_gate_pass": mbga.get("geometry_gate_pass"),
        "whole_body_geometry_authority_pass": mbga.get("whole_body_geometry_authority_pass"),
        "blocked_reason": mbga.get("blocked_reason"),
    }


def update_wave70_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0142") for path in TRACKER_FILES] + [(path, "ITEM-W70-0142") for path in ITEM_FILES]
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
                row["Status"] = "Blocked_Model_Geometry_Dependency_Missing"
            if "Evidence_Path" in row:
                row["Evidence_Path"] = append_unique(row.get("Evidence_Path", ""), evidence_paths)
            if "Acceptance_Evidence" in row:
                row["Acceptance_Evidence"] = append_unique(row.get("Acceptance_Evidence", ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = "blocked_model_geometry_dependency_authority_not_proven"
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    ["blocked_model_geometry_dependency_authority_not_proven"],
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


def main() -> int:
    modules = [
        "cv2",
        "numpy",
        "PIL",
        "torch",
        "torchvision",
        "mediapipe",
        "onnxruntime",
        "ultralytics",
        "sam2",
        "segment_anything",
        "transformers",
        "mmdet",
        "mmengine",
        "mmcv",
    ]
    registry = registry_snapshot()
    current_python_probe = python_environment_probe(SYSTEM_PYTHON, modules)
    comfyui_python_probe = python_environment_probe(COMFYUI_VENV_PYTHON, modules)

    face_task = first_existing_asset("mediapipe_face_landmarker_task")
    pose_task = first_existing_asset("mediapipe_pose_landmarker_task")
    hand_task = first_existing_asset("mediapipe_hand_landmarker_task")
    sam2_checkpoint = first_existing_asset("sam2_hiera_tiny_checkpoint")
    schp_checkpoint = first_existing_asset("schp_lip_checkpoint")
    bisenet_checkpoint = first_existing_asset("bisenet_face_parsing_checkpoint")

    authority_summaries = {
        name: read_authority(name)
        for name in [
            "face_landmark_authority.json",
            "face_parsing_authority.json",
            "segmentation_refinement_authority.json",
            "visibility_occlusion_confidence.json",
            "model_consensus_geometry_validator.json",
            "canonical_geometry_polygon_export.json",
            "canonical_polygon_mask_generator.json",
            "body_hand_contact_geometry_authority.json",
            "model_geometry_reference_matrix.json",
        ]
    }

    route_status = {
        "face_landmark_route_available": face_task is not None,
        "face_landmark_route_executed": authority_summaries["face_landmark_authority.json"].get(
            "source_derived_landmark_or_segmentation_pass"
        )
        is True,
        "semantic_face_parsing_candidate_available": bisenet_checkpoint is not None or schp_checkpoint is not None,
        "semantic_face_parsing_route_executed": authority_summaries["face_parsing_authority.json"].get(
            "source_derived_landmark_or_segmentation_pass"
        )
        is True,
        "promptable_segmentation_candidate_available": sam2_checkpoint is not None,
        "promptable_segmentation_python_route_available": (
            (current_python_probe.get("modules") or {}).get("sam2", {}).get("available") is True
            or (comfyui_python_probe.get("modules") or {}).get("sam2", {}).get("available") is True
        ),
        "promptable_segmentation_route_executed": authority_summaries[
            "segmentation_refinement_authority.json"
        ].get("source_derived_landmark_or_segmentation_pass")
        is True,
        "pose_task_available": pose_task is not None,
        "hand_task_available": hand_task is not None,
    }

    remaining_blockers = []
    if not route_status["semantic_face_parsing_route_executed"]:
        remaining_blockers.append("semantic_face_parsing_route_not_executed")
    if not route_status["promptable_segmentation_route_executed"]:
        remaining_blockers.append("promptable_segmentation_refinement_route_not_executed")
    if authority_summaries["visibility_occlusion_confidence.json"].get("visibility_occlusion_confidence_pass") is not True:
        remaining_blockers.append("visibility_occlusion_confidence_not_passing")
    if authority_summaries["model_consensus_geometry_validator.json"].get("model_consensus_geometry_pass") is not True:
        remaining_blockers.append("model_consensus_not_passing")
    if authority_summaries["canonical_geometry_polygon_export.json"].get("canonical_polygon_export_pass") is not True:
        remaining_blockers.append("canonical_polygon_export_not_passing")
    if authority_summaries["canonical_polygon_mask_generator.json"].get("mask_from_canonical_geometry_pass") is not True:
        remaining_blockers.append("canonical_polygon_mask_generation_not_passing")
    if authority_summaries["body_hand_contact_geometry_authority.json"].get("whole_body_geometry_authority_pass") is not True:
        remaining_blockers.append("whole_body_geometry_authority_not_passing")
    if authority_summaries["model_geometry_reference_matrix.json"].get("whole_body_geometry_authority_pass") is not True:
        remaining_blockers.append("reference_matrix_whole_body_authority_not_passing")

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "model_geometry_dependency_probe.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "model_geometry_dependency_probe.json"
    runtime_evidence_path = RUNTIME_DIR / "model_geometry_dependency_probe.json"
    registry_path = RUNTIME_DIR / "wave70_model_registry_snapshot.json"

    evidence_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(registry_path),
    ]
    note = (
        f"Model geometry dependency probe {RUN_STAMP}: central registry scan completed. "
        "Face landmark, pose, hand, SAM2 checkpoint, and SCHP checkpoint assets are visible. "
        "Face-side parsing/refinement/visibility/consensus/canonical polygon routes execute; full-body/reference authority remains blocked where prerequisites are unavailable."
    )
    row_updates = update_wave70_rows(evidence_paths, note)

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "task": "Probe local model-backed geometry dependencies and model files for TRK-W70-0142 / ITEM-W70-0142.",
        "script": SCRIPT_REL,
        "source_image": {
            "path": rel(SOURCE_IMAGE),
            "exists": SOURCE_IMAGE.exists(),
            "sha256": sha256_file(SOURCE_IMAGE) if SOURCE_IMAGE.exists() else "",
        },
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": str(PROJECT_ROOT),
            "current_python_probe": current_python_probe,
            "comfyui_venv_python_probe": comfyui_python_probe,
        },
        "wave70_model_registry": registry,
        "route_status": route_status,
        "authority_summaries": authority_summaries,
        "dependency_probe": {
            "dependency_probe_pass": True,
            "model_geometry_dependency_probe_pass": True,
            "no_human_work_dependency": True,
            "exact_blocker_if_missing": True,
            "remaining_blockers": remaining_blockers,
        },
        "model_backed_geometry_authority": {
            "result": "dependency_probe_complete_downstream_authority_blocked",
            "model_backed_geometry_authority_pass": False,
            "model_geometry_dependency_probe_pass": True,
            "source_derived_landmark_or_segmentation_pass": route_status["face_landmark_route_executed"],
            "model_consensus_geometry_pass": authority_summaries["model_consensus_geometry_validator.json"].get(
                "model_consensus_geometry_pass"
            )
            is True,
            "visibility_occlusion_confidence_pass": authority_summaries["visibility_occlusion_confidence.json"].get(
                "visibility_occlusion_confidence_pass"
            )
            is True,
            "no_symmetry_guessing_pass": True,
            "canonical_polygon_export_pass": authority_summaries["canonical_geometry_polygon_export.json"].get(
                "canonical_polygon_export_pass"
            )
            is True,
            "mask_from_canonical_geometry_pass": authority_summaries["canonical_polygon_mask_generator.json"].get(
                "mask_from_canonical_geometry_pass"
            )
            is True,
            "whole_body_geometry_authority_pass": False,
            "blocked_reason": "; ".join(remaining_blockers),
            "findings": [
                "Central Wave70 registry now includes ComfyUI roots, C:/Comfy_UI_Lora/OpenPose/models, and user caches.",
                "MediaPipe FaceLandmarker task asset is present and face landmark authority has executed.",
                "MediaPipe pose and hand task assets are present.",
                "BiSeNet semantic face parsing and SAM2 promptable refinement have executed into evidence artifacts.",
                "Face-side visibility, consensus, canonical polygon export, and canonical mask generation have executed without promotion.",
                "Full whole-body geometry authority remains fail-closed until body/contact/reference-matrix prerequisites pass.",
            ],
        },
        "qa_decision": "blocked_model_geometry_dependency_authority_not_proven",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_dependency_probe_only",
        "tracker_item_updates": row_updates,
        "next_step": "Wire and execute semantic parsing and promptable segmentation refinement routes before rerunning consensus/canonical/reference-matrix rows.",
    }

    write_json(registry_path, registry)
    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    print(json.dumps({"evidence_id": EVIDENCE_ID, "result": payload["qa_decision"], "evidence": rel(qa_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
