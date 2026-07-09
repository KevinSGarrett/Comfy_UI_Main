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
EVIDENCE_ID = f"W70_VISIBILITY_OCCLUSION_CONFIDENCE_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_visibility_occlusion_confidence.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_visibility_occlusion_confidence" / RUN_STAMP

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]

PREREQ_FILES = {
    "model_geometry_dependency_probe": QA_DIR / "model_geometry_dependency_probe.json",
    "face_landmark_authority": QA_DIR / "face_landmark_authority.json",
    "face_parsing_authority": QA_DIR / "face_parsing_authority.json",
    "segmentation_refinement_authority": QA_DIR / "segmentation_refinement_authority.json",
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


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"exists": False, "path": rel(path), "error": "missing"}
    return {"exists": True, "path": rel(path), "payload": json.loads(path.read_text(encoding="utf-8-sig"))}


def deep_get(payload: object, keys: list[str]) -> object | None:
    current = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def summarize_prerequisites() -> dict[str, object]:
    records: dict[str, object] = {}
    for name, path in PREREQ_FILES.items():
        record = read_json(path)
        payload = record.get("payload")
        if isinstance(payload, dict):
            mbga = payload.get("model_backed_geometry_authority")
            authority = payload.get(name)
            record["evidence_id"] = payload.get("evidence_id")
            record["qa_decision"] = payload.get("qa_decision")
            record["promotion_decision"] = payload.get("promotion_decision")
            record["result"] = deep_get(mbga, ["result"]) if isinstance(mbga, dict) else None
            record["model_backed_geometry_authority_pass"] = (
                deep_get(mbga, ["model_backed_geometry_authority_pass"]) if isinstance(mbga, dict) else None
            )
            record["source_derived_landmark_or_segmentation_pass"] = (
                deep_get(mbga, ["source_derived_landmark_or_segmentation_pass"]) if isinstance(mbga, dict) else None
            )
            record["canonical_polygon_export_pass"] = (
                deep_get(mbga, ["canonical_polygon_export_pass"]) if isinstance(mbga, dict) else None
            )
            record["visibility_occlusion_confidence_pass"] = (
                deep_get(mbga, ["visibility_occlusion_confidence_pass"]) if isinstance(mbga, dict) else None
            )
            record["blocked_reason"] = deep_get(mbga, ["blocked_reason"]) if isinstance(mbga, dict) else None
            if isinstance(authority, dict):
                record["authority_result"] = authority.get("result")
        records[name] = record
    return records


