from __future__ import annotations

import csv
import hashlib
import importlib
import importlib.util
import json
import os
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[3]
LORA_OPENPOSE_MODELS = Path(r"C:\Comfy_UI_Lora\OpenPose\models")
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
REF_IMAGE_1 = PROJECT_ROOT / "Ref_Image_1/725de85824bbe45ba4601dd4a7aed698.jpg"
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_WHOLE_BODY_GEOMETRY_DEPENDENCY_PROBE_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/probe_wave70_whole_body_geometry_dependencies.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_whole_body_geometry_dependency_probe" / RUN_STAMP

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]

IMPORT_PROBES = {
    "python_numpy": "numpy",
    "python_pil": "PIL",
    "python_cv2": "cv2",
    "python_imageio": "imageio",
    "python_torch": "torch",
    "python_torchvision": "torchvision",
    "python_mediapipe": "mediapipe",
    "python_onnxruntime": "onnxruntime",
    "python_ultralytics": "ultralytics",
    "python_segment_anything": "segment_anything",
    "python_sam2": "sam2",
    "python_skimage": "skimage",
    "python_scipy": "scipy",
    "python_mmpose": "mmpose",
    "python_mmseg": "mmseg",
    "python_detectron2": "detectron2",
    "python_densepose": "densepose",
}

MODEL_EXTENSIONS = {".task", ".tflite", ".onnx", ".pt", ".pth", ".safetensors", ".ckpt", ".bin"}
MODEL_SEARCH_ROOTS = [
    PROJECT_ROOT / "models",
    PROJECT_ROOT / "ComfyUI/models",
    Path(r"C:\Comfy_UI\models"),
    Path(r"C:\Comfy_UI\ComfyUI\models"),
    PROJECT_ROOT / "tools",
    LORA_OPENPOSE_MODELS,
    Path.home() / ".cache",
]

KNOWN_ASSETS = {
    "mediapipe_pose_landmarker_task": [
        LORA_OPENPOSE_MODELS / "mediapipe/pose_landmarker_heavy.task",
        PROJECT_ROOT / "ComfyUI/models/mediapipe/pose_landmarker_heavy.task",
    ],
    "mediapipe_hand_landmarker_task": [
        LORA_OPENPOSE_MODELS / "mediapipe/hand_landmarker.task",
        PROJECT_ROOT / "ComfyUI/models/mediapipe/hand_landmarker.task",
    ],
    "dwpose_detector_onnx": [
        LORA_OPENPOSE_MODELS / "dwpose/yolox_l.onnx",
    ],
    "dwpose_pose_onnx": [
        LORA_OPENPOSE_MODELS / "dwpose/dw-ll_ucoco_384.onnx",
    ],
    "sam2_hiera_tiny_checkpoint": [
        LORA_OPENPOSE_MODELS / "sam2/sam2.1_hiera_tiny.pt",
    ],
    "ultralytics_yolo_pose": [
        LORA_OPENPOSE_MODELS / "ultralytics/yolo11x-pose.pt",
    ],
    "bisenet_face_parsing_checkpoint": [
        LORA_OPENPOSE_MODELS / "face_parsing/79999_iter.pth",
    ],
    "schp_lip_checkpoint": [
        LORA_OPENPOSE_MODELS / "schp/exp-schp-201908261155-lip.pth",
    ],
    "densepose_base_config": [
        LORA_OPENPOSE_MODELS / "densepose/Base-DensePose-RCNN-FPN.yaml",
    ],
    "densepose_model_config": [
        LORA_OPENPOSE_MODELS / "densepose/densepose_rcnn_R_50_FPN_s1x.yaml",
    ],
    "densepose_checkpoint": [
        LORA_OPENPOSE_MODELS / "densepose/model_final_162be9.pkl",
    ],
}

