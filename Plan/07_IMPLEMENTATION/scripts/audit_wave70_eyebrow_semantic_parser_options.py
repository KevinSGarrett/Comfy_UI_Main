from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from wave70_model_registry import first_existing_asset


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
QA_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_DIR = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence"
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_EYEBROW_SEMANTIC_PARSER_OPTIONS_AUDIT_{RUN_STAMP}"

SOURCE_PATTERNS = {
    "combined_gold_gate": "W70_FACIAL_COMBINED_GOLD_GATE_DECISION_*.json",
    "eye_brow_dataset_failure_diagnostic": "W70_EYE_BROW_ROUTE_DATASET_FAILURE_DIAGNOSTIC_*.json",
    "runtime_106_landmark_source_audit": "W70_RUNTIME_106_LANDMARK_SOURCE_AUDIT_*.json",
    "lapa_supplied_landmark_eye_brow_routes": "W70_LAPA_SUPPLIED_LANDMARK_EYE_BROW_ROUTE_EVAL_*.json",
    "lapa_parser_landmark_brow_routes": "W70_LAPA_PARSER_LANDMARK_BROW_ROUTE_EVAL_*.json",
}

MODULES = [
    "torch",
    "cv2",
    "mediapipe",
    "onnxruntime",
    "face_alignment",
    "insightface",
    "dlib",
    "facexlib",
]