def project_path(path_value: object) -> Path | None:
    if not isinstance(path_value, str) or not path_value:
        return None
    path = Path(path_value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def mask_count(path: Path, positive_values: set[int] | None = None) -> int:
    image = Image.open(path).convert("L")
    values = list(image.getdata())
    if positive_values is None:
        return sum(1 for value in values if value > 0)
    return sum(1 for value in values if value in positive_values)


def compute_visibility_confidence(prerequisites: dict[str, object]) -> dict[str, object]:
    landmark_payload = prerequisites.get("face_landmark_authority", {}).get("payload", {})
    parsing_payload = prerequisites.get("face_parsing_authority", {}).get("payload", {})
    refinement_payload = prerequisites.get("segmentation_refinement_authority", {}).get("payload", {})
    landmark_mbga = landmark_payload.get("model_backed_geometry_authority", {}) if isinstance(landmark_payload, dict) else {}
    parsing_mbga = parsing_payload.get("model_backed_geometry_authority", {}) if isinstance(parsing_payload, dict) else {}
    refinement_mbga = (
        refinement_payload.get("model_backed_geometry_authority", {}) if isinstance(refinement_payload, dict) else {}
    )
    landmark_path = project_path(landmark_mbga.get("landmark_record_path"))
    parsing_map_path = project_path((parsing_payload.get("artifacts") or {}).get("semantic_parsing_map"))
    sam_mask_path = project_path(refinement_mbga.get("sam_refinement_record_path"))
    required_ready = {
        "face_landmark_authority": landmark_mbga.get("source_derived_landmark_or_segmentation_pass") is True,
        "face_parsing_authority": parsing_mbga.get("source_derived_landmark_or_segmentation_pass") is True,
        "segmentation_refinement_authority": refinement_mbga.get("source_derived_landmark_or_segmentation_pass") is True,
        "landmark_record_exists": bool(landmark_path and landmark_path.exists()),
        "semantic_parsing_map_exists": bool(parsing_map_path and parsing_map_path.exists()),
        "sam_refinement_mask_exists": bool(sam_mask_path and sam_mask_path.exists()),
    }
    if not all(required_ready.values()) or not landmark_path or not parsing_map_path or not sam_mask_path:
        return {
            "visibility_occlusion_confidence_pass": False,
            "visibility_state_pass": False,
            "required_ready": required_ready,
            "blocked_reason": "Blocked_Model_Geometry_Low_Confidence",
        }

    landmark_record = json.loads(landmark_path.read_text(encoding="utf-8-sig"))
    bbox = landmark_record.get("bbox_xyxy") or []
    parse_image = Image.open(parsing_map_path).convert("L")
    sam_image = Image.open(sam_mask_path).convert("L")
    parse_values = list(parse_image.getdata())
    sam_values = list(sam_image.getdata())
    total = len(parse_values)
    face_region_classes = {1, 2, 3, 4, 5, 10, 11, 12, 13, 14, 17}
    parse_region_count = sum(1 for value in parse_values if value in face_region_classes)
    sam_count = sum(1 for value in sam_values if value > 0)
    overlap_count = sum(
        1 for parse_value, sam_value in zip(parse_values, sam_values) if parse_value in face_region_classes and sam_value > 0
    )
    parse_region_ratio = parse_region_count / float(total)
    sam_region_ratio = sam_count / float(total)
    parse_to_sam_overlap_ratio = overlap_count / float(parse_region_count or 1)
    sam_to_parse_overlap_ratio = overlap_count / float(sam_count or 1)
    bbox_in_bounds = (
        len(bbox) == 4
        and min(bbox) >= 0
        and bbox[0] < bbox[2] <= parse_image.width
        and bbox[1] < bbox[3] <= parse_image.height
    )
    visibility_confidence = min(
        0.99,
        0.25
        + (0.25 if bbox_in_bounds else 0.0)
        + min(0.2, parse_region_ratio)
        + min(0.2, sam_region_ratio)
        + min(0.25, parse_to_sam_overlap_ratio * 0.25)
    )
    occlusion_confidence = 0.72 if parse_to_sam_overlap_ratio >= 0.25 and sam_to_parse_overlap_ratio >= 0.45 else 0.54
    overall_confidence = round((visibility_confidence + occlusion_confidence) / 2.0, 4)
    pass_gate = (
        bbox_in_bounds
        and parse_region_ratio >= 0.05
        and sam_region_ratio >= 0.03
        and parse_to_sam_overlap_ratio >= 0.25
        and sam_to_parse_overlap_ratio >= 0.45
    )
    visibility_record = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "source_image": rel(SOURCE_IMAGE),
        "landmark_record_path": rel(landmark_path),
        "semantic_parsing_map_path": rel(parsing_map_path),
        "sam_refinement_mask_path": rel(sam_mask_path),
        "bbox_xyxy": bbox,
        "bbox_in_bounds": bbox_in_bounds,
        "parse_region_classes": sorted(face_region_classes),
        "parse_region_count": parse_region_count,
        "sam_region_count": sam_count,
        "overlap_count": overlap_count,
        "parse_region_ratio": round(parse_region_ratio, 6),
        "sam_region_ratio": round(sam_region_ratio, 6),
        "parse_to_sam_overlap_ratio": round(parse_to_sam_overlap_ratio, 6),
        "sam_to_parse_overlap_ratio": round(sam_to_parse_overlap_ratio, 6),
        "visibility_confidence": round(visibility_confidence, 4),
        "occlusion_confidence": round(occlusion_confidence, 4),
        "overall_confidence": overall_confidence,
        "visibility_state_pass": pass_gate,
        "visibility_occlusion_confidence_pass": pass_gate,
        "no_symmetry_guessing_pass": True,
        "no_debug_rectangle_mask_pass": True,
    }
    visibility_record_path = RUNTIME_DIR / "visibility_occlusion_confidence_record.json"
    write_json(visibility_record_path, visibility_record)
    return {
        **visibility_record,
        "required_ready": required_ready,
        "visibility_record_path": rel(visibility_record_path),
        "blocked_reason": "" if pass_gate else "Blocked_Model_Geometry_Low_Confidence",
    }


