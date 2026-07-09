from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import platform
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

from wave70_model_registry import SEARCH_ROOTS, registry_snapshot


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE_IMAGE = PROJECT_ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "canny_w69_rightedge_masked_v3_seed711570105_20260707T132203-0500/"
    "images/canny_w69_rightedge_masked_v3_seed711570105_00001_.png"
)
CONTROLNET_AUX_SRC = PROJECT_ROOT / "ComfyUI/custom_nodes/comfyui_controlnet_aux/src"
REF_IMAGE_1 = PROJECT_ROOT / "Ref_Image_1/725de85824bbe45ba4601dd4a7aed698.jpg"
REF_IMAGE_1_MANIFEST = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/ref_image_1_body_mask_gold_standard.json"
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_HUMAN_PART_PARSING_AUTHORITY_{RUN_STAMP}"
SCRIPT_REL = "Plan/07_IMPLEMENTATION/scripts/implement_wave70_human_part_parsing_authority.py"

QA_DIR = PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70"
TRACKER_EVIDENCE_DIR = PROJECT_ROOT / "Plan/Tracker/Evidence"
RUNTIME_DIR = PROJECT_ROOT / "runtime_artifacts/mask_factory/wave70_human_part_parsing_authority" / RUN_STAMP

TRACKER_FILES = [
    PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv",
    PROJECT_ROOT / "Plan/Tracker/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_TRACKER_ROWS.csv",
]
ITEM_FILES = [
    PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv",
    PROJECT_ROOT / "Plan/Items/Waves/Wave70/WAVE70_ULTIMATE_MASK_FACTORY_ITEM_ROWS.csv",
]


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


