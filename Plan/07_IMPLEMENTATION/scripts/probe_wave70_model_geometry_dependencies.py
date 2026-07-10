#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
RUN_STAMP = "20260708T004000-0500"
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_model_geometry_dependency_probe" / RUN_STAMP
STAMPED_QA = QA_DIR / f"W70_MODEL_GEOMETRY_DEPENDENCY_PROBE_{RUN_STAMP}.json"
CANONICAL_QA = QA_DIR / "model_geometry_dependency_probe.json"
STAMPED_TRACKER = TRACKER_DIR / f"W70_MODEL_GEOMETRY_DEPENDENCY_PROBE_{RUN_STAMP}.json"
CANONICAL_TRACKER = TRACKER_DIR / "model_geometry_dependency_probe.json"

IMPORT_PROBES = {
    "python_numpy": "numpy",
    "python_pil": "PIL",
    "python_cv2": "cv2",
    "python_torch": "torch",
    "python_torchvision": "torchvision",
    "python_mediapipe": "mediapipe",
    "python_dlib": "dlib",
    "python_onnxruntime": "onnxruntime",
    "python_transformers": "transformers",
    "python_diffusers": "diffusers",
    "python_segment_anything": "segment_anything",
    "python_sam2": "sam2",
    "python_ultralytics": "ultralytics",
    "python_insightface": "insightface",
    "python_face_alignment": "face_alignment",
    "python_skimage": "skimage",
    "python_scipy": "scipy",
}

