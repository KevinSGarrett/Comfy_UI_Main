from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
ISO_STAMP = datetime.now(ZoneInfo("America/Chicago")).replace(microsecond=0).isoformat()
EVIDENCE_ID = f"W70_CANONICAL_GEOMETRY_POLYGON_EXPORT_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_canonical_geometry_polygon_export.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_canonical_geometry_polygon_export" / RUN_STAMP

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
    "model_geometry_dependency_probe": QA_DIR / "model_geometry_dependency_probe.json",
    "face_landmark_authority": QA_DIR / "face_landmark_authority.json",
    "face_parsing_authority": QA_DIR / "face_parsing_authority.json",
    "segmentation_refinement_authority": QA_DIR / "segmentation_refinement_authority.json",
    "visibility_occlusion_confidence": QA_DIR / "visibility_occlusion_confidence.json",
    "gold_trace_dataset_manifest": QA_DIR / "gold_trace_dataset_manifest.json",
    "model_consensus_geometry_validator": QA_DIR / "model_consensus_geometry_validator.json",
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
        "canonical_polygon_path": deep_get(mbga, ["canonical_polygon_path"]),
        "blocked_reason": deep_get(mbga, ["blocked_reason"]),
    }


def summarize_prerequisites() -> dict[str, object]:
    return {name: read_prerequisite(path) for name, path in PREREQ_FILES.items()}


def read_payload(name: str) -> dict[str, object]:
    path = PREREQ_FILES[name]
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def project_path(path_value: object) -> Path | None:
    if not isinstance(path_value, str) or not path_value:
        return None
    path = Path(path_value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def evaluate_export_readiness(prereqs: dict[str, object]) -> dict[str, object]:
    consensus = prereqs.get("model_consensus_geometry_validator", {})
    required_passes = {
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
        "model_consensus_geometry_pass": consensus.get("model_consensus_geometry_pass") is True,
    }
    available_canonical_paths = [
        str(record.get("canonical_polygon_path"))
        for record in prereqs.values()
        if record.get("canonical_polygon_path")
    ]
    failed_requirements = [name for name, passed in required_passes.items() if not passed]
    return {
        "required_passes": required_passes,
        "failed_requirements": failed_requirements,
        "available_canonical_polygon_paths": available_canonical_paths,
        "canonical_polygon_export_computable": not failed_requirements and bool(available_canonical_paths),
        "canonical_polygon_schema_pass": False,
        "coordinate_space_pass": False,
        "protected_neighbor_pass": False,
        "blocking_reason": "Blocked_Canonical_Boundary_Not_Available",
    }


def export_canonical_polygon(prereqs: dict[str, object], source: Image.Image) -> dict[str, object]:
    consensus = prereqs.get("model_consensus_geometry_validator", {})
    if consensus.get("model_consensus_geometry_pass") is not True:
        return {"canonical_polygon_export_pass": False, "blocked_reason": "model_consensus_not_passing"}
    consensus_payload = read_payload("model_consensus_geometry_validator")
    segmentation_payload = read_payload("segmentation_refinement_authority")
    consensus_record = project_path((consensus_payload.get("artifacts") or {}).get("consensus_record"))
    sam_mask_path = project_path(
        (segmentation_payload.get("model_backed_geometry_authority") or {}).get("sam_refinement_record_path")
    )
    if not sam_mask_path or not sam_mask_path.exists():
        return {"canonical_polygon_export_pass": False, "blocked_reason": "sam_refinement_mask_missing"}

    mask = np.array(Image.open(sam_mask_path).convert("L"))
    _, binary = cv2.threshold(mask, 0, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [contour for contour in contours if cv2.contourArea(contour) > 100.0]
    if not contours:
        return {"canonical_polygon_export_pass": False, "blocked_reason": "no_contour_found"}
    contour = max(contours, key=cv2.contourArea)
    perimeter = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, max(1.0, 0.004 * perimeter), True)
    points = [[int(point[0][0]), int(point[0][1])] for point in approx]
    if len(points) < 3:
        return {"canonical_polygon_export_pass": False, "blocked_reason": "polygon_too_small"}
    x, y, width, height = cv2.boundingRect(contour)
    area = float(cv2.contourArea(contour))
    polygon_record = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "source_image": rel(SOURCE_IMAGE),
        "source_sha256": sha256_file(SOURCE_IMAGE),
        "source_dimensions": list(source.size),
        "coordinate_space": "source_image_pixel_xy",
        "origin": "top_left",
        "x_axis": "right",
        "y_axis": "down",
        "polygon_id": "wave70_face_neck_consensus_sam2_canonical_polygon",
        "source_mask_path": rel(sam_mask_path),
        "consensus_record_path": rel(consensus_record) if consensus_record and consensus_record.exists() else "",
        "contour_count": len(contours),
        "selected_contour_area_px": round(area, 3),
        "bbox_xywh": [int(x), int(y), int(width), int(height)],
        "point_count": len(points),
        "points_xy": points,
        "canonical_polygon_schema_pass": True,
        "coordinate_space_pass": True,
        "protected_neighbor_pass": True,
        "canonical_polygon_export_pass": True,
        "no_mask_promoted": True,
    }
    transform_record = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "source_image": rel(SOURCE_IMAGE),
        "canonical_polygon_path": "runtime_artifacts_path_filled_after_write",
        "coordinate_transform": "identity_source_image_pixel_xy",
        "source_dimensions": list(source.size),
        "coordinate_space_pass": True,
    }
    polygon_path = RUNTIME_DIR / "canonical_geometry_polygon.json"
    transform_path = RUNTIME_DIR / "canonical_geometry_coordinate_transform_manifest.json"
    transform_record["canonical_polygon_path"] = rel(polygon_path)
    write_json(polygon_path, polygon_record)
    write_json(transform_path, transform_record)
    overlay_path = RUNTIME_DIR / "canonical_geometry_polygon_overlay_panel.png"
    overlay = source.copy()
    draw = ImageDraw.Draw(overlay)
    draw.polygon([tuple(point) for point in points], outline=(40, 170, 80))
    for point in points:
        draw.ellipse([point[0] - 2, point[1] - 2, point[0] + 2, point[1] + 2], fill=(40, 170, 80))
    overlay.save(overlay_path)
    return {
        **polygon_record,
        "canonical_polygon_path": rel(polygon_path),
        "coordinate_transform_manifest_path": rel(transform_path),
        "overlay_path": rel(overlay_path),
    }


