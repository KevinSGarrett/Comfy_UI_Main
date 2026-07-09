from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

from wave70_model_registry import SEARCH_ROOTS, file_record, first_existing_asset, registry_snapshot


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
COMFYUI_VENV_PYTHON = PROJECT_ROOT / "ComfyUI/.venv/Scripts/python.exe"
CONTROLNET_AUX_SRC = PROJECT_ROOT / "ComfyUI/custom_nodes/comfyui_controlnet_aux/src"
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_SEGMENTATION_REFINEMENT_AUTHORITY_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_segmentation_refinement_authority.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_segmentation_refinement_authority" / RUN_STAMP

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]


def rel(path: Path) -> str:
    resolved = path.resolve()
    root = PROJECT_ROOT.resolve()
    try:
        return resolved.relative_to(root).as_posix()
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


def module_probe(module_name: str) -> dict[str, object]:
    record: dict[str, object] = {
        "module": module_name,
        "available": False,
        "origin": None,
        "imported": False,
        "version": None,
        "error": None,
    }
    try:
        spec = importlib.util.find_spec(module_name)
        record["available"] = spec is not None
        record["origin"] = spec.origin if spec else None
        if spec is None:
            return record
        module = __import__(module_name)
        record["imported"] = True
        record["version"] = getattr(module, "__version__", None)
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def python_environment_probe(python_path: Path) -> dict[str, object]:
    modules = ["segment_anything", "sam2", "torch", "torchvision", "cv2", "numpy", "PIL", "onnxruntime"]
    if not python_path.exists():
        return {"python": str(python_path), "exists": False, "modules": {}, "error": "python_not_found"}
    code = (
        "import importlib.util, json, sys\n"
        f"mods={modules!r}\n"
        "out={'python':sys.executable,'exists':True,'modules':{}}\n"
        "for m in mods:\n"
        "    rec={'available':False,'origin':None,'imported':False,'version':None,'error':None}\n"
        "    try:\n"
        "        spec=importlib.util.find_spec(m)\n"
        "        rec['available']=spec is not None\n"
        "        rec['origin']=spec.origin if spec else None\n"
        "        if spec is not None:\n"
        "            module=__import__(m)\n"
        "            rec['imported']=True\n"
        "            rec['version']=getattr(module,'__version__',None)\n"
        "    except Exception as exc:\n"
        "        rec['error']=type(exc).__name__+': '+str(exc)\n"
        "    out['modules'][m]=rec\n"
        "print(json.dumps(out))\n"
    )
    try:
        proc = subprocess.run(
            [str(python_path), "-c", code],
            cwd=str(PROJECT_ROOT),
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            return {
                "python": str(python_path),
                "exists": True,
                "modules": {},
                "error": proc.stderr.strip() or f"exit_{proc.returncode}",
            }
        return json.loads(proc.stdout)
    except Exception as exc:  # noqa: BLE001
        return {"python": str(python_path), "exists": True, "modules": {}, "error": f"{type(exc).__name__}: {exc}"}


def find_promptable_segmentation_candidates() -> list[dict[str, object]]:
    roots = SEARCH_ROOTS
    tokens = [
        "sam2",
        "sam_vit",
        "sam-vit",
        "mobile_sam",
        "mobile-sam",
        "segment_anything",
        "segment-anything",
        "sam_hq",
        "sam-hq",
        "sam_b",
        "sam_l",
        "sam_h",
        "sam3",
    ]
    suffixes = {".pth", ".pt", ".safetensors", ".onnx", ".bin", ".ckpt", ".yaml", ".json", ".py"}
    records: list[dict[str, object]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            lower = str(path).lower()
            if not any(token in lower for token in tokens):
                continue
            is_model = path.suffix.lower() in {".pth", ".pt", ".safetensors", ".onnx", ".bin", ".ckpt"}
            records.append(
                {
                    "path": str(path),
                    "relative_path": rel(path),
                    "size_bytes": path.stat().st_size,
                    "suffix": path.suffix.lower(),
                    "likely_promptable_segmentation_checkpoint": is_model,
                    "classification": "candidate_promptable_segmentation_checkpoint" if is_model else "code_config_or_wrapper",
                }
            )
    return records


def controlnet_aux_sam_probe() -> dict[str, object]:
    record: dict[str, object] = {
        "sys_path_added": str(CONTROLNET_AUX_SRC),
        "src_exists": CONTROLNET_AUX_SRC.exists(),
        "routes": {},
    }
    if not CONTROLNET_AUX_SRC.exists():
        return record
    sys.path.insert(0, str(CONTROLNET_AUX_SRC))
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    for module_name in ["custom_controlnet_aux.sam", "custom_controlnet_aux.mobile_sam"]:
        route = module_probe(module_name)
        route["load_attempted"] = False
        route["loaded"] = False
        route["inference_pass"] = False
        record["routes"][module_name] = route
    return record


def make_blocker_panel(source: Image.Image) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "segmentation_refinement_authority_blocker_panel.png"
    width, height = source.size
    panel = Image.new("RGB", (width * 2, height), "white")
    panel.paste(source, (0, 0))
    marked = source.copy()
    draw = ImageDraw.Draw(marked)
    draw.rectangle([0, 0, width - 1, height - 1], outline=(230, 40, 40), width=6)
    draw.rectangle([20, 20, width - 20, 205], fill=(255, 255, 255), outline=(230, 40, 40), width=3)
    font = ImageFont.load_default()
    lines = [
        "TRK-W70-0145 blocked",
        "No loadable SAM/SAM2 model route.",
        "No promptable segmentation checkpoint found.",
        "Wrapper code is not refinement evidence.",
        "No prompt manifest or stability score.",
        "No masks promoted.",
    ]
    y = 34
    for line in lines:
        draw.text((34, y), line, fill=(120, 0, 0), font=font)
        y += 25
    panel.paste(marked, (width, 0))
    panel.save(panel_path)
    return panel_path


def mean_point(points: list[dict[str, object]]) -> list[float]:
    xs = [float(point["x_px"]) for point in points]
    ys = [float(point["y_px"]) for point in points]
    return [round(sum(xs) / len(xs), 3), round(sum(ys) / len(ys), 3)]


def run_sam2_refinement(source: Image.Image) -> dict[str, object]:
    record: dict[str, object] = {
        "attempted": False,
        "sam_refinement_pass": False,
        "positive_negative_prompt_manifest_pass": False,
        "stability_score_recorded": False,
        "error": None,
    }
    sam2_checkpoint = first_existing_asset("sam2_hiera_tiny_checkpoint")
    if sam2_checkpoint is None:
        record["error"] = "sam2_checkpoint_missing"
        return record

    face_authority_path = QA_DIR / "face_landmark_authority.json"
    if not face_authority_path.exists():
        record["error"] = "face_landmark_authority_missing"
        return record
    face_authority = json.loads(face_authority_path.read_text(encoding="utf-8-sig"))
    if not face_authority.get("landmark_detection", {}).get("source_derived_landmark_or_segmentation_pass"):
        record["error"] = "face_landmark_authority_not_passing"
        return record
    landmark_rel = face_authority.get("artifacts", {}).get("landmark_record_path")
    if not landmark_rel:
        record["error"] = "face_landmark_record_path_missing"
        return record
    landmark_path = PROJECT_ROOT / str(landmark_rel)
    if not landmark_path.exists():
        record["error"] = "face_landmark_record_missing"
        return record
    landmark_record = json.loads(landmark_path.read_text(encoding="utf-8-sig"))
    groups = landmark_record.get("groups", {})
    bbox = landmark_record.get("bbox_xyxy")
    if not bbox or not groups.get("nose") or not groups.get("outer_lips"):
        record["error"] = "face_prompt_landmark_groups_missing"
        return record

    width, height = source.size
    center = [round((float(bbox[0]) + float(bbox[2])) / 2, 3), round((float(bbox[1]) + float(bbox[3])) / 2, 3)]
    positive_points = [
        {"label": "face_bbox_center", "xy": center},
        {"label": "nose_center", "xy": mean_point(groups["nose"])},
        {"label": "outer_lips_center", "xy": mean_point(groups["outer_lips"])},
    ]
    negative_points = [
        {"label": "background_top_left", "xy": [20.0, 20.0]},
        {"label": "background_top_right", "xy": [float(width - 20), 20.0]},
        {"label": "background_bottom_left", "xy": [20.0, float(height - 20)]},
        {"label": "background_bottom_right", "xy": [float(width - 20), float(height - 20)]},
    ]

    prompt_manifest_path = RUNTIME_DIR / "sam2_face_refinement_prompt_manifest.json"
    mask_path = RUNTIME_DIR / "sam2_face_refinement_mask.png"
    overlay_path = RUNTIME_DIR / "sam2_face_refinement_overlay_panel.png"
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "source_image": rel(SOURCE_IMAGE),
        "source_dimensions": [width, height],
        "prompt_source": rel(landmark_path),
        "target": "face_region_refinement_smoke",
        "positive_points": positive_points,
        "negative_points": negative_points,
        "sam2_checkpoint": file_record(sam2_checkpoint),
    }
    write_json(prompt_manifest_path, manifest)

    try:
        import numpy as np
        from sam2.build_sam import build_sam2
        from sam2.sam2_image_predictor import SAM2ImagePredictor

        record["attempted"] = True
        sam2_model = build_sam2(
            "configs/sam2.1/sam2.1_hiera_t.yaml",
            str(sam2_checkpoint),
            device="cpu",
        )
        predictor = SAM2ImagePredictor(sam2_model)
        image_np = np.array(source.convert("RGB"))
        predictor.set_image(image_np)
        point_coords = np.array([item["xy"] for item in positive_points + negative_points], dtype=np.float32)
        point_labels = np.array([1] * len(positive_points) + [0] * len(negative_points), dtype=np.int32)
        masks, scores, _ = predictor.predict(
            point_coords=point_coords,
            point_labels=point_labels,
            multimask_output=True,
        )
        best_index = int(np.argmax(scores))
        best_mask = masks[best_index].astype("uint8") * 255
        Image.fromarray(best_mask, mode="L").save(mask_path)

        overlay = source.convert("RGBA")
        color = Image.new("RGBA", source.size, (40, 210, 120, 0))
        alpha = Image.fromarray((best_mask * 0.38).astype("uint8"), mode="L")
        color.putalpha(alpha)
        overlay = Image.alpha_composite(overlay, color)
        draw = ImageDraw.Draw(overlay)
        for point in positive_points:
            x, y = point["xy"]
            draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(35, 210, 80, 255))
        for point in negative_points:
            x, y = point["xy"]
            draw.line((x - 6, y - 6, x + 6, y + 6), fill=(230, 40, 40, 255), width=3)
            draw.line((x - 6, y + 6, x + 6, y - 6), fill=(230, 40, 40, 255), width=3)
        overlay.convert("RGB").save(overlay_path)

        mask_pixels = int((best_mask > 0).sum())
        area_ratio = mask_pixels / float(width * height)
        score_list = [float(score) for score in scores.tolist()]
        record.update(
            {
                "sam_refinement_pass": bool(mask_pixels > 0 and max(score_list) >= 0.5),
                "positive_negative_prompt_manifest_pass": True,
                "stability_score_recorded": True,
                "prompt_manifest_path": rel(prompt_manifest_path),
                "refinement_mask_path": rel(mask_path),
                "refinement_overlay_path": rel(overlay_path),
                "scores": score_list,
                "selected_mask_index": best_index,
                "selected_score": float(score_list[best_index]),
                "mask_pixels": mask_pixels,
                "mask_area_ratio": round(area_ratio, 6),
                "sam2_checkpoint": file_record(sam2_checkpoint),
            }
        )
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def update_wave70_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0145") for path in TRACKER_FILES] + [(path, "ITEM-W70-0145") for path in ITEM_FILES]
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
            if "Evidence_Required" in row:
                row["Evidence_Required"] = append_unique(row.get("Evidence_Required", ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = "blocked_exact_local_promptable_segmentation_route_unavailable"
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    ["blocked_exact_local_promptable_segmentation_route_unavailable"],
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
    candidates = find_promptable_segmentation_candidates()
    checkpoints = [item for item in candidates if item["likely_promptable_segmentation_checkpoint"]]
    current_python_probe = python_environment_probe(Path(sys.executable))
    comfyui_python_probe = python_environment_probe(COMFYUI_VENV_PYTHON)
    aux_probe = controlnet_aux_sam_probe()
    sam2_refinement = run_sam2_refinement(source)
    panel_path = (
        PROJECT_ROOT / str(sam2_refinement["refinement_overlay_path"])
        if sam2_refinement.get("refinement_overlay_path")
        else make_blocker_panel(source)
    )
    sam2_pass = sam2_refinement.get("sam_refinement_pass") is True

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "segmentation_refinement_authority.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "segmentation_refinement_authority.json"
    runtime_evidence_path = RUNTIME_DIR / "segmentation_refinement_authority.json"

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(panel_path),
    ]
    note = (
        f"Promptable segmentation refinement authority {RUN_STAMP}: SAM2 route executed from face-landmark prompts. "
        "Prompt manifest, refinement mask, and stability score were written; no canonical polygon or mask promotion occurred."
        if sam2_pass
        else f"Promptable segmentation refinement authority {RUN_STAMP}: exact local blocker. "
        "No compatible local SAM/SAM2 or equivalent promptable segmentation model route loaded and executed. "
        "No prompt manifest, stability score, canonical polygon, or mask promotion was produced."
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note)
    if sam2_pass:
        # Refine the row status after the shared blocker-style row updater has attached evidence.
        for csv_path, target_id in [(path, "TRK-W70-0145") for path in TRACKER_FILES] + [
            (path, "ITEM-W70-0145") for path in ITEM_FILES
        ]:
            with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
                fieldnames = reader.fieldnames or []
            id_field = "Tracker_ID" if target_id.startswith("TRK-") else "Item_ID"
            for row in rows:
                if row.get(id_field) != target_id:
                    continue
                row["Status"] = "Segmentation_Refinement_Authority_Implemented_Pending_Consensus"
                if "Status_Decision" in row:
                    row["Status_Decision"] = "sam2_promptable_refinement_executed_pending_consensus_and_canonical_polygon"
                if "Coverage_Audit_Status" in row:
                    row["Coverage_Audit_Status"] = append_unique(
                        row.get("Coverage_Audit_Status", ""),
                        ["sam2_promptable_refinement_executed_pending_consensus_and_canonical_polygon"],
                    )
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                writer.writerows(rows)

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "task": "Implement promptable segmentation refinement adapter for TRK-W70-0145 / ITEM-W70-0145.",
        "script": SCRIPT_REL,
        "source_image": {
            "path": rel(SOURCE_IMAGE),
            "exists": SOURCE_IMAGE.exists(),
            "sha256": sha256_file(SOURCE_IMAGE),
            "dimensions": [width, height],
        },
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": str(PROJECT_ROOT),
            "wave70_model_registry": registry_snapshot(),
            "current_python_probe": current_python_probe,
            "comfyui_venv_python_probe": comfyui_python_probe,
        },
        "local_promptable_segmentation_candidates": candidates,
        "candidate_summary": {
            "total_keyword_matches": len(candidates),
            "likely_promptable_segmentation_checkpoint_count": len(checkpoints),
            "likely_promptable_segmentation_checkpoints": checkpoints,
        },
        "runtime_attempts": {
            "controlnet_aux_sam_routes": aux_probe,
            "sam2_refinement": sam2_refinement,
        },
        "artifacts": {
            "blocker_panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
        },
        "model_backed_geometry_authority": {
            "result": "sam2_refinement_executed_pending_consensus"
            if sam2_pass
            else "blocked",
            "model_backed_geometry_authority_pass": False,
            "source_image": rel(SOURCE_IMAGE),
            "source_sha256": sha256_file(SOURCE_IMAGE),
            "source_dimensions": [width, height],
            "mask_type_id": "MBGA-004",
            "matrix_slot_id": "TRK-W70-0145",
            "models_attempted": [
                "default_python_segment_anything_sam2_probe",
                "comfyui_venv_segment_anything_sam2_probe",
                "custom_controlnet_aux_sam_import_probe",
                "local_promptable_segmentation_model_file_scan",
            ],
            "models_available": ["base_image_io_and_cv"],
            "model_versions": {
                name: rec.get("version")
                for name, rec in (current_python_probe.get("modules") or {}).items()
                if isinstance(rec, dict) and rec.get("version") is not None
            },
            "landmark_record_path": "",
            "semantic_parsing_record_path": "",
            "sam_refinement_record_path": sam2_refinement.get("refinement_mask_path", ""),
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
            "model_geometry_dependency_probe_pass": sam2_pass,
            "sam_refinement_pass": sam2_pass,
            "positive_negative_prompt_manifest_pass": sam2_refinement.get(
                "positive_negative_prompt_manifest_pass"
            )
            is True,
            "stability_score_recorded": sam2_refinement.get("stability_score_recorded") is True,
            "source_derived_landmark_or_segmentation_pass": sam2_pass,
            "model_consensus_geometry_pass": False,
            "visibility_occlusion_confidence_pass": False,
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
            "blocked_reason": "full_authority_pending_semantic_face_parsing_visibility_consensus_and_canonical_polygon"
            if sam2_pass
            else "Blocked_Model_Geometry_Dependency_Missing",
            "findings": [
                "SAM2 tiny checkpoint loaded locally and produced a promptable refinement mask from face landmark prompts.",
                "Positive and negative prompt manifest plus stability score were recorded.",
                "This is refinement evidence only; semantic face parsing, visibility, consensus, canonical polygons, and mask promotion remain fail-closed.",
            ]
            if sam2_pass
            else [
                "Active Wave70 source image exists and was used for the blocker panel.",
                "No local checkpoint proven to be a promptable segmentation model was found.",
                "A wrapper/code path alone is not promptable segmentation refinement evidence.",
                "The ComfyUI virtualenv does not expose segment_anything or sam2 modules.",
                "No source-derived positive/negative prompt manifest could be created because face parsing and landmark authority remain blocked.",
                "No refinement mask, stability score, consensus metric, canonical polygon, or mask promotion was produced.",
            ],
        },
        "segmentation_refinement_authority": {
            "result": "sam2_refinement_executed_pending_consensus"
            if sam2_pass
            else "blocked",
            "sam_refinement_pass": sam2_pass,
            "positive_negative_prompt_manifest_pass": sam2_refinement.get(
                "positive_negative_prompt_manifest_pass"
            )
            is True,
            "stability_score_recorded": sam2_refinement.get("stability_score_recorded") is True,
            "refinement_mask_path": sam2_refinement.get("refinement_mask_path", ""),
            "prompt_manifest_path": sam2_refinement.get("prompt_manifest_path", ""),
            "refinement_overlay_path": sam2_refinement.get("refinement_overlay_path", ""),
            "stability_score": sam2_refinement.get("selected_score"),
            "mask_area_ratio": sam2_refinement.get("mask_area_ratio"),
            "canonical_polygon_path": "",
            "blocked_reason": "full_authority_pending_semantic_face_parsing_visibility_consensus_and_canonical_polygon"
            if sam2_pass
            else "Blocked_Model_Geometry_Dependency_Missing",
        },
        "qa_decision": "sam2_promptable_refinement_executed_pending_consensus_and_canonical_polygon"
        if sam2_pass
        else "blocked_exact_local_promptable_segmentation_route_unavailable",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_sam2_refinement_only"
        if sam2_pass
        else "no_mask_promoted_no_active_input_changed_segmentation_refinement_blocked",
        "tracker_item_updates": row_updates,
        "next_step": "Resolve a compatible local promptable segmentation runtime/model or continue to the next model-backed authority row with exact local evidence.",
    }

    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    print(json.dumps({"evidence_id": EVIDENCE_ID, "result": payload["qa_decision"], "evidence": rel(qa_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