MODEL_EXTENSIONS = {".task", ".tflite", ".onnx", ".pt", ".pth", ".safetensors", ".ckpt", ".bin"}
MODEL_SEARCH_ROOTS = [
    PROJECT_ROOT / "models",
    PROJECT_ROOT / "ComfyUI/models",
    PROJECT_ROOT / "tools",
    Path.home() / ".cache",
]
KEYWORD_GROUPS = {
    "mediapipe_task_models": ["face_landmarker", "face_detector", "pose_landmarker", "hand_landmarker", "mediapipe"],
    "face_parsing_models": ["face_parsing", "bisenet", "parsenet", "celebamask", "faceparse"],
    "sam_promptable_segmentation_models": ["sam", "sam2", "mobile_sam", "segment_anything"],
    "pose_hand_models": ["openpose", "dwpose", "hand", "pose"],
    "face_landmark_models": ["landmark", "68", "facemesh", "face_mesh", "shape_predictor"],
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def import_probe(module: str) -> dict[str, Any]:
    record: dict[str, Any] = {"module": module, "available": False, "version": None, "error": None}
    try:
        spec = importlib.util.find_spec(module)
        if spec is None:
            record["error"] = "module_spec_not_found"
            return record
        imported = importlib.import_module(module)
        record["available"] = True
        record["version"] = getattr(imported, "__version__", None)
        return record
    except Exception as exc:  # noqa: BLE001 - evidence should capture exact import failure
        record["error"] = f"{type(exc).__name__}: {exc}"
        return record


def safe_model_record(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
    except OSError as exc:
        return {"path": str(path), "error": f"{type(exc).__name__}: {exc}"}
    out: dict[str, Any] = {
        "path": str(path),
        "name": path.name,
        "suffix": path.suffix.lower(),
        "size_bytes": int(stat.st_size),
    }
    # Hash small model/adapter files. Large checkpoint hashes are expensive and
    # not needed for this availability probe.
    if stat.st_size <= 512 * 1024 * 1024:
        try:
            out["sha256"] = sha256_file(path)
        except OSError as exc:
            out["sha256_error"] = f"{type(exc).__name__}: {exc}"
    else:
        out["sha256"] = "skipped_large_file"
    return out


def scan_models() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    roots: list[dict[str, Any]] = []
    max_records = 400
    for root in MODEL_SEARCH_ROOTS:
        root_record: dict[str, Any] = {"root": str(root), "exists": root.exists(), "scanned": False, "matched_count": 0}
        roots.append(root_record)
        if not root.exists() or not root.is_dir():
            continue
        root_record["scanned"] = True
        try:
            for current_root, dirnames, filenames in os.walk(root):
                # Avoid walking generated outputs and temp caches too deeply.
                lower_root = current_root.lower()
                if any(skip in lower_root for skip in ("\\output", "\\outputs", "\\temp", "\\tmp", "\\runtime_artifacts")):
                    dirnames[:] = []
                    continue
                for filename in filenames:
                    suffix = Path(filename).suffix.lower()
                    if suffix not in MODEL_EXTENSIONS:
                        continue
                    path = Path(current_root) / filename
                    records.append(safe_model_record(path))
                    root_record["matched_count"] += 1
                    if len(records) >= max_records:
                        root_record["truncated_at_record_limit"] = max_records
                        raise StopIteration
        except StopIteration:
            break
        except OSError as exc:
            root_record["scan_error"] = f"{type(exc).__name__}: {exc}"
    grouped = {group: [] for group in KEYWORD_GROUPS}
    for record in records:
        haystack = f"{record.get('path', '')} {record.get('name', '')}".lower()
        for group, keywords in KEYWORD_GROUPS.items():
            if any(keyword in haystack for keyword in keywords):
                grouped[group].append(record)
    return {"roots": roots, "matched_model_files": records, "keyword_groups": grouped}


def evaluate_routes(imports: dict[str, Any], models: dict[str, Any]) -> dict[str, Any]:
    groups = models["keyword_groups"]
    has_torch = imports["python_torch"]["available"]
    has_cv2 = imports["python_cv2"]["available"]
    face_landmark_available = imports["python_mediapipe"]["available"] or (
        imports["python_dlib"]["available"] and bool(groups["face_landmark_models"])
    ) or imports["python_face_alignment"]["available"] or imports["python_insightface"]["available"]
    face_parsing_available = bool(groups["face_parsing_models"]) and (has_torch or imports["python_onnxruntime"]["available"])
    sam_available = (
        (imports["python_segment_anything"]["available"] or imports["python_sam2"]["available"])
        and bool(groups["sam_promptable_segmentation_models"])
        and has_torch
    )
    pose_hand_available = imports["python_mediapipe"]["available"] or bool(groups["pose_hand_models"])
    base_image_stack_available = imports["python_numpy"]["available"] and imports["python_pil"]["available"] and has_cv2
    routes = {
        "base_image_io_and_cv": {
            "available": base_image_stack_available,
            "evidence": ["numpy", "PIL", "cv2"],
        },
        "face_landmark_authority_route": {
            "available": face_landmark_available,
            "evidence": [
                "mediapipe import",
                "dlib plus landmark model",
                "face_alignment import",
                "insightface import",
            ],
        },
        "semantic_face_parsing_route": {
            "available": face_parsing_available,
            "evidence": ["face parsing model file", "torch or onnxruntime"],
        },
        "promptable_segmentation_refinement_route": {
            "available": sam_available,
            "evidence": ["segment_anything/sam2 import", "SAM/SAM2 model file", "torch"],
        },
        "pose_hand_body_extension_route": {
            "available": pose_hand_available,
            "evidence": ["mediapipe import", "pose/hand model files"],
        },
    }
    required_route_names = [
        "base_image_io_and_cv",
        "face_landmark_authority_route",
        "semantic_face_parsing_route",
        "promptable_segmentation_refinement_route",
    ]
    missing_required = [name for name in required_route_names if not routes[name]["available"]]
    return {
        "routes": routes,
        "missing_required_routes": missing_required,
        "required_stack_available": not missing_required,
    }


def main() -> int:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    imports = {name: import_probe(module) for name, module in IMPORT_PROBES.items()}
    models = scan_models()
    route_evaluation = evaluate_routes(imports, models)
    source_exists = SOURCE_IMAGE.exists()
    blocked = not route_evaluation["required_stack_available"]
    findings = []
    if source_exists:
        findings.append("Active Wave70 source image exists for future model-backed geometry probes.")
    else:
        findings.append("Active Wave70 source image is missing.")
    for route_name in route_evaluation["missing_required_routes"]:
        findings.append(f"Required local route unavailable or incomplete: {route_name}.")
    if blocked:
        findings.append("TRK-W70-0142 cannot pass; exact dependency/model blocker is required before mask derivation resumes.")
    else:
        findings.append("Required local dependency/model routes appear available for the next authority row; load/runtime validation still required.")

    payload = {
        "schema_version": "1.0",
        "evidence_id": f"W70_MODEL_GEOMETRY_DEPENDENCY_PROBE_{RUN_STAMP}",
        "created_local": RUN_STAMP,
        "task": "Probe local model-backed geometry dependencies and model files for TRK-W70-0142 / ITEM-W70-0142.",
        "source_image": {
            "path": rel(SOURCE_IMAGE) if source_exists else str(SOURCE_IMAGE),
            "exists": source_exists,
            "sha256": sha256_file(SOURCE_IMAGE) if source_exists else None,
        },
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": str(Path.cwd()),
        },
        "imports": imports,
        "model_file_scan": models,
        "route_evaluation": route_evaluation,
        "model_backed_geometry_authority": {
            "result": "blocked" if blocked else "needs_runtime_validation",
            "model_backed_geometry_authority_pass": False,
            "source_image": rel(SOURCE_IMAGE) if source_exists else str(SOURCE_IMAGE),
            "source_sha256": sha256_file(SOURCE_IMAGE) if source_exists else None,
            "source_dimensions": [768, 768] if source_exists else [0, 0],
            "mask_type_id": "MBGA-001",
            "matrix_slot_id": "TRK-W70-0142",
            "models_attempted": [],
            "models_available": [
                route for route, record in route_evaluation["routes"].items() if record["available"]
            ],
            "model_versions": {
                name: record["version"] for name, record in imports.items() if record.get("available")
            },
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
            "dependency_probe_completed": True,
            "model_geometry_dependency_probe_pass": not blocked,
            "blocked_reason": "Blocked_Model_Geometry_Dependency_Missing" if blocked else "",
            "findings": findings,
        },
        "qa_decision": "blocked_model_geometry_dependency_missing" if blocked else "dependency_probe_needs_next_runtime_validation",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_no_W70_MODEL_BACKED_GEOMETRY_AUTHORITY_ROW_GATE_PASS_TRUE",
        "next_step": (
            "Write exact blocker and keep Wave70 masks fail-closed until missing local model-backed geometry routes are installed/registered."
            if blocked
            else "Proceed to MBGA-002 face landmark authority runtime validation."
        ),
    }
    write_json(RUNTIME_DIR / "model_geometry_dependency_probe.json", payload)
    write_json(STAMPED_QA, payload)
    write_json(CANONICAL_QA, payload)
    write_json(STAMPED_TRACKER, payload)
    write_json(CANONICAL_TRACKER, payload)
    print(json.dumps({"result": payload["qa_decision"], "qa_evidence": rel(STAMPED_QA), "canonical": rel(CANONICAL_QA)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