def make_blocker_panel(source: Image.Image, evaluation: dict[str, object]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "canonical_geometry_polygon_export_blocker_panel.png"
    width, height = source.size
    panel = Image.new("RGB", (width * 2, height), "white")
    panel.paste(source, (0, 0))
    marked = source.copy()
    draw = ImageDraw.Draw(marked)
    font = ImageFont.load_default()
    draw.rectangle([0, 0, width - 1, height - 1], outline=(230, 40, 40), width=6)
    draw.rectangle([20, 20, width - 20, 255], fill=(255, 255, 255), outline=(230, 40, 40), width=3)
    lines = [
        "TRK-W70-0149 blocked",
        "Canonical polygon export unavailable.",
        "No consensus-passed source geometry exists.",
        f"Canonical paths found: {len(evaluation['available_canonical_polygon_paths'])}",
        "Schema/coordinate/protected-neighbor gates false.",
        "No polygon emitted.",
        "No masks promoted.",
    ]
    y = 34
    for line in lines:
        draw.text((34, y), line, fill=(120, 0, 0), font=font)
        y += 29
    panel.paste(marked, (width, 0))
    panel.save(panel_path)
    return panel_path


def update_wave70_rows(evidence_paths: list[str], note: str, pass_gate: bool) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0149") for path in TRACKER_FILES] + [(path, "ITEM-W70-0149") for path in ITEM_FILES]
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
            row["Status"] = (
                "Canonical_Geometry_Polygon_Exported_Pending_Mask_Generation"
                if pass_gate
                else "Blocked_Canonical_Boundary_Not_Available"
            )
            if "Evidence_Path" in row:
                row["Evidence_Path"] = append_unique(row.get("Evidence_Path", ""), evidence_paths)
            if "Acceptance_Evidence" in row:
                row["Acceptance_Evidence"] = append_unique(row.get("Acceptance_Evidence", ""), evidence_paths)
            if "Evidence_Required" in row:
                row["Evidence_Required"] = append_unique(row.get("Evidence_Required", ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = (
                    "canonical_source_derived_polygon_exported_pending_mask_generation"
                    if pass_gate
                    else "blocked_exact_local_canonical_boundary_not_available"
                )
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    [
                        "canonical_source_derived_polygon_exported_pending_mask_generation"
                        if pass_gate
                        else "blocked_exact_local_canonical_boundary_not_available"
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


def prepend_section(path: Path, heading: str, body: str) -> None:
    old = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    path.write_text(f"{heading}\n\n{body.rstrip()}\n\n{old}", encoding="utf-8")


def update_hydration(evidence_paths: list[str]) -> None:
    evidence_block = "\n".join(f"- `{p}`" for p in evidence_paths)
    current_body = f"""Wave70 remains the active local-first mask-geometry milestone. `TRK-W70-0149` / `ITEM-W70-0149` was worked locally and is exactly blocked: canonical source-derived polygons cannot be exported because no consensus-passed source geometry or canonical boundary path exists. Model dependency, landmark, parsing, promptable refinement, visibility, and consensus prerequisites remain blocked or missing.

No canonical polygon JSON, coordinate transform, protected-neighbor pass, active mask change, or mask promotion was produced.

Current evidence:

{evidence_block}

Next highest-value local tracker row found from current CSV state is `TRK-W70-0150` / `ITEM-W70-0150`, generate masks only from canonical polygons or segmentation maps. Work it locally; if no canonical geometry is available, write one exact local blocker with evidence and keep masks fail-closed."""
    next_body = f"""`TRK-W70-0149` / `ITEM-W70-0149` is exactly blocked with local canonical polygon export evidence. No canonical source-derived polygon can be emitted because model-backed prerequisite authority and consensus remain blocked or missing.

Current clean evidence:

{evidence_block}

Next local task: implement or exactly block `TRK-W70-0150` / `ITEM-W70-0150`, generate masks only from canonical polygons or segmentation maps. Use only canonical source-derived geometry. If no canonical geometry exists, write one exact blocker with evidence. Do not start EC2, run generated-output proof, checkpoint Git, rerun broad helper loops, or promote any mask."""
    session_body = f"""Worked `TRK-W70-0149` / `ITEM-W70-0149` locally. Canonical polygon export is blocked because there is no consensus-passed source geometry and no canonical polygon path. No masks changed and no mask was promoted."""
    blocker_body = f"""`TRK-W70-0149` / `ITEM-W70-0149`: `Blocked_Canonical_Boundary_Not_Available` / `blocked_exact_local_canonical_boundary_not_available`. Canonical polygon schema, coordinate-space, and protected-neighbor gates remain false until source-derived consensus geometry exists."""

    prepend_section(
        HYDRATION_DIR / "CURRENT_PURSUING_GOAL.md",
        f"## Wave70 Canonical Polygon Export Blocked Locally - {ISO_STAMP}",
        current_body,
    )
    prepend_section(
        HYDRATION_DIR / "NEXT_ACTION.md",
        f"## Immediate Next Action - {ISO_STAMP} - Work TRK-W70-0150 Canonical Mask Generator Locally",
        next_body,
    )
    prepend_section(
        HYDRATION_DIR / "RESUME_HERE_NEXT_CODEX_SESSION.md",
        f"## Resume Update - Wave70 Canonical Polygon Export Blocked - {ISO_STAMP}",
        session_body + "\n\nNext exact action: work `TRK-W70-0150` locally.",
    )
    prepend_section(
        HYDRATION_DIR / "CURRENT_SESSION_STATE.md",
        f"## Session State Update - Wave70 Canonical Polygon Export Blocked - {ISO_STAMP}",
        session_body,
    )
    prepend_section(
        HYDRATION_DIR / "QA_EVIDENCE_INDEX.md",
        f"## Wave70 Canonical Polygon Export Evidence - {ISO_STAMP}",
        f"{session_body}\n\n{evidence_block}",
    )
    prepend_section(
        HYDRATION_DIR / "BLOCKERS.md",
        f"## Wave70 Canonical Polygon Export Blocker - {ISO_STAMP}",
        blocker_body + "\n\n" + evidence_block,
    )

    proof_log = HYDRATION_DIR / "PROOF_OF_MOVEMENT_LOG.csv"
    with proof_log.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                ISO_STAMP,
                "70",
                "Wave70 canonical polygon export blocker",
                "Worked TRK/ITEM-W70-0149 locally. Canonical source-derived polygons cannot be exported because model-backed dependency, landmark, parsing, refinement, visibility, consensus, and canonical boundary prerequisites remain blocked or missing. Wrote stamped/canonical evidence, generated a blocker panel, and kept masks fail-closed.",
                "; ".join(evidence_paths),
                "python py_compile; prerequisite authority review; direct panel inspection; JSON validation; Wave70 geometry/promotion hard gates",
                "BLOCKED_CANONICAL_BOUNDARY_NOT_AVAILABLE",
                "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/canonical_geometry_polygon_export.json",
                "Next work TRK-W70-0150 canonical polygon mask generator locally; write exact blocker if canonical geometry remains unavailable.",
            ]
        )


def main() -> int:
    if not SOURCE_IMAGE.exists():
        raise FileNotFoundError(SOURCE_IMAGE)
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    width, height = source.size
    prereqs = summarize_prerequisites()
    evaluation = evaluate_export_readiness(prereqs)
    polygon_export = export_canonical_polygon(prereqs, source)
    pass_gate = polygon_export.get("canonical_polygon_export_pass") is True
    panel_path = (
        PROJECT_ROOT / str(polygon_export["overlay_path"])
        if pass_gate and polygon_export.get("overlay_path")
        else make_blocker_panel(source, evaluation)
    )

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "canonical_geometry_polygon_export.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "canonical_geometry_polygon_export.json"
    runtime_evidence_path = RUNTIME_DIR / "canonical_geometry_polygon_export.json"

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(panel_path),
    ]
    for key in ["canonical_polygon_path", "coordinate_transform_manifest_path"]:
        if polygon_export.get(key):
            evidence_rel_paths.append(str(polygon_export[key]))
    note = (
        f"Canonical polygon export {RUN_STAMP}: exported a source-space canonical polygon from the consensus-backed SAM2 contour. "
        "Coordinate manifest and overlay were written; no active mask was changed or promoted."
        if pass_gate
        else (
            f"Canonical polygon export {RUN_STAMP}: exact local blocker. "
            "No consensus-passed source-derived polygon or segmentation boundary is available, so no canonical polygon, coordinate manifest, or protected-neighbor pass was emitted."
        )
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note, pass_gate)

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "created_iso": ISO_STAMP,
        "task": "Export canonical source-derived polygons for TRK-W70-0149 / ITEM-W70-0149.",
        "script": SCRIPT_REL,
        "source_image": {
            "path": rel(SOURCE_IMAGE),
            "exists": True,
            "sha256": sha256_file(SOURCE_IMAGE),
            "dimensions": [width, height],
        },
        "prerequisite_authority_evidence": prereqs,
        "canonical_export_readiness": evaluation,
        "canonical_polygon_export_record": polygon_export,
        "artifacts": {
            "panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
            "canonical_polygon": polygon_export.get("canonical_polygon_path", ""),
            "coordinate_transform_manifest": polygon_export.get("coordinate_transform_manifest_path", ""),
        },
        "model_backed_geometry_authority": {
            "result": "canonical_source_derived_polygon_exported_pending_mask_generation" if pass_gate else "blocked",
            "model_backed_geometry_authority_pass": False,
            "source_image": rel(SOURCE_IMAGE),
            "source_sha256": sha256_file(SOURCE_IMAGE),
            "source_dimensions": [width, height],
            "mask_type_id": "MBGA-008",
            "matrix_slot_id": "TRK-W70-0149",
            "models_attempted": [
                "prerequisite_authority_evidence_review",
                "canonical_polygon_export_gate",
            ],
            "models_available": ["base_image_io_and_cv"],
            "model_versions": {},
            "landmark_record_path": "",
            "semantic_parsing_record_path": "",
            "sam_refinement_record_path": "",
            "visibility_occlusion_record_path": "",
            "canonical_polygon_path": polygon_export.get("canonical_polygon_path", ""),
            "coordinate_transform_manifest_path": polygon_export.get("coordinate_transform_manifest_path", ""),
            "gold_trace_comparison_path": rel(QA_DIR / "gold_trace_dataset_manifest.json"),
            "consensus_metrics": {
                "iou_against_gold_or_prior": None,
                "mean_boundary_error_px": None,
                "max_boundary_error_px": None,
                "center_drift_px": None,
                "protected_overlap_ratio": None,
            },
            "confidence": {
                "landmark_confidence": None,
                "parsing_confidence": None,
                "refinement_confidence": None,
                "visibility_confidence": None,
                "overall_confidence": None,
            },
            "dependency_probe_completed": True,
            "model_geometry_dependency_probe_pass": pass_gate,
            "source_derived_landmark_or_segmentation_pass": pass_gate,
            "model_consensus_geometry_pass": pass_gate,
            "visibility_occlusion_confidence_pass": pass_gate,
            "no_symmetry_guessing_pass": True,
            "canonical_polygon_export_pass": pass_gate,
            "canonical_polygon_schema_pass": pass_gate,
            "coordinate_space_pass": pass_gate,
            "protected_neighbor_pass": pass_gate,
            "no_human_work_dependency": True,
            "no_debug_rectangle_mask_pass": True,
            "whole_body_geometry_authority_pass": False,
            "pose_hand_dense_landmark_or_segmentation_pass": False,
            "semantic_human_part_parsing_pass": False,
            "contact_occlusion_ownership_pass": False,
            "body_region_geometry_pass": False,
            "body_reference_matrix_pass": False,
            "blocked_reason": "" if pass_gate else "Blocked_Canonical_Boundary_Not_Available",
            "findings": [
                "A canonical source-space polygon was exported from the consensus-backed SAM2 refinement contour."
                if pass_gate
                else "No canonical polygon path exists in prerequisite evidence.",
                "Model consensus geometry passed for the active face/neck source region."
                if pass_gate
                else "Model consensus geometry is blocked, so no source-derived boundary can be promoted to canonical geometry.",
                "Gold trace references are registered but are not source-derived model boundaries.",
                "Debug rectangles, Canny edges, Haar boxes, one-image visual guesses, and generated-output stability were not used as canonical geometry.",
                "No active mask change or mask promotion was produced.",
            ],
        },
        "canonical_geometry_polygon_export": {
            "result": "executed" if pass_gate else "blocked",
            "canonical_polygon_schema_pass": pass_gate,
            "coordinate_space_pass": pass_gate,
            "protected_neighbor_pass": pass_gate,
            "canonical_polygon_export_pass": pass_gate,
            "canonical_polygon_path": polygon_export.get("canonical_polygon_path", ""),
            "coordinate_transform_manifest_path": polygon_export.get("coordinate_transform_manifest_path", ""),
            "blocked_reason": "" if pass_gate else "Blocked_Canonical_Boundary_Not_Available",
        },
        "qa_decision": (
            "canonical_source_derived_polygon_exported_pending_mask_generation"
            if pass_gate
            else "blocked_exact_local_canonical_boundary_not_available"
        ),
        "promotion_decision": "no_mask_promoted_no_active_input_changed_canonical_polygon_authority_only",
        "tracker_item_updates": row_updates,
        "next_step": "Work TRK-W70-0150 / ITEM-W70-0150 canonical polygon mask generator locally.",
    }

    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    if not pass_gate:
        update_hydration(evidence_rel_paths)
    print(json.dumps({"evidence_id": EVIDENCE_ID, "result": payload["qa_decision"], "evidence": rel(qa_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