KEYWORD_GROUPS = {
    "mediapipe_task_models": [
        "pose_landmarker",
        "hand_landmarker",
        "holistic_landmarker",
        "image_segmenter",
        "selfie_segmenter",
        "mediapipe",
    ],
    "pose_hand_models": ["openpose", "dwpose", "rtmpose", "mmpose", "pose", "hand", "wholebody"],
    "human_part_parsing_models": [
        "human_parsing",
        "schp",
        "cihp",
        "parsing",
        "segformer",
        "mask2former",
        "body_part",
        "part_seg",
        "densepose",
    ],
    "person_instance_segmentation_models": [
        "yolo",
        "yolov",
        "mask_rcnn",
        "mask-rcnn",
        "detectron",
        "instance",
        "person",
        "coco",
    ],
    "sam_promptable_segmentation_models": ["sam", "sam2", "mobile_sam", "segment_anything"],
    "temporal_video_models": ["xmem", "aot", "deva", "track", "tracking", "raft", "optical", "flow", "propagation"],
}


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


def import_probe(module_name: str) -> dict[str, Any]:
    record: dict[str, Any] = {"module": module_name, "available": False, "version": None, "error": None}
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            record["error"] = "module_spec_not_found"
            return record
        module = importlib.import_module(module_name)
        record["available"] = True
        record["version"] = getattr(module, "__version__", None)
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def mediapipe_surface_probe(imports: dict[str, Any]) -> dict[str, Any]:
    if not imports["python_mediapipe"]["available"]:
        return {"available": False, "error": "mediapipe_import_unavailable"}
    try:
        import mediapipe as mp
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    solutions = getattr(mp, "solutions", None)
    tasks = getattr(mp, "tasks", None)
    return {
        "available": True,
        "version": getattr(mp, "__version__", None),
        "has_solutions": solutions is not None,
        "has_solutions_pose": bool(solutions is not None and hasattr(solutions, "pose")),
        "has_solutions_hands": bool(solutions is not None and hasattr(solutions, "hands")),
        "has_solutions_selfie_segmentation": bool(solutions is not None and hasattr(solutions, "selfie_segmentation")),
        "has_tasks": tasks is not None,
        "tasks_surface": [name for name in dir(tasks) if not name.startswith("_")][:80] if tasks is not None else [],
    }


def safe_model_record(path: Path) -> dict[str, Any]:
    stat = path.stat()
    record: dict[str, Any] = {
        "path": str(path),
        "name": path.name,
        "suffix": path.suffix.lower(),
        "size_bytes": int(stat.st_size),
    }
    if stat.st_size <= 256 * 1024 * 1024:
        record["sha256"] = sha256_file(path)
    else:
        record["sha256"] = "skipped_large_file"
    return record


def known_asset_records() -> dict[str, Any]:
    records: dict[str, Any] = {}
    for asset_id, candidates in KNOWN_ASSETS.items():
        candidate_records = []
        selected = ""
        for candidate in candidates:
            record: dict[str, Any] = {
                "path": str(candidate),
                "exists": candidate.exists(),
                "relative_path": rel(candidate) if candidate.exists() and PROJECT_ROOT in candidate.resolve().parents else str(candidate),
            }
            if candidate.exists():
                selected = selected or str(candidate)
                record.update(safe_model_record(candidate))
            candidate_records.append(record)
        records[asset_id] = {"selected_path": selected, "candidates": candidate_records}
    return records


def asset_exists(assets: dict[str, Any], asset_id: str) -> bool:
    return bool(assets.get(asset_id, {}).get("selected_path"))