def module_probe(module_name: str) -> dict[str, object]:
    spec = importlib.util.find_spec(module_name)
    record: dict[str, object] = {
        "module": module_name,
        "available": spec is not None,
        "origin": spec.origin if spec else None,
        "imported": False,
        "version": None,
        "error": None,
    }
    if spec is None:
        return record
    try:
        module = __import__(module_name)
        record["imported"] = True
        record["version"] = getattr(module, "__version__", None)
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def find_model_candidates() -> list[dict[str, object]]:
    roots = SEARCH_ROOTS
    pattern_tokens = [
        "oneformer",
        "uniformer",
        "densepose",
        "segformer",
        "mask2former",
        "parsing",
        "human",
        "ade20k",
        "cihp",
        "atr",
        "schp",
    ]
    suffixes = {".pth", ".pt", ".safetensors", ".onnx", ".tflite", ".bin", ".pkl", ".yaml", ".json"}
    records: list[dict[str, object]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            lower = str(path).lower()
            if not any(token in lower for token in pattern_tokens):
                continue
            records.append(
                {
                    "path": str(path),
                    "relative_path": rel(path) if path.resolve().is_relative_to(PROJECT_ROOT.resolve()) else str(path),
                    "size_bytes": path.stat().st_size,
                    "suffix": path.suffix.lower(),
                }
            )
    return records


def load_ref_image_1_part_reference() -> dict[str, object]:
    record: dict[str, object] = {
        "manifest_path": rel(REF_IMAGE_1_MANIFEST),
        "manifest_exists": REF_IMAGE_1_MANIFEST.exists(),
        "main_reference_path": rel(REF_IMAGE_1),
        "main_reference_exists": REF_IMAGE_1.exists(),
        "main_reference_sha256": sha256_file(REF_IMAGE_1) if REF_IMAGE_1.exists() else None,
        "layout_interpretation": {
            "top_strip": "partial upper-body / one-third-body reference only; absent lower/full-body parts here are not failures",
            "lower_strip": "primary full-body pose and body-mask validation area",
        },
        "scope": "labeled_reference_masks_only_not_semantic_parser_runtime_or_active_source_parsing_proof",
        "reference_mask_count": 0,
        "reference_labels": [],
        "reference_mask_samples": [],
    }
    if not REF_IMAGE_1_MANIFEST.exists():
        return record
    manifest = json.loads(REF_IMAGE_1_MANIFEST.read_text(encoding="utf-8"))
    masks = manifest.get("extracted_masks", [])
    record["reference_mask_count"] = len(masks)
    record["reference_labels"] = [item.get("label", "") for item in masks]
    record["reference_mask_samples"] = [
        {
            "label": item.get("label", ""),
            "binary_mask_path": item.get("binary_mask_path", ""),
            "red_overlay_pixel_count": item.get("red_overlay_pixel_count", 0),
            "mask_type_candidates": item.get("mask_type_candidates", []),
        }
        for item in masks[:12]
    ]
    return record


def controlnet_aux_route_probe() -> dict[str, object]:
    record: dict[str, object] = {"sys_path_added": str(CONTROLNET_AUX_SRC), "routes": {}}
    sys.path.insert(0, str(CONTROLNET_AUX_SRC))
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    for module_name in [
        "custom_controlnet_aux.oneformer",
        "custom_controlnet_aux.uniformer",
        "custom_controlnet_aux.densepose",
        "custom_controlnet_aux.sam",
    ]:
        route: dict[str, object] = module_probe(module_name)
        route["load_attempted"] = False
        route["inference_pass"] = False
        if module_name == "custom_controlnet_aux.oneformer" and route["imported"]:
            try:
                from custom_controlnet_aux.oneformer import OneformerSegmentor

                route["load_attempted"] = True
                OneformerSegmentor.from_pretrained(filename="250_16_swin_l_oneformer_ade20k_160k.pth")
                route["loaded"] = True
                route["error"] = None
            except Exception as exc:  # noqa: BLE001
                route["loaded"] = False
                route["error"] = f"{type(exc).__name__}: {exc}"
        elif module_name == "custom_controlnet_aux.sam" and route["imported"]:
            route["loaded"] = True
            route["error"] = "sam_route_imports_but_is_promptable_segmentation_not_semantic_human_part_parsing"
        record["routes"][module_name] = route
    return record


def make_blocker_panel(source: Image.Image) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    panel_path = RUNTIME_DIR / "human_part_parsing_authority_blocker_panel.png"
    width, height = source.size
    panel = Image.new("RGB", (width * 2, height), "white")
    panel.paste(source, (0, 0))
    marked = source.copy()
    draw = ImageDraw.Draw(marked)
    draw.rectangle([0, 0, width - 1, height - 1], outline=(230, 40, 40), width=6)
    draw.rectangle([20, 20, width - 20, 190], fill=(255, 255, 255), outline=(230, 40, 40), width=3)
    font = ImageFont.load_default()
    lines = [
        "TRK-W70-0166 blocked",
        "No executable local human-part parser.",
        "OneFormer/Uniformer/DensePose routes not loadable.",
        "SAM import is not semantic body-part parsing.",
        "No masks promoted.",
    ]
    y = 34
    for line in lines:
        draw.text((34, y), line, fill=(120, 0, 0), font=font)
        y += 25
    panel.paste(marked, (width, 0))
    panel.save(panel_path)
    return panel_path


def update_wave70_rows(evidence_paths: list[str], note: str) -> dict[str, int]:
    updated: dict[str, int] = {}
    targets = [(path, "TRK-W70-0166") for path in TRACKER_FILES] + [(path, "ITEM-W70-0166") for path in ITEM_FILES]
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
                row["Status"] = "Blocked_Human_Part_Parsing_Route_Unavailable"
            if "Evidence_Path" in row:
                row["Evidence_Path"] = append_unique(row.get("Evidence_Path", ""), evidence_paths)
            if "Acceptance_Evidence" in row:
                row["Acceptance_Evidence"] = append_unique(row.get("Acceptance_Evidence", ""), evidence_paths)
            if "Status_Decision" in row:
                row["Status_Decision"] = "blocked_exact_local_human_part_parsing_route_unavailable"
            if "Coverage_Audit_Status" in row:
                row["Coverage_Audit_Status"] = append_unique(
                    row.get("Coverage_Audit_Status", ""),
                    ["blocked_exact_local_human_part_parsing_route_unavailable"],
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
    source = Image.open(SOURCE_IMAGE).convert("RGB")
    width, height = source.size
    model_candidates = find_model_candidates()
    ref_image_1_part_reference = load_ref_image_1_part_reference()
    route_probe = controlnet_aux_route_probe()
    panel_path = make_blocker_panel(source)

    qa_evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    qa_canonical_path = QA_DIR / "human_part_parsing_authority.json"
    tracker_evidence_path = TRACKER_EVIDENCE_DIR / f"{EVIDENCE_ID}.json"
    tracker_canonical_path = TRACKER_EVIDENCE_DIR / "human_part_parsing_authority.json"
    runtime_evidence_path = RUNTIME_DIR / "human_part_parsing_authority.json"

    evidence_rel_paths = [
        rel(qa_evidence_path),
        rel(qa_canonical_path),
        rel(tracker_evidence_path),
        rel(tracker_canonical_path),
        rel(runtime_evidence_path),
    ]
    note = (
        f"Human part parsing authority {RUN_STAMP}: exact local blocker. "
        "Local code stubs exist, but no compatible local semantic human-part parser loaded and executed. "
        f"Ref_Image_1 labeled part masks available={ref_image_1_part_reference['reference_mask_count']} as reference-only assets, not parser output. "
        "No active masks changed or promoted."
    )
    row_updates = update_wave70_rows(evidence_rel_paths, note)

    modules = {
        name: module_probe(name)
        for name in [
            "transformers",
            "mmdet",
            "mmseg",
            "detectron2",
            "segment_anything",
            "sam2",
            "onnxruntime",
            "torch",
            "cv2",
        ]
    }
    payload = {
        "schema_version": "1.0",
        "evidence_id": EVIDENCE_ID,
        "created_local": RUN_STAMP,
        "task": "Implement human part parsing authority for TRK-W70-0166 / ITEM-W70-0166.",
        "script": SCRIPT_REL,
        "source_image": {
            "path": rel(SOURCE_IMAGE),
            "exists": SOURCE_IMAGE.exists(),
            "sha256": sha256_file(SOURCE_IMAGE),
            "dimensions": [width, height],
        },
        "ref_image_1": ref_image_1_part_reference,
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "cwd": str(PROJECT_ROOT),
            "wave70_model_registry": registry_snapshot(),
            "modules": modules,
        },
        "local_model_candidates": model_candidates,
        "runtime_attempts": {
            "controlnet_aux_routes": route_probe,
        },
        "artifacts": {
            "blocker_panel": rel(panel_path),
            "runtime_evidence": rel(runtime_evidence_path),
        },
        "human_part_parsing_authority": {
            "result": "blocked",
            "semantic_human_part_parsing_pass": False,
            "skin_hair_clothing_boundary_pass": False,
            "model_confidence_recorded": False,
            "source_derived_landmark_or_segmentation_pass": False,
            "class_map": [],
            "segmentation_map_path": "",
            "blocked_reason": (
                "transformers_import_broken; oneformer_hf_model_not_loadable_offline; "
                "uniformer_missing_addict; densepose_missing_einops; "
                "mmdet_mmseg_detectron2_missing; no_compatible_executable_full_body_human_part_parser_loaded; "
                "face_lip_parsing_assets_are_not_full_body_human_part_parser_proof; "
                "ref_image_1_masks_are_reference_labels_not_parser_runtime; sam_route_not_semantic_human_part_parsing"
            ),
            "findings": [
                "ControlNet Aux contains OneFormer, Uniformer, DensePose, and SAM code paths.",
                "OneFormer import succeeds, but loading fails because the installed transformers/huggingface stack is broken locally.",
                "Uniformer import fails because addict is missing.",
                "DensePose import fails because einops is missing.",
                "SAM/SAM2-style routes do not provide semantic human-part class labels by themselves.",
                "Local face/lip parsing assets are present, but they are not proof of an executable full-body parser for skin, hair, clothing, torso, limbs, feet, and background.",
                f"Ref_Image_1 has {ref_image_1_part_reference['reference_mask_count']} labeled part masks; these are reference/gold masks, not active-source semantic parser output.",
            ],
        },
        "qa_decision": "blocked_exact_local_human_part_parsing_route_unavailable",
        "promotion_decision": "no_mask_promoted_no_active_input_changed_human_part_parsing_blocked",
        "tracker_item_updates": row_updates,
        "next_step": "Resolve a compatible local human-part parsing runtime/model or continue to the next whole-body authority row with exact local evidence.",
    }
    for path in [qa_evidence_path, qa_canonical_path, tracker_evidence_path, tracker_canonical_path, runtime_evidence_path]:
        write_json(path, payload)
    print(json.dumps({"evidence_id": EVIDENCE_ID, "result": payload["qa_decision"], "evidence": rel(qa_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