OPTION_ASSETS = {
    "current_bisenet_face_parser": {
        "asset_id": "bisenet_face_parsing_checkpoint",
        "role": "current semantic face parser with eyebrow classes used by prior gold brow routes",
    },
    "schp_lip_human_parser": {
        "asset_id": "schp_lip_checkpoint",
        "role": "human parsing checkpoint; local asset is not proven to expose facial eyebrow semantic labels",
    },
    "openpose_face_model": {
        "asset_id": "openpose_face_model",
        "role": "face landmark/pose model, not a semantic eyebrow segmentation parser",
    },
    "sam2_promptable_segmenter": {
        "asset_id": "sam2_hiera_tiny_checkpoint",
        "role": "promptable segmentation/refinement model; no automatic eyebrow prompt authority is registered",
    },
    "mediapipe_face_landmarker": {
        "asset_id": "mediapipe_face_landmarker_task",
        "role": "runtime face landmarks; prior MediaPipe eye/brow route family failed combined gold gates",
    },
}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def latest(pattern: str) -> Path | None:
    matches = sorted(QA_DIR.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def module_record(name: str) -> dict[str, Any]:
    spec = importlib.util.find_spec(name)
    return {
        "module": name,
        "available": spec is not None,
        "origin": getattr(spec, "origin", None) if spec else None,
    }


def file_record(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"exists": False, "path": None, "relative_path": None, "bytes": None, "sha256": None}
    exists = path.exists()
    return {
        "exists": exists,
        "path": str(path),
        "relative_path": rel(path) if exists else str(path),
        "bytes": path.stat().st_size if exists and path.is_file() else None,
        "sha256": sha256(path) if exists and path.is_file() else None,
    }


def source_record(name: str, pattern: str) -> dict[str, Any]:
    path = latest(pattern)
    if path is None:
        return {"name": name, "exists": False, "path": None, "result": None, "summary": None}
    payload = load_json(path)
    summary: dict[str, Any] = {}
    if name == "combined_gold_gate":
        summary = {
            "supported_regions": payload.get("supported_regions"),
            "blocked_regions": payload.get("blocked_regions"),
        }
    elif name == "lapa_parser_landmark_brow_routes":
        region = payload.get("region_result", {})
        summary = {
            "region": region.get("region"),
            "best_route": region.get("best_route"),
            "best_pass_gate": region.get("best_pass_gate"),
            "best_summary": region.get("best_summary"),
            "best_failed_reasons": region.get("best_failed_reasons"),
        }
    elif name == "runtime_106_landmark_source_audit":
        summary = {
            "runtime_106_landmark_source_available": payload.get("runtime_106_landmark_source_available"),
            "mediapipe_runtime_available": payload.get("mediapipe_runtime_available"),
            "runtime_106_candidate_modules": payload.get("runtime_106_candidate_modules"),
        }
    elif name == "lapa_supplied_landmark_eye_brow_routes":
        results = payload.get("region_results", [])
        summary = {
            item.get("region"): {
                "best_route": item.get("best_route"),
                "best_pass_gate": item.get("best_pass_gate"),
                "best_summary": item.get("best_summary"),
            }
            for item in results
            if item.get("region") in {"mf70_eyes_full", "mf70_eyebrows"}
        }
    elif name == "eye_brow_dataset_failure_diagnostic":
        summary = {"any_dataset_level_pass": payload.get("any_dataset_level_pass")}
    return {
        "name": name,
        "exists": True,
        "path": rel(path),
        "result": payload.get("result"),
        "summary": summary,
    }


def classify_option(option_name: str, exists: bool) -> dict[str, Any]:
    if option_name == "current_bisenet_face_parser":
        return {
            "usable_as_stronger_eyebrow_parser_now": False,
            "classification": "available_but_already_current_parser_authority",
            "reason": "BiSeNet face parsing is the parser already used in the latest parser+landmark brow route, which failed the LaPa gold gate.",
        }
    if option_name == "schp_lip_human_parser":
        return {
            "usable_as_stronger_eyebrow_parser_now": False,
            "classification": "available_but_not_registered_for_eyebrow_semantics" if exists else "asset_missing",
            "reason": "The registered SCHP asset is a LIP human-parsing checkpoint and is not currently proven or wired as a face eyebrow semantic-label parser.",
        }
    if option_name == "openpose_face_model":
        return {
            "usable_as_stronger_eyebrow_parser_now": False,
            "classification": "available_landmark_model_not_semantic_parser" if exists else "asset_missing",
            "reason": "OpenPose facenet is a landmark/pose asset, not an eyebrow segmentation authority; landmark-band repair already failed the gold gate.",
        }
    if option_name == "sam2_promptable_segmenter":
        return {
            "usable_as_stronger_eyebrow_parser_now": False,
            "classification": "available_promptable_segmenter_without_automatic_brow_prompt_policy" if exists else "asset_missing",
            "reason": "SAM2 can refine prompted regions, but no automatic eyebrow prompt source or gold-backed route is registered for Mask Factory promotion.",
        }
    if option_name == "mediapipe_face_landmarker":
        return {
            "usable_as_stronger_eyebrow_parser_now": False,
            "classification": "available_landmarker_already_failed_prior_route_family" if exists else "asset_missing",
            "reason": "MediaPipe landmarks are available, but MediaPipe-only and hybrid eye/brow routes failed combined gold gates.",
        }
    return {
        "usable_as_stronger_eyebrow_parser_now": False,
        "classification": "unknown",
        "reason": "No classifier was registered for this option.",
    }


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)

    options = []
    for option_name, spec in OPTION_ASSETS.items():
        path = first_existing_asset(spec["asset_id"])
        record = file_record(path)
        exists = bool(record["exists"])
        options.append(
            {
                "option": option_name,
                "asset_id": spec["asset_id"],
                "role": spec["role"],
                "asset": record,
                **classify_option(option_name, exists),
            }
        )

    usable_now = [item for item in options if item["usable_as_stronger_eyebrow_parser_now"]]
    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "local Wave70 eyebrow semantic parser options audit after gold-backed eyebrow route failure",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "project_root": str(PROJECT_ROOT),
        "gold_mask_authority": {
            "masked_warehouse": str(PROJECT_ROOT / "MaskedWarehouse"),
            "datasets": ["CelebAMask-HQ", "LaPa"],
            "single_generated_portrait_is_pass_authority": False,
        },
        "module_probe": [module_record(name) for name in MODULES],
        "source_evidence": [
            source_record(name, pattern) for name, pattern in SOURCE_PATTERNS.items()
        ],
        "parser_options": options,
        "stronger_local_eyebrow_semantic_parser_registered_now": bool(usable_now),
        "registered_stronger_options": [item["option"] for item in usable_now],
        "result": "blocked_no_stronger_local_eyebrow_semantic_parser_registered",
        "decision": (
            "Do not keep tuning eyebrow landmark bands or use the generated portrait as pass evidence. "
            "The registered local assets do not currently provide a stronger automatic eyebrow semantic parser than the failed BiSeNet-backed route."
        ),
        "next_required_action": (
            "Register and validate a stronger face parser with eyebrow labels, define an explicit eyebrow dataset-vs-runtime policy, "
            "or switch to another blocked facial/body row with a genuinely new gold-backed route."
        ),
    }

    evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / evidence_path.name
    write_json(evidence_path, evidence)
    write_json(tracker_path, evidence)
    print(
        json.dumps(
            {
                "evidence": rel(evidence_path),
                "tracker": rel(tracker_path),
                "result": evidence["result"],
                "stronger_local_eyebrow_semantic_parser_registered_now": evidence[
                    "stronger_local_eyebrow_semantic_parser_registered_now"
                ],
                "parser_options_checked": [item["option"] for item in options],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