def scan_models() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    roots: list[dict[str, Any]] = []
    for root in MODEL_SEARCH_ROOTS:
        root_record: dict[str, Any] = {"root": str(root), "exists": root.exists(), "scanned": False, "matched_count": 0}
        roots.append(root_record)
        if not root.exists() or not root.is_dir():
            continue
        root_record["scanned"] = True
        for current_root, dirnames, filenames in os.walk(root):
            lower_root = current_root.lower()
            if any(skip in lower_root for skip in ("\\output", "\\outputs", "\\temp", "\\tmp", "\\runtime_artifacts")):
                dirnames[:] = []
                continue
            for filename in filenames:
                if Path(filename).suffix.lower() not in MODEL_EXTENSIONS:
                    continue
                records.append(safe_model_record(Path(current_root) / filename))
                root_record["matched_count"] += 1
    grouped = {group: [] for group in KEYWORD_GROUPS}
    for record in records:
        haystack = f"{record.get('path', '')} {record.get('name', '')}".lower()
        for group, keywords in KEYWORD_GROUPS.items():
            if any(keyword in haystack for keyword in keywords):
                grouped[group].append(record)
    return {"roots": roots, "matched_model_files": records, "keyword_groups": grouped, "known_assets": known_asset_records()}


def task_model_exists(groups: dict[str, list[dict[str, Any]]], token: str) -> bool:
    return any(token in record.get("name", "").lower() for record in groups["mediapipe_task_models"])


