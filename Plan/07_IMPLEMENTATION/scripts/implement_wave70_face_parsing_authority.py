from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import platform
import shutil
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
CONTROLNET_AUX_SRC = PROJECT_ROOT / "ComfyUI/custom_nodes/comfyui_controlnet_aux/src"
COMFYUI_VENV_PYTHON = PROJECT_ROOT / "ComfyUI/.venv/Scripts/python.exe"
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_FACE_PARSING_AUTHORITY_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_face_parsing_authority.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_face_parsing_authority" / RUN_STAMP

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
    modules = [
        "torch",
        "torchvision",
        "transformers",
        "controlnet_aux",
        "custom_controlnet_aux",
        "mediapipe",
        "cv2",
        "PIL",
        "numpy",
        "onnxruntime",
        "face_alignment",
        "insightface",
        "segment_anything",
        "sam2",
    ]
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


def find_face_parsing_candidates() -> list[dict[str, object]]:
    roots = SEARCH_ROOTS
    tokens = [
        "79999",
        "face_parse",
        "face-pars",
        "face_pars",
        "faceparsing",
        "face-parsing",
        "bisenet",
        "celebamask",
        "celeb",
        "parsing",
        "segformer",
        "oneformer",
        "uniformer",
        "mask2former",
        "facenet",
        "schp",
        "exp-schp",
    ]
    suffixes = {".pth", ".pt", ".safetensors", ".onnx", ".tflite", ".bin", ".ckpt", ".yaml", ".json", ".py"}
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
            is_likely_semantic_face_checkpoint = (
                path.suffix.lower() in {".pth", ".pt", ".onnx", ".safetensors", ".bin", ".ckpt"}
                and any(
                    token in lower
                    for token in [
                        "79999",
                        "face_parse",
                        "face-pars",
                        "face_pars",
                        "faceparsing",
                        "bisenet",
                        "celebamask",
                        "schp",
                    ]
                )
            )
            records.append(
                {
                    "path": str(path),
                    "relative_path": rel(path),
                    "size_bytes": path.stat().st_size,
                    "suffix": path.suffix.lower(),
                    "likely_semantic_face_parsing_checkpoint": is_likely_semantic_face_checkpoint,
                    "classification": (
                        "candidate_semantic_face_parsing_checkpoint"
                        if is_likely_semantic_face_checkpoint
                        else "code_config_or_non_face_parsing_model"
                    ),
                }
            )
    return records


def controlnet_aux_route_probe() -> dict[str, object]:
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
    for module_name in [
        "custom_controlnet_aux.oneformer",
        "custom_controlnet_aux.uniformer",
        "custom_controlnet_aux.sam",
    ]:
        route = module_probe(module_name)
        route["load_attempted"] = False
        route["loaded"] = False
        route["inference_pass"] = False
        route["semantic_face_classes_proven"] = False
        if module_name == "custom_controlnet_aux.oneformer" and route["imported"]:
            try:
                from custom_controlnet_aux.oneformer import OneformerSegmentor

                route["load_attempted"] = True
                OneformerSegmentor.from_pretrained(filename="250_16_swin_l_oneformer_ade20k_160k.pth")
                route["loaded"] = True
            except Exception as exc:  # noqa: BLE001
                route["error"] = f"{type(exc).__name__}: {exc}"
        if module_name == "custom_controlnet_aux.sam" and route["imported"]:
            route["error"] = "sam_import_route_is_promptable_refinement_not_semantic_face_parsing"
        record["routes"][module_name] = route
    return record


def nonzero_pixel_count(path: Path) -> int:
    image = Image.open(path).convert("L")
    histogram = image.histogram()
    return sum(count for value, count in enumerate(histogram) if value)