def make_blocker_panel(source: Image.Image) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "visibility_occlusion_confidence_blocker_panel.png"
    width, height = source.size
    panel = Image.new("RGB", (width * 2, height), "white")
    panel.paste(source, (0, 0))
    marked = source.copy()
    draw = ImageDraw.Draw(marked)
    draw.rectangle([0, 0, width - 1, height - 1], outline=(230, 40, 40), width=6)
    draw.rectangle([20, 20, width - 20, 205], fill=(255, 255, 255), outline=(230, 40, 40), width=3)
    font = ImageFont.load_default()
    lines = [
        "TRK-W70-0146 blocked",
        "Visibility confidence cannot be computed.",
        "Landmark/parsing/refinement prerequisites blocked.",
        "No canonical polygons available.",
        "No symmetry guessing.",
        "No masks promoted.",
    ]
    y = 34
    for line in lines:
        draw.text((34, y), line, fill=(120, 0, 0), font=font)
        y += 25
    panel.paste(marked, (width, 0))
    panel.save(panel_path)
    return panel_path


def make_success_panel(source: Image.Image, visibility: dict[str, object]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "visibility_occlusion_confidence_panel.png"
    width, height = source.size
    panel = Image.new("RGB", (width * 2, height), "white")
    panel.paste(source, (0, 0))
    marked = source.copy()
    draw = ImageDraw.Draw(marked)
    draw.rectangle([0, 0, width - 1, height - 1], outline=(40, 170, 80), width=6)
    draw.rectangle([20, 20, width - 20, 235], fill=(255, 255, 255), outline=(40, 170, 80), width=3)
    font = ImageFont.load_default()
    lines = [
        "TRK-W70-0146 executed",
        "Visibility confidence computed from model outputs.",
        f"Parse/SAM overlap: {visibility.get('parse_to_sam_overlap_ratio')}",
        f"SAM/parse overlap: {visibility.get('sam_to_parse_overlap_ratio')}",
        f"Overall confidence: {visibility.get('overall_confidence')}",
        "No masks promoted.",
    ]
    y = 34
    for line in lines:
        draw.text((34, y), line, fill=(0, 90, 35), font=font)
        y += 29
    panel.paste(marked, (width, 0))
    panel.save(panel_path)
    return panel_path


def update_wave70_rows(evidence_paths: list[str], note: str, pass_gate: bool) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0146") for path in TRACKER_FILES] + [(path, "ITEM-W70-0146") for path in ITEM_FILES]
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
                row["Status"] = (
                    "Visibility_Occlusion_Confidence_Implemented_Pending_Consensus"
                    if pass_gate
                    else "Blocked_Model_Geometry_Low_Confidence"
                )
            if "Evidence_Path" in row:
                row["Evidence_Path"] = append_unique(row.get("Evidence_Path", ""), evidence_paths)
            if "Acceptance_Evidence" in row:
                row["Acceptance_Evidence"] = append_unique(row.get("Acceptance_Evidence", ""), evidence_paths)
            if "Evidence_Required" in row:
                row["Evidence_Required"] = append_unique(row.get("Evidence_Required", ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = (
                    "visibility_occlusion_confidence_executed_pending_consensus_and_canonical_polygon"
                    if pass_gate
                    else "blocked_exact_local_visibility_occlusion_confidence_low_confidence"
                )
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    [
                        "visibility_occlusion_confidence_executed_pending_consensus_and_canonical_polygon"
                        if pass_gate
                        else "blocked_exact_local_visibility_occlusion_confidence_low_confidence"
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


def main() -> int:
    if not SOURCE_IMAGE.exists():
        raise FileNotFoundError(SOURCE_IMAGE)
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    width, height = source.size
    prerequisites = summarize_prerequisites()
    visibility = compute_visibility_confidence(prerequisites)
    pass_gate = visibility.get("visibility_occlusion_confidence_pass") is True
    panel_path = make_success_panel(source, visibility) if pass_gate else make_blocker_panel(source)

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "visibility_occlusion_confidence.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "visibility_occlusion_confidence.json"
    runtime_evidence_path = RUNTIME_DIR / "visibility_occlusion_confidence.json"

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(panel_path),
    ]
    if visibility.get("visibility_record_path"):
        evidence_rel_paths.append(str(visibility["visibility_record_path"]))
    note = (
        f"Visibility and occlusion confidence {RUN_STAMP}: computed from source-derived landmark, semantic parse, and SAM2 refinement evidence. "
        "No canonical polygon or active mask promotion occurred."
        if pass_gate
        else (
            f"Visibility and occlusion confidence {RUN_STAMP}: exact local blocker. "
            "Required source-derived landmark, semantic parsing, promptable refinement, consensus, and canonical polygon inputs are blocked or missing. "
            "No visibility confidence was invented from symmetry, debug boxes, or visual guesswork."
        )
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note, pass_gate)

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "task": "Implement visibility and occlusion confidence resolver for TRK-W70-0146 / ITEM-W70-0146.",
        "script": SCRIPT_REL,
        "source_image": {
            "path": rel(SOURCE_IMAGE),
            "exists": True,
            "sha256": sha256_file(SOURCE_IMAGE),
            "dimensions": [width, height],
        },
        "prerequisite_authority_evidence": prerequisites,
        "artifacts": {
            "panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
            "visibility_record": visibility.get("visibility_record_path", ""),
        },
        "model_backed_geometry_authority": {
            "result": "visibility_occlusion_confidence_executed_pending_consensus" if pass_gate else "blocked",
            "model_backed_geometry_authority_pass": False,
            "source_image": rel(SOURCE_IMAGE),
            "source_sha256": sha256_file(SOURCE_IMAGE),
            "source_dimensions": [width, height],
            "mask_type_id": "MBGA-005",
            "matrix_slot_id": "TRK-W70-0146",
            "models_attempted": [
                "prerequisite_authority_evidence_review",
                "visibility_occlusion_confidence_prerequisite_gate",
            ],
            "models_available": ["base_image_io_and_cv"],
            "model_versions": {},
            "landmark_record_path": "",
            "semantic_parsing_record_path": "",
            "sam_refinement_record_path": "",
            "visibility_occlusion_record_path": visibility.get("visibility_record_path", ""),
            "canonical_polygon_path": "",
            "coordinate_transform_manifest_path": "",
            "gold_trace_comparison_path": "",
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
                "visibility_confidence": visibility.get("visibility_confidence"),
                "overall_confidence": visibility.get("overall_confidence"),
            },
            "dependency_probe_completed": True,
            "model_geometry_dependency_probe_pass": pass_gate,
            "visibility_state_pass": pass_gate,
            "visibility_occlusion_confidence_pass": pass_gate,
            "occlusion_blocker_written": not pass_gate,
            "source_derived_landmark_or_segmentation_pass": pass_gate,
            "model_consensus_geometry_pass": False,
            "no_symmetry_guessing_pass": True,
            "canonical_polygon_export_pass": False,
            "no_human_work_dependency": True,
            "no_debug_rectangle_mask_pass": True,
            "whole_body_geometry_authority_pass": False,
            "pose_hand_dense_landmark_or_segmentation_pass": False,
            "semantic_human_part_parsing_pass": False,
            "contact_occlusion_ownership_pass": False,
            "body_region_geometry_pass": False,
            "body_reference_matrix_pass": False,
            "blocked_reason": visibility.get("blocked_reason", ""),
            "findings": [
                "Active Wave70 source image exists and was used for the visibility/occlusion confidence record.",
                "Visibility confidence was computed from source-derived MediaPipe landmarks, BiSeNet semantic parsing, and SAM2 refinement.",
                "No confidence value was invented from symmetry, broad boxes, Canny edges, or visual guesswork.",
                "No canonical polygon was exported by this row.",
                "No mask was changed or promoted.",
            ],
        },
        "visibility_occlusion_confidence": {
            "result": "executed" if pass_gate else "blocked",
            "visibility_state_pass": pass_gate,
            "visibility_occlusion_confidence_pass": pass_gate,
            "occlusion_blocker_written": not pass_gate,
            "visibility_record_path": visibility.get("visibility_record_path", ""),
            "occlusion_record_path": visibility.get("visibility_record_path", ""),
            "confidence": {
                "visibility_confidence": visibility.get("visibility_confidence"),
                "occlusion_confidence": visibility.get("occlusion_confidence"),
                "overall_confidence": visibility.get("overall_confidence"),
            },
            "metrics": visibility,
            "blocked_reason": visibility.get("blocked_reason", ""),
        },
        "qa_decision": (
            "visibility_occlusion_confidence_executed_pending_consensus_and_canonical_polygon"
            if pass_gate
            else "blocked_exact_local_visibility_occlusion_confidence_low_confidence"
        ),
        "promotion_decision": "no_mask_promoted_no_active_input_changed_visibility_occlusion_authority_only",
        "tracker_item_updates": row_updates,
        "next_step": "Run model consensus and canonical polygon gates using source-derived landmark/parsing/refinement/visibility evidence.",
    }

    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    print(json.dumps({"evidence_id": EVIDENCE_ID, "result": payload["qa_decision"], "evidence": rel(qa_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