def evaluate_routes(imports: dict[str, Any], models: dict[str, Any], mp_surface: dict[str, Any]) -> dict[str, Any]:
    groups = models["keyword_groups"]
    assets = models["known_assets"]
    has_torch = imports["python_torch"]["available"]
    has_cv2 = imports["python_cv2"]["available"]
    has_onnx = imports["python_onnxruntime"]["available"]
    pose_asset_available = (
        bool(mp_surface.get("has_solutions_pose"))
        or task_model_exists(groups, "pose_landmarker")
        or asset_exists(assets, "mediapipe_pose_landmarker_task")
        or (asset_exists(assets, "dwpose_detector_onnx") and asset_exists(assets, "dwpose_pose_onnx") and has_onnx)
        or asset_exists(assets, "ultralytics_yolo_pose")
    )
    hand_asset_available = (
        bool(mp_surface.get("has_solutions_hands"))
        or task_model_exists(groups, "hand_landmarker")
        or asset_exists(assets, "mediapipe_hand_landmarker_task")
    )
    promptable_asset_available = (
        (bool(groups["sam_promptable_segmentation_models"]) or asset_exists(assets, "sam2_hiera_tiny_checkpoint"))
        and (imports["python_segment_anything"]["available"] or imports["python_sam2"]["available"])
        and has_torch
    )
    densepose_assets_available = (
        asset_exists(assets, "densepose_base_config")
        and asset_exists(assets, "densepose_model_config")
        and asset_exists(assets, "densepose_checkpoint")
    )
    densepose_runtime_available = (
        densepose_assets_available
        and imports["python_detectron2"]["available"]
        and imports["python_densepose"]["available"]
        and has_torch
    )
    person_instance_asset_available = any(
        record.get("name", "").lower().endswith(("-seg.pt", "-seg.onnx"))
        or "mask_rcnn" in record.get("name", "").lower()
        or "detectron" in record.get("name", "").lower()
        for record in groups["person_instance_segmentation_models"]
    )
    full_body_part_parse_asset_available = any(
        token in f"{record.get('path', '')} {record.get('name', '')}".lower()
        for record in groups["human_part_parsing_models"]
        for token in ("human_parsing", "cihp", "atr", "body_part", "part_seg")
    )
    routes = {
        "base_image_video_io": {
            "available": imports["python_numpy"]["available"] and imports["python_pil"]["available"] and has_cv2,
            "evidence": ["numpy", "PIL", "cv2"],
        },
        "pose_landmark_route": {
            "available": pose_asset_available,
            "runtime_validated": False,
            "evidence": ["mediapipe pose task", "DWPose ONNX pair", "YOLO pose"],
            "known_assets": {
                "mediapipe_pose_landmarker_task": assets["mediapipe_pose_landmarker_task"],
                "dwpose_detector_onnx": assets["dwpose_detector_onnx"],
                "dwpose_pose_onnx": assets["dwpose_pose_onnx"],
                "ultralytics_yolo_pose": assets["ultralytics_yolo_pose"],
            },
            "available_but_unproven_model_files": groups["pose_hand_models"][:20],
        },
        "hand_landmark_route": {
            "available": hand_asset_available,
            "runtime_validated": False,
            "evidence": ["mediapipe hand task"],
            "known_assets": {"mediapipe_hand_landmarker_task": assets["mediapipe_hand_landmarker_task"]},
            "available_but_unproven_model_files": groups["pose_hand_models"][:20],
        },
        "human_part_parsing_route": {
            "available": (full_body_part_parse_asset_available and (has_torch or has_onnx)) or densepose_runtime_available,
            "runtime_validated": False,
            "evidence": ["full-body human parsing/body-part model file", "torch or onnxruntime", "or DensePose checkpoint plus Detectron2/DensePose runtime"],
            "not_counted_as_full_body": {
                "bisenet_face_parsing_checkpoint": assets["bisenet_face_parsing_checkpoint"],
                "schp_lip_checkpoint": assets["schp_lip_checkpoint"],
            },
            "densepose_candidate": {
                "assets_available": densepose_assets_available,
                "runtime_available": densepose_runtime_available,
                "runtime_requires": ["detectron2", "densepose", "torch"],
                "assets": {
                    "densepose_base_config": assets["densepose_base_config"],
                    "densepose_model_config": assets["densepose_model_config"],
                    "densepose_checkpoint": assets["densepose_checkpoint"],
                },
            },
        },
        "person_instance_segmentation_route": {
            "available": person_instance_asset_available
            and (imports["python_ultralytics"]["available"] or imports["python_detectron2"]["available"] or has_torch or has_onnx),
            "runtime_validated": False,
            "evidence": ["person instance segmentation model file", "ultralytics/detectron2/torch/onnxruntime"],
            "available_but_not_instance_segmentation": {
                "ultralytics_yolo_pose": assets["ultralytics_yolo_pose"],
            },
        },
        "promptable_segmentation_refinement_route": {
            "available": promptable_asset_available,
            "runtime_validated": False,
            "evidence": ["SAM/SAM2 model file", "segment_anything or sam2 import", "torch"],
            "known_assets": {"sam2_hiera_tiny_checkpoint": assets["sam2_hiera_tiny_checkpoint"]},
        },
        "temporal_propagation_route": {
            "available": bool(groups["temporal_video_models"]),
            "runtime_validated": False,
            "evidence": ["tracking/propagation/optical-flow model file"],
        },
    }
    routes["contact_occlusion_ownership_route"] = {
        "available": bool(
            routes["pose_landmark_route"]["available"]
            and routes["hand_landmark_route"]["available"]
            and routes["person_instance_segmentation_route"]["available"]
            and routes["human_part_parsing_route"]["available"]
        ),
        "evidence": ["pose route", "hand route", "person instance route", "human parsing route"],
    }
    required = [
        "base_image_video_io",
        "pose_landmark_route",
        "hand_landmark_route",
        "human_part_parsing_route",
        "person_instance_segmentation_route",
        "promptable_segmentation_refinement_route",
        "temporal_propagation_route",
        "contact_occlusion_ownership_route",
    ]
    missing = [name for name in required if not routes[name]["available"]]
    available_but_unvalidated = [
        name for name in required if routes[name]["available"] and routes[name].get("runtime_validated") is False
    ]
    return {
        "routes": routes,
        "required_route_names": required,
        "missing_required_routes": missing,
        "available_but_unvalidated_routes": available_but_unvalidated,
        "required_stack_available": not missing,
    }


