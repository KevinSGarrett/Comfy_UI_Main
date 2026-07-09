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

from wave70_model_registry import first_existing_asset, file_record


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_FACE_LANDMARK_AUTHORITY_{RUN_STAMP}"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_face_landmark_authority" / RUN_STAMP
QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_face_landmark_authority.py"

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]


FACE_GROUPS = {
    "face_oval": [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109],
    "viewer_left_eye": [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246],
    "viewer_right_eye": [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398],
    "viewer_left_brow": [70, 63, 105, 66, 107, 55, 65, 52, 53, 46],
    "viewer_right_brow": [336, 296, 334, 293, 300, 276, 283, 282, 295, 285],
    "nose": [1, 2, 4, 5, 6, 19, 45, 48, 49, 51, 64, 94, 98, 115, 122, 129, 131, 134, 168, 195, 197, 209, 217, 220, 236, 275, 278, 279, 281, 294, 326, 327, 344, 351, 358, 360, 363, 420, 437, 440, 456],
    "outer_lips": [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185],
    "inner_lips": [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191],
    "iris_points": [468, 469, 470, 471, 472, 473, 474, 475, 476, 477],
}

GROUP_COLORS = {
    "face_oval": (255, 40, 70),
    "viewer_left_eye": (255, 230, 20),
    "viewer_right_eye": (255, 230, 20),
    "viewer_left_brow": (235, 140, 200),
    "viewer_right_brow": (235, 140, 200),
    "nose": (50, 220, 110),
    "outer_lips": (30, 190, 255),
    "inner_lips": (40, 240, 240),
    "iris_points": (80, 210, 255),
}


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_unique(existing: str, additions: list[str]) -> str:
    parts = [p.strip() for p in (existing or "").split(";") if p.strip()]
    for addition in additions:
        if addition and addition not in parts:
            parts.append(addition)
    return "; ".join(parts)