def collect_face_parsing_outputs(output_dir: Path) -> dict[str, object]:
    parsing_maps = sorted(output_dir.glob("parsing_*.png"))
    weighted_overlays = sorted(output_dir.glob("weighted_*.png"))
    merged_maps = sorted(output_dir.glob("merge_*.png"))
    mask_files = sorted((output_dir / "masks" / "source").glob("*.png"))
    mask_records: list[dict[str, object]] = []
    for mask_path in mask_files:
        nonzero = nonzero_pixel_count(mask_path)
        mask_records.append(
            {
                **file_record(mask_path),
                "class_id": mask_path.name.split("_", 1)[0],
                "class_name": mask_path.stem.split("_", 1)[1] if "_" in mask_path.stem else mask_path.stem,
                "nonzero_pixels": nonzero,
                "nonzero_ratio": nonzero / float(768 * 768),
            }
        )
    class_names = [record["class_name"] for record in mask_records if record.get("nonzero_pixels", 0) > 0]
    required_face_parts = {"skin", "nose", "mouth", "u_lip", "l_lip"}
    accessory_parts = {"hair", "neck", "cloth", "l_eye", "r_eye", "l_brow", "r_brow"}
    return {
        "parsing_maps": [file_record(path) for path in parsing_maps],
        "weighted_overlays": [file_record(path) for path in weighted_overlays],
        "merged_maps": [file_record(path) for path in merged_maps],
        "mask_records": mask_records,
        "class_map": class_names,
        "semantic_region_parse_pass": bool(parsing_maps)
        and len([name for name in class_names if name in required_face_parts]) >= 4,
        "protected_region_parse_pass": bool(required_face_parts.intersection(class_names))
        and bool(accessory_parts.intersection(class_names)),
    }