def write_panel(path: Path, route_eval: dict[str, Any], source_exists: bool, ref_exists: bool) -> None:
    lines = [
        "TRK-W70-0162 / ITEM-W70-0162 - whole-body dependency/model probe",
        f"Source image exists: {source_exists}",
        f"Ref_Image_1 exists: {ref_exists}",
        "Ref_Image_1 layout rule: top strip is partial upper-body only; lower strip is full-body validation.",
        "",
        "Route status:",
    ]
    for name in route_eval["required_route_names"]:
        route = route_eval["routes"][name]
        state = "asset_available_unvalidated" if route["available"] else "missing"
        if name == "base_image_video_io" and route["available"]:
            state = "available"
        lines.append(f"- {name}: {state}")
    lines.extend(
        [
            "",
            "Decision: fail-closed; no whole-body geometry authority pass and no mask promotion.",
            "Missing routes: " + ", ".join(route_eval["missing_required_routes"]),
        ]
    )
    width, height = 1600, 900
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    y = 30
    for index, line in enumerate(lines):
        fill = "black"
        if "missing" in line or "fail-closed" in line:
            fill = (130, 0, 0)
        if "asset_available_unvalidated" in line:
            fill = (120, 80, 0)
        draw.text((30, y), line, fill=fill)
        y += 34 if index else 46
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def update_wave70_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updates: dict[str, int] = {}
    pairs = [(path, "TRK-W70-0162") for path in TRACKER_FILES] + [(path, "ITEM-W70-0162") for path in ITEM_FILES]
    for csv_path, target_id in pairs:
        if not csv_path.exists():
            updates[rel(csv_path)] = 0
            continue
        with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fieldnames = reader.fieldnames or []
        id_field = "Tracker_ID" if target_id.startswith("TRK-") else "Item_ID"
        if id_field not in fieldnames:
            id_field = fieldnames[0]
        changed = 0
        for row in rows:
            if row.get(id_field) != target_id:
                continue
            changed += 1
            row["Status"] = "Blocked_Body_Geometry_Dependency_Missing"
            for field in ("Evidence_Path", "Acceptance_Evidence"):
                if field in row:
                    row[field] = append_unique(row.get(field, ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = "blocked_body_geometry_dependency_missing_until_pose_hand_human_parsing_instance_sam_temporal_and_contact_routes_are_available"
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = "blocked_body_geometry_dependency_missing_until_exact_local_model_routes_available"
            if "Notes" in row:
                row["Notes"] = append_unique(row.get("Notes", ""), [note])
        if changed:
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                writer.writerows(rows)
        updates[rel(csv_path)] = changed
    return updates


def main() -> int:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    imports = {name: import_probe(module) for name, module in IMPORT_PROBES.items()}
    mp_surface = mediapipe_surface_probe(imports)
    models = scan_models()
    route_eval = evaluate_routes(imports, models, mp_surface)
    source_exists = SOURCE_IMAGE.exists()
    ref_exists = REF_IMAGE_1.exists()
    source_sha = sha256_file(SOURCE_IMAGE) if source_exists else None
    ref_sha = sha256_file(REF_IMAGE_1) if ref_exists else None
    missing = route_eval["missing_required_routes"]
    unvalidated = route_eval["available_but_unvalidated_routes"]
    result = "blocked_body_geometry_dependency_missing" if missing else "dependency_probe_needs_runtime_validation"
    findings = [
        "Active Wave70 source image exists for whole-body geometry dependency probing." if source_exists else "Active Wave70 source image is missing.",
        "Base local image/CV stack is available." if route_eval["routes"]["base_image_video_io"]["available"] else "Base local image/CV stack is incomplete.",
    ]
    findings.extend(f"Required whole-body route unavailable or incomplete: {route}." for route in missing)
    findings.extend(f"Required whole-body route has local assets but still needs runtime validation: {route}." for route in unvalidated)
    findings.append("No body, hand, contact, soft-body, or temporal mask may be promoted from broad boxes, Canny edges, generated-output stability, or manual single-image geometry.")
    panel_path = RUNTIME_DIR / "body_geometry_dependency_probe_panel.png"
    write_panel(panel_path, route_eval, source_exists, ref_exists)

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "task": "Probe local whole-body geometry dependencies and model files for TRK-W70-0162 / ITEM-W70-0162.",
        "script": SCRIPT_REL,
        "source_image": {"path": rel(SOURCE_IMAGE) if source_exists else str(SOURCE_IMAGE), "exists": source_exists, "sha256": source_sha},
        "ref_image_1": {
            "path": rel(REF_IMAGE_1) if ref_exists else str(REF_IMAGE_1),
            "exists": ref_exists,
            "sha256": ref_sha,
            "layout_interpretation": {
                "top_strip": "partial upper-body / one-third-body reference only; missing lower/full-body parts here are not failures",
                "lower_strip": "primary full-body pose and body-mask validation region",
            },
        },
        "environment": {"python_executable": sys.executable, "python_version": sys.version, "platform": platform.platform(), "cwd": str(PROJECT_ROOT)},
        "imports": imports,
        "mediapipe_runtime_surface": mp_surface,
        "model_file_scan": models,
        "route_evaluation": route_eval,
        "whole_body_geometry_authority": {
            "result": "blocked" if missing else "needs_runtime_validation",
            "whole_body_geometry_authority_pass": False,
            "pose_hand_dense_landmark_or_segmentation_pass": False,
            "semantic_human_part_parsing_pass": False,
            "contact_occlusion_ownership_pass": False,
            "body_region_geometry_pass": False,
            "body_reference_matrix_pass": False,
            "source_image": rel(SOURCE_IMAGE) if source_exists else str(SOURCE_IMAGE),
            "source_sha256": source_sha,
            "ref_image_1_path": rel(REF_IMAGE_1) if ref_exists else str(REF_IMAGE_1),
            "ref_image_1_sha256": ref_sha,
            "source_dimensions": [768, 768] if source_exists else [0, 0],
            "mask_type_id": "whole_body_geometry_authority",
            "matrix_slot_id": "TRK-W70-0162",
            "person_instance_id": "",
            "subject_side_mapping": {},
            "models_attempted": [],
            "models_available": [name for name, route in route_eval["routes"].items() if route["available"]],
            "models_available_but_runtime_unvalidated": unvalidated,
            "pose_landmark_record_path": "",
            "hand_landmark_record_path": "",
            "human_part_parsing_record_path": "",
            "sam_refinement_record_path": "",
            "contact_occlusion_record_path": "",
            "visibility_occlusion_record_path": "",
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
                "visibility_confidence": None,
                "overall_confidence": None,
            },
            "blocked_reason": "Blocked_Body_Geometry_Dependency_Missing" if missing else "",
            "findings": findings,
        },
        "qa_decision": result,
        "promotion_decision": "no_mask_promoted_no_active_input_changed_no_whole_body_geometry_authority_pass",
        "next_step": (
            "Install/register approved local pose, hand, human parsing, person-instance, SAM/SAM2, temporal propagation, and contact ownership routes before whole-body masks can pass."
            if missing
            else "Run bounded runtime validation for each whole-body route before deriving masks."
        ),
    }
    evidence_paths = [
        QA_DIR / f"{EVIDENCE_ID}.json",
        QA_DIR / "body_geometry_dependency_probe.json",
        TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json",
        TRACKER_EVIDENCE_DIR / "body_geometry_dependency_probe.json",
        RUNTIME_DIR / "body_geometry_dependency_probe.json",
        panel_path,
    ]
    json_evidence_paths = [path for path in evidence_paths if path.suffix.lower() == ".json"]
    for path in json_evidence_paths:
        write_json(path, payload)
    note = (
        f"Whole-body geometry dependency probe {RUN_STAMP}: {result}; missing routes: {', '.join(missing)}; "
        f"available but runtime-unvalidated routes: {', '.join(unvalidated)}. Ref_Image_1 top strip remains partial upper-body only; no masks promoted."
    )
    payload["panel_path"] = rel(panel_path)
    payload["tracker_item_updates"] = update_wave70_rows([rel(path) for path in evidence_paths], note)
    for path in json_evidence_paths:
        write_json(path, payload)
    print(json.dumps({"result": result, "missing_required_routes": missing, "qa_evidence": rel(evidence_paths[0]), "updated_rows": payload["tracker_item_updates"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