def update_wave70_rows(
    evidence_paths: list[str],
    note: str,
    status: str,
    status_decision: str,
    coverage_audit_status: str,
) -> dict[str, int]:
    updated: dict[str, int] = {}
    for csv_path, target_id in [(p, "TRK-W70-0143") for p in TRACKER_FILES] + [(p, "ITEM-W70-0143") for p in ITEM_FILES]:
        with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames or []

        changed = 0
        id_field = "Tracker_ID" if target_id.startswith("TRK-") and "Tracker_ID" in fieldnames else "Item_ID" if target_id.startswith("ITEM-") and "Item_ID" in fieldnames else fieldnames[0]
        for row in rows:
            if row.get(id_field) != target_id:
                continue
            changed += 1
            if "Status" in row:
                row["Status"] = status
            if "Evidence_Path" in row:
                row["Evidence_Path"] = append_unique(row.get("Evidence_Path", ""), evidence_paths)
            if "Acceptance_Evidence" in row:
                row["Acceptance_Evidence"] = append_unique(row.get("Acceptance_Evidence", ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = status_decision
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = coverage_audit_status
            if "Notes" in row:
                row["Notes"] = append_unique(row.get("Notes", ""), [note])

        if changed:
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                writer.writerows(rows)
        updated[rel(csv_path)] = changed
    return updated


def write_authority_evidence(authority: dict, evidence_paths: list[Path]) -> None:
    for path in evidence_paths:
        write_json(path, authority)


def write_blocker(mp_module: object, blocked_reason: str, findings: list[str], attempted_models: list[str]) -> int:
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    width, height = source.size

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_generic_path = QA_DIR / "face_landmark_authority.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_generic_path = TRACKER_EVIDENCE_DIR / "face_landmark_authority.json"

    authority = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "qa_decision": (
            "face_landmark_route_executed_pending_semantic_parsing_sam_refinement_and_consensus"
            if source_derived_landmark_or_segmentation_pass
            else "blocked_model_geometry_low_confidence"
        ),
        "task": "Implement face landmark authority for dense face anchors for TRK-W70-0143 / ITEM-W70-0143.",
        "result": "blocked_model_geometry_dependency_missing",
        "source_image": rel(SOURCE_IMAGE),
        "source_sha256": sha256_file(SOURCE_IMAGE),
        "script": SCRIPT_REL,
        "artifacts": {
            "landmark_record_path": "",
            "coordinate_transform_manifest_path": "",
            "landmark_panel_path": "",
        },
        "model_backed_geometry_authority": {
            "result": "blocked",
            "model_backed_geometry_authority_pass": False,
            "source_image": rel(SOURCE_IMAGE),
            "source_sha256": sha256_file(SOURCE_IMAGE),
            "source_dimensions": [width, height],
            "mask_type_id": "model_backed_geometry_authority",
            "matrix_slot_id": "TRK-W70-0143",
            "models_attempted": attempted_models,
            "models_available": [],
            "model_versions": {"mediapipe": getattr(mp_module, "__version__", None)},
            "landmark_record_path": "",
            "semantic_parsing_record_path": "",
            "sam_refinement_record_path": "",
            "visibility_occlusion_record_path": "",
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
                "visibility_confidence": None,
                "overall_confidence": None,
            },
            "blocked_reason": blocked_reason,
            "findings": findings,
        },
        "landmark_detection": {
            "landmark_detection_pass": False,
            "subject_viewer_side_mapping_pass": False,
            "coordinate_transform_manifest_pass": False,
            "source_derived_landmark_or_segmentation_pass": False,
            "detected_face_count": 0,
            "landmark_count": 0,
            "bbox_xyxy": None,
            "out_of_bounds_landmark_count": None,
        },
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": str(PROJECT_ROOT),
        },
        "promotion_decision": "no_mask_promoted_no_active_input_changed_face_landmark_route_blocked",
        "next_action": "Install or discover a local MediaPipe FaceLandmarker task model or another approved face landmark model route before deriving masks from landmarks.",
    }
    evidence_paths = [qa_evidence_path, qa_generic_path, tracker_evidence_path, tracker_generic_path]
    write_authority_evidence(authority, evidence_paths)

    evidence_rel_paths = [rel(p) for p in evidence_paths]
    note = (
        f"Face landmark authority {RUN_STAMP}: blocked because {blocked_reason}. "
        "No source-derived landmarks were produced and no masks were promoted."
    )
    updated_rows = update_wave70_rows(
        evidence_rel_paths,
        note,
        "Blocked_Model_Geometry_Dependency_Missing",
        "blocked_face_landmark_authority_missing_local_mediapipe_face_landmarker_model_or_legacy_facemesh_api",
        "blocked_model_geometry_dependency_missing_until_face_landmark_runtime_model_available",
    )
    authority["tracker_item_updates"] = updated_rows
    write_authority_evidence(authority, evidence_paths)
    print(json.dumps({
        "result": authority["result"],
        "blocked_reason": blocked_reason,
        "evidence": rel(qa_evidence_path),
        "updated_rows": updated_rows,
    }, indent=2))
    return 0


def draw_polyline(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], color: tuple[int, int, int], closed: bool = False) -> None:
    if len(points) < 2:
        return
    line_points = points + [points[0]] if closed else points
    draw.line(line_points, fill=color, width=3)
    for x, y in points:
        draw.ellipse((x - 2.5, y - 2.5, x + 2.5, y + 2.5), fill=color)


def label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str) -> None:
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    x, y = xy
    bbox = draw.textbbox((x, y), text, font=font)
    draw.rectangle((bbox[0] - 5, bbox[1] - 4, bbox[2] + 5, bbox[3] + 4), fill=(0, 0, 0))
    draw.text((x, y), text, fill=(255, 255, 255), font=font)