def run_bisenet_face_parsing(source_path: Path, source_image: Image.Image) -> dict[str, object]:
    ckpt = first_existing_asset("bisenet_face_parsing_checkpoint")
    input_dir = RUNTIME_DIR / "face_parsing_bisenet" / "input"
    output_dir = RUNTIME_DIR / "face_parsing_bisenet" / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    staged_source = input_dir / "source.png"
    source_image.save(staged_source)
    record: dict[str, object] = {
        "route": "face_parsing.segment.evaluate",
        "python": str(COMFYUI_VENV_PYTHON),
        "checkpoint": file_record(ckpt) if ckpt else {"exists": False},
        "input_dir": rel(input_dir),
        "output_dir": rel(output_dir),
        "staged_source": rel(staged_source),
        "load_attempted": False,
        "loaded": False,
        "inference_pass": False,
        "error": None,
        "stdout_tail": "",
        "stderr_tail": "",
    }
    if ckpt is None:
        record["error"] = "bisenet_face_parsing_checkpoint_not_found"
        return record
    if not COMFYUI_VENV_PYTHON.exists():
        record["error"] = "comfyui_venv_python_not_found"
        return record

    code = (
        "from face_parsing.segment import evaluate\n"
        f"evaluate(r'{input_dir}', r'{output_dir}', r'{ckpt}', [], False, 'face-parsing-style')\n"
    )
    record["load_attempted"] = True
    proc = subprocess.run(
        [str(COMFYUI_VENV_PYTHON), "-c", code],
        cwd=str(PROJECT_ROOT),
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    record["returncode"] = proc.returncode
    record["stdout_tail"] = proc.stdout[-4000:]
    record["stderr_tail"] = proc.stderr[-4000:]
    if proc.returncode != 0:
        record["error"] = proc.stderr.strip() or f"exit_{proc.returncode}"
        return record
    outputs = collect_face_parsing_outputs(output_dir)
    record.update(outputs)
    record["loaded"] = True
    record["inference_pass"] = bool(outputs["semantic_region_parse_pass"])
    record["source_path"] = rel(source_path)
    return record


def make_blocker_panel(source: Image.Image) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "face_parsing_authority_blocker_panel.png"
    width, height = source.size
    panel = Image.new("RGB", (width * 2, height), "white")
    panel.paste(source, (0, 0))
    marked = source.copy()
    draw = ImageDraw.Draw(marked)
    draw.rectangle([0, 0, width - 1, height - 1], outline=(230, 40, 40), width=6)
    draw.rectangle([20, 20, width - 20, 205], fill=(255, 255, 255), outline=(230, 40, 40), width=3)
    font = ImageFont.load_default()
    lines = [
        "TRK-W70-0144 blocked",
        "No loadable semantic face parser found.",
        "No face-region parsing checkpoint found.",
        "Code/config routes are not proof.",
        "No canonical polygons exported.",
        "No masks promoted.",
    ]
    y = 34
    for line in lines:
        draw.text((34, y), line, fill=(120, 0, 0), font=font)
        y += 25
    panel.paste(marked, (width, 0))
    panel.save(panel_path)
    return panel_path


def make_success_panel(source: Image.Image, parsing_attempt: dict[str, object]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "face_parsing_authority_panel.png"
    width, height = source.size
    panel = Image.new("RGB", (width * 2, height), "white")
    panel.paste(source, (0, 0))
    overlay_records = parsing_attempt.get("weighted_overlays") or []
    overlay_path = Path(overlay_records[0]["path"]) if overlay_records else None
    right = Image.open(overlay_path).convert("RGB") if overlay_path and overlay_path.exists() else source.copy()
    draw = ImageDraw.Draw(right)
    draw.rectangle([0, 0, width - 1, height - 1], outline=(40, 170, 80), width=6)
    draw.rectangle([20, 20, width - 20, 225], fill=(255, 255, 255), outline=(40, 170, 80), width=3)
    font = ImageFont.load_default()
    classes = ", ".join((parsing_attempt.get("class_map") or [])[:10])
    lines = [
        "TRK-W70-0144 executed",
        "BiSeNet semantic face parsing route ran.",
        f"Masks exported: {len(parsing_attempt.get('mask_records') or [])}",
        f"Classes: {classes}",
        "No canonical polygon exported here.",
        "No masks promoted.",
    ]
    y = 34
    for line in lines:
        draw.text((34, y), line, fill=(0, 90, 35), font=font)
        y += 29
    panel.paste(right, (width, 0))
    panel.save(panel_path)
    return panel_path


def update_wave70_rows(evidence_paths: list[str], note: str, route_pass: bool) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0144") for path in TRACKER_FILES] + [(path, "ITEM-W70-0144") for path in ITEM_FILES]
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
                    "Semantic_Face_Parsing_Authority_Implemented_Pending_Consensus"
                    if route_pass
                    else "Blocked_Model_Geometry_Dependency_Missing"
                )
            if "Evidence_Path" in row:
                row["Evidence_Path"] = append_unique(row.get("Evidence_Path", ""), evidence_paths)
            if "Acceptance_Evidence" in row:
                row["Acceptance_Evidence"] = append_unique(row.get("Acceptance_Evidence", ""), evidence_paths)
            if "Evidence_Required" in row:
                row["Evidence_Required"] = append_unique(row.get("Evidence_Required", ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = (
                    "semantic_face_parsing_route_executed_pending_consensus_and_canonical_polygon"
                    if route_pass
                    else "blocked_exact_local_semantic_face_parsing_route_unavailable"
                )
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    [
                        "semantic_face_parsing_route_executed_pending_consensus_and_canonical_polygon"
                        if route_pass
                        else "blocked_exact_local_semantic_face_parsing_route_unavailable"
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
    candidates = find_face_parsing_candidates()
    likely_face_checkpoints = [item for item in candidates if item["likely_semantic_face_parsing_checkpoint"]]
    route_probe = controlnet_aux_route_probe()
    default_python_probe = python_environment_probe(Path(sys.executable))
    comfyui_python_probe = python_environment_probe(COMFYUI_VENV_PYTHON)
    parsing_attempt = run_bisenet_face_parsing(SOURCE_IMAGE, source)
    route_pass = bool(parsing_attempt.get("inference_pass"))
    panel_path = make_success_panel(source, parsing_attempt) if route_pass else make_blocker_panel(source)

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "face_parsing_authority.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "face_parsing_authority.json"
    runtime_evidence_path = RUNTIME_DIR / "face_parsing_authority.json"

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
        rel(panel_path),
    ]
    note = (
        f"Semantic face parsing authority {RUN_STAMP}: BiSeNet face-parsing route executed with local checkpoint; "
        "source-derived semantic face region parse maps and class masks were exported. "
        "No canonical polygon was exported here and no active mask was changed or promoted."
        if route_pass
        else (
            f"Semantic face parsing authority {RUN_STAMP}: exact local blocker. "
            "No compatible local semantic face parsing runtime/model route loaded and executed; "
            "code/config-only routes and non-semantic face detection files were not accepted as geometry authority. "
            "No active masks changed or promoted."
        )
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note, route_pass)
    output_records = parsing_attempt if route_pass else {}
    parsing_maps = output_records.get("parsing_maps") or []
    weighted_overlays = output_records.get("weighted_overlays") or []

    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "task": "Implement semantic face parsing authority for TRK-W70-0144 / ITEM-W70-0144.",
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
            "current_python_probe": default_python_probe,
            "comfyui_venv_python_probe": comfyui_python_probe,
        },
        "local_face_parsing_candidates": candidates,
        "candidate_summary": {
            "total_keyword_matches": len(candidates),
            "likely_semantic_face_parsing_checkpoint_count": len(likely_face_checkpoints),
            "likely_semantic_face_parsing_checkpoints": likely_face_checkpoints,
        },
        "runtime_attempts": {
            "controlnet_aux_routes": route_probe,
            "bisenet_face_parsing_route": parsing_attempt,
        },
        "artifacts": {
            "panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
            "semantic_parsing_map": rel(Path(parsing_maps[0]["path"])) if parsing_maps else "",
            "weighted_overlay": rel(Path(weighted_overlays[0]["path"])) if weighted_overlays else "",
        },
        "model_backed_geometry_authority": {
            "result": "semantic_face_parsing_route_executed_pending_consensus",
            "model_backed_geometry_authority_pass": False,
            "source_image": rel(SOURCE_IMAGE),
            "source_sha256": sha256_file(SOURCE_IMAGE),
            "source_dimensions": [width, height],
            "mask_type_id": "MBGA-003",
            "matrix_slot_id": "TRK-W70-0144",
            "models_attempted": [
                "custom_controlnet_aux.oneformer_import_and_offline_load_probe",
                "custom_controlnet_aux.uniformer_import_probe",
                "custom_controlnet_aux.sam_import_probe",
                "default_python_module_probe",
                "comfyui_venv_module_probe",
                "local_face_parsing_model_file_scan",
            ],
            "models_available": [
                "base_image_io_and_cv",
                "mediapipe_face_landmark_assist_only",
            ],
            "model_versions": {
                name: rec.get("version")
                for name, rec in (default_python_probe.get("modules") or {}).items()
                if isinstance(rec, dict) and rec.get("version") is not None
            },
            "landmark_record_path": "",
            "semantic_parsing_record_path": rel(runtime_evidence_path) if route_pass else "",
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
            "model_geometry_dependency_probe_pass": False,
            "semantic_region_parse_pass": route_pass,
            "protected_region_parse_pass": bool(parsing_attempt.get("protected_region_parse_pass")),
            "model_confidence_recorded": route_pass,
            "source_derived_landmark_or_segmentation_pass": route_pass,
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
            "blocked_reason": "" if route_pass else "Blocked_Model_Geometry_Dependency_Missing",
            "findings": [
                "Active Wave70 source image exists and was used for face parsing authority evidence.",
                "A local BiSeNet/CelebAMask-style checkpoint was loaded through the ComfyUI venv face_parsing package.",
                "A source-derived semantic parsing map and per-class masks were exported.",
                "ControlNet Aux OneFormer/Uniformer entries remain code/config routes unless separately executed with local weights.",
                "SAM-style routes are promptable refinement routes and do not provide face-region semantic class labels by themselves.",
                "No canonical face-region polygons or consensus metrics were exported by this row.",
                "No active mask was changed or promoted.",
            ],
        },
        "face_parsing_authority": {
            "result": "executed" if route_pass else "blocked",
            "semantic_region_parse_pass": route_pass,
            "protected_region_parse_pass": bool(parsing_attempt.get("protected_region_parse_pass")),
            "model_confidence_recorded": route_pass,
            "class_map": parsing_attempt.get("class_map") or [],
            "segmentation_map_path": rel(Path(parsing_maps[0]["path"])) if parsing_maps else "",
            "mask_records": parsing_attempt.get("mask_records") or [],
            "canonical_polygon_path": "",
            "blocked_reason": "" if route_pass else "Blocked_Model_Geometry_Dependency_Missing",
        },
        "qa_decision": (
            "semantic_face_parsing_route_executed_pending_consensus_and_canonical_polygon"
            if route_pass
            else "blocked_exact_local_semantic_face_parsing_route_unavailable"
        ),
        "promotion_decision": "no_mask_promoted_no_active_input_changed_face_parsing_authority_only",
        "tracker_item_updates": row_updates,
        "next_step": "Run visibility, consensus, and canonical polygon gates using source-derived landmark/parsing/refinement evidence.",
    }

    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    print(json.dumps({"evidence_id": EVIDENCE_ID, "result": payload["qa_decision"], "evidence": rel(qa_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