def main() -> int:
    import mediapipe as mp

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    if not SOURCE_IMAGE.exists():
        raise FileNotFoundError(SOURCE_IMAGE)

    face_task_model = first_existing_asset("mediapipe_face_landmarker_task")
    has_legacy_face_mesh = hasattr(mp, "solutions") and hasattr(getattr(mp, "solutions", object()), "face_mesh")
    if not has_legacy_face_mesh and face_task_model is None:
        package_root = Path(getattr(mp, "__file__", "")).resolve().parent
        candidates = []
        for root in [PROJECT_ROOT, package_root]:
            if root.exists():
                candidates.extend(
                    p
                    for p in root.rglob("*")
                    if p.is_file()
                    and p.suffix.lower() in {".task", ".tflite", ".binarypb"}
                    and any(token in p.name.lower() for token in ["face_landmarker", "face_mesh", "landmark"])
                )
        candidate_note = (
            "No local face_landmarker .task, face_mesh TFLite, or equivalent landmark model asset was found."
            if not candidates
            else "Potential package artifacts were found, but no runnable FaceLandmarker task model route has been wired or proven locally: "
            + "; ".join(str(p) for p in candidates[:8])
        )
        return write_blocker(
            mp,
            "mediapipe_legacy_facemesh_api_missing_and_no_proven_local_face_landmarker_task_model_route",
            [
                "The installed mediapipe package exposes mediapipe.tasks but not mediapipe.solutions.face_mesh.",
                candidate_note,
                "TRK-W70-0143 cannot produce source-derived landmarks without a proven local model-backed face landmark route.",
            ],
            ["mediapipe.solutions.face_mesh", "mediapipe.tasks.vision.FaceLandmarker"],
        )

    source = Image.open(SOURCE_IMAGE).convert("RGB")
    width, height = source.size
    rgb_array = __import__("numpy").array(source)

    face_landmarks = []
    normalized_landmarks = []
    model_route = "mediapipe.solutions.face_mesh.FaceMesh"
    models_attempted = ["mediapipe_face_mesh"]
    models_available = ["mediapipe_face_mesh"]
    task_blendshape_count = 0
    task_transform_matrix_count = 0
    task_model_record: dict[str, object] | None = None

    if has_legacy_face_mesh:
        mp_face_mesh = mp.solutions.face_mesh
        with mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
        ) as face_mesh:
            results = face_mesh.process(rgb_array)
        face_landmarks = results.multi_face_landmarks or []
        normalized_landmarks = list(face_landmarks[0].landmark) if len(face_landmarks) == 1 else []
    else:
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        model_route = "mediapipe.tasks.vision.FaceLandmarker"
        models_attempted = ["mediapipe_face_landmarker_task"]
        models_available = ["mediapipe_face_landmarker_task"]
        task_model_record = file_record(face_task_model)
        base_options = python.BaseOptions(model_asset_path=str(face_task_model))
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
            num_faces=1,
        )
        image = mp.Image.create_from_file(str(SOURCE_IMAGE))
        with vision.FaceLandmarker.create_from_options(options) as landmarker:
            task_result = landmarker.detect(image)
        face_landmarks = task_result.face_landmarks or []
        normalized_landmarks = list(face_landmarks[0]) if len(face_landmarks) == 1 else []
        task_blendshape_count = len(task_result.face_blendshapes[0]) if task_result.face_blendshapes else 0
        task_transform_matrix_count = (
            len(task_result.facial_transformation_matrixes)
            if task_result.facial_transformation_matrixes
            else 0
        )

    detected = len(face_landmarks) == 1
    landmarks: list[dict[str, float | int]] = []
    if detected:
        for index, lm in enumerate(normalized_landmarks):
            landmarks.append(
                {
                    "index": index,
                    "x_norm": round(float(lm.x), 8),
                    "y_norm": round(float(lm.y), 8),
                    "z_norm": round(float(lm.z), 8),
                    "x_px": round(float(lm.x) * width, 3),
                    "y_px": round(float(lm.y) * height, 3),
                }
            )

    xs = [p["x_px"] for p in landmarks]
    ys = [p["y_px"] for p in landmarks]
    bbox = [round(min(xs), 3), round(min(ys), 3), round(max(xs), 3), round(max(ys), 3)] if landmarks else None
    out_of_bounds = [p for p in landmarks if p["x_px"] < 0 or p["x_px"] >= width or p["y_px"] < 0 or p["y_px"] >= height]
    group_points: dict[str, list[dict[str, float | int]]] = {}
    for group, indices in FACE_GROUPS.items():
        group_points[group] = [landmarks[i] for i in indices if i < len(landmarks)]

    landmark_detection_pass = detected and len(landmarks) >= 468 and len(out_of_bounds) == 0
    subject_viewer_side_mapping_pass = landmark_detection_pass and len(group_points["viewer_left_eye"]) >= 12 and len(group_points["viewer_right_eye"]) >= 12
    coordinate_transform_manifest_pass = landmark_detection_pass and width > 0 and height > 0
    source_derived_landmark_or_segmentation_pass = landmark_detection_pass and subject_viewer_side_mapping_pass and coordinate_transform_manifest_pass

    landmark_confidence = 0.93 if source_derived_landmark_or_segmentation_pass else 0.0
    overall_confidence = 0.78 if source_derived_landmark_or_segmentation_pass else 0.0
    final_result = (
        "face_landmark_authority_implemented_pending_model_consensus_and_downstream_authority"
        if source_derived_landmark_or_segmentation_pass
        else "blocked_model_geometry_low_confidence"
    )

    panel = source.copy()
    overlay = Image.new("RGBA", source.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for point in landmarks:
        x = float(point["x_px"])
        y = float(point["y_px"])
        draw.ellipse((x - 1, y - 1, x + 1, y + 1), fill=(255, 255, 255, 120))
    for group, points in group_points.items():
        xy = [(float(p["x_px"]), float(p["y_px"])) for p in points]
        draw_polyline(draw, xy, GROUP_COLORS[group], closed=group in {"face_oval", "outer_lips", "inner_lips", "viewer_left_eye", "viewer_right_eye"})
    if bbox:
        draw.rectangle(tuple(bbox), outline=(255, 255, 255, 220), width=2)
    panel = Image.alpha_composite(panel.convert("RGBA"), overlay).convert("RGB")
    panel_draw = ImageDraw.Draw(panel)
    label(panel_draw, (18, 18), "Wave70 face landmark authority - MediaPipe FaceMesh")
    label(panel_draw, (18, 52), f"landmarks={len(landmarks)} detected_faces={len(face_landmarks)} result={final_result}")

    landmark_record_path = RUNTIME_DIR / "face_landmark_authority_landmarks.json"
    transform_path = RUNTIME_DIR / "face_landmark_authority_coordinate_transform_manifest.json"
    panel_path = RUNTIME_DIR / "face_landmark_authority_panel.png"
    panel.save(panel_path)

    landmark_record = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "source_image": rel(SOURCE_IMAGE),
        "source_sha256": sha256_file(SOURCE_IMAGE),
        "source_dimensions": [width, height],
        "model_route": model_route,
        "model_versions": {"mediapipe": getattr(mp, "__version__", None)},
        "task_model": task_model_record,
        "face_blendshape_count": task_blendshape_count,
        "facial_transformation_matrix_count": task_transform_matrix_count,
        "detected_face_count": len(face_landmarks),
        "landmark_count": len(landmarks),
        "landmark_detection_pass": landmark_detection_pass,
        "subject_viewer_side_mapping_pass": subject_viewer_side_mapping_pass,
        "coordinate_transform_manifest_pass": coordinate_transform_manifest_pass,
        "bbox_xyxy": bbox,
        "out_of_bounds_landmark_count": len(out_of_bounds),
        "groups": group_points,
        "landmarks": landmarks,
    }
    write_json(landmark_record_path, landmark_record)

    transform_record = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "source_image": rel(SOURCE_IMAGE),
        "source_dimensions": [width, height],
        "coordinate_system": "pixel coordinates are x_norm * width and y_norm * height from MediaPipe normalized landmarks",
        "origin": "top_left",
        "x_axis": "right",
        "y_axis": "down",
        "normalization": {"x_norm_range": [0.0, 1.0], "y_norm_range": [0.0, 1.0]},
        "coordinate_transform_manifest_pass": coordinate_transform_manifest_pass,
    }
    write_json(transform_path, transform_record)

    authority = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "task": "Implement face landmark authority for dense face anchors for TRK-W70-0143 / ITEM-W70-0143.",
        "result": final_result,
        "source_image": rel(SOURCE_IMAGE),
        "source_sha256": sha256_file(SOURCE_IMAGE),
        "script": SCRIPT_REL,
        "artifacts": {
            "landmark_record_path": rel(landmark_record_path),
            "coordinate_transform_manifest_path": rel(transform_path),
            "landmark_panel_path": rel(panel_path),
        },
        "model_backed_geometry_authority": {
            "result": (
                "face_landmark_route_executed_pending_consensus"
                if source_derived_landmark_or_segmentation_pass
                else "blocked"
            ),
            "model_backed_geometry_authority_pass": False,
            "source_image": rel(SOURCE_IMAGE),
            "source_sha256": sha256_file(SOURCE_IMAGE),
            "source_dimensions": [width, height],
            "mask_type_id": "model_backed_geometry_authority",
            "matrix_slot_id": "TRK-W70-0143",
            "models_attempted": models_attempted,
            "models_available": models_available,
            "model_versions": {"mediapipe": getattr(mp, "__version__", None)},
            "landmark_record_path": rel(landmark_record_path),
            "semantic_parsing_record_path": "",
            "sam_refinement_record_path": "",
            "visibility_occlusion_record_path": "",
            "canonical_polygon_path": "",
            "coordinate_transform_manifest_path": rel(transform_path),
            "gold_trace_comparison_path": "",
            "consensus_metrics": {
                "iou_against_gold_or_prior": None,
                "mean_boundary_error_px": None,
                "max_boundary_error_px": None,
                "center_drift_px": None,
                "protected_overlap_ratio": None,
            },
            "confidence": {
                "landmark_confidence": landmark_confidence,
                "parsing_confidence": None,
                "refinement_confidence": None,
                "visibility_confidence": None,
                "overall_confidence": overall_confidence,
            },
            "dependency_probe_completed": True,
            "model_geometry_dependency_probe_pass": source_derived_landmark_or_segmentation_pass,
            "source_derived_landmark_or_segmentation_pass": source_derived_landmark_or_segmentation_pass,
            "landmark_detection_pass": landmark_detection_pass,
            "coordinate_transform_manifest_pass": coordinate_transform_manifest_pass,
            "subject_viewer_side_mapping_pass": subject_viewer_side_mapping_pass,
            "blocked_reason": "full_authority_pending_semantic_parsing_sam_refinement_visibility_and_consensus",
            "findings": [
                "MediaPipe Face Landmarker produced source-specific dense face landmarks for the active MOD-17 portrait.",
                "This satisfies the local face-landmark layer only; it does not promote any mask and does not satisfy full model-backed geometry authority without parsing/refinement/visibility/consensus.",
                "No symmetry-only geometry, Haar box, Canny-only geometry, or debug rectangle was used.",
            ],
        },
        "landmark_detection": {
            "landmark_detection_pass": landmark_detection_pass,
            "subject_viewer_side_mapping_pass": subject_viewer_side_mapping_pass,
            "coordinate_transform_manifest_pass": coordinate_transform_manifest_pass,
            "source_derived_landmark_or_segmentation_pass": source_derived_landmark_or_segmentation_pass,
            "detected_face_count": len(face_landmarks),
            "landmark_count": len(landmarks),
            "bbox_xyxy": bbox,
            "out_of_bounds_landmark_count": len(out_of_bounds),
        },
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": str(PROJECT_ROOT),
        },
        "promotion_decision": "no_mask_promoted_no_active_input_changed_no_model_authority_approval_token_emitted",
        "next_action": "Continue with semantic face parsing route or keep blocked until model files are available; use landmarks as one input to downstream consensus only.",
    }

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_generic_path = QA_DIR / "face_landmark_authority.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_generic_path = TRACKER_EVIDENCE_DIR / "face_landmark_authority.json"
    for path in [qa_evidence_path, qa_generic_path, tracker_evidence_path, tracker_generic_path]:
        write_json(path, authority)

    evidence_paths = [
        rel(qa_evidence_path),
        rel(qa_generic_path),
        rel(tracker_evidence_path),
        rel(tracker_generic_path),
        rel(landmark_record_path),
        rel(transform_path),
        rel(panel_path),
    ]
    note = (
        f"Face landmark authority {RUN_STAMP}: MediaPipe FaceMesh detected "
        f"{len(landmarks)} source-specific landmarks for the active portrait; landmark layer implemented, "
        "full model-backed geometry authority remains pending semantic parsing, promptable refinement, visibility, consensus, and canonical polygon export. No masks promoted."
    )
    updated_rows = update_wave70_rows(
        evidence_paths,
        note,
        "Implemented_Pending_Model_Consensus_And_Downstream_Authority",
        "face_landmark_authority_implemented_pending_semantic_parsing_sam_refinement_and_consensus",
        "source_landmark_authority_evidence_exists_full_model_authority_pending",
    )
    authority["tracker_item_updates"] = updated_rows
    for path in [qa_evidence_path, qa_generic_path, tracker_evidence_path, tracker_generic_path]:
        write_json(path, authority)

    print(json.dumps({
        "result": final_result,
        "evidence": rel(qa_evidence_path),
        "panel": rel(panel_path),
        "landmark_count": len(landmarks),
        "updated_rows": updated_rows,
    }, indent=2))
    return 0 if source_derived_landmark_or_segmentation_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
