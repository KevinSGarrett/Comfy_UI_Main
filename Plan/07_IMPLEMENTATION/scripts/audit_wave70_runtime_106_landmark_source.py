from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
QA_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_DIR = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence"
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_RUNTIME_106_LANDMARK_SOURCE_AUDIT_{RUN_STAMP}"

MODULES = [
    "face_alignment",
    "insightface",
    "dlib",
    "facexlib",
    "mediapipe",
    "cv2",
    "onnxruntime",
    "skimage",
]

KNOWN_FILES = {
    "mediapipe_face_landmarker_runtime_task": PROJECT_ROOT / "runtime_artifacts/mask_factory/mediapipe_models/face_landmarker_float16_latest.task",
    "comfyui_mediapipe_face_landmarker_code": PROJECT_ROOT / "ComfyUI/comfy_extras/mediapipe/face_landmarker.py",
    "comfyui_openpose_face_facenet_model": PROJECT_ROOT / "ComfyUI/custom_nodes/comfyui_controlnet_aux/ckpts/lllyasviel/Annotators/facenet.pth",
    "latest_face_landmark_authority": PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/face_landmark_authority.json",
    "lapa_supplied_landmark_route_eval": PROJECT_ROOT / "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_LAPA_SUPPLIED_LANDMARK_EYE_BROW_ROUTE_EVAL_20260710T052514-0500.json",
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


def module_record(name: str) -> dict[str, Any]:
    spec = importlib.util.find_spec(name)
    return {
        "module": name,
        "available": spec is not None,
        "origin": getattr(spec, "origin", None) if spec else None,
    }


def file_record(name: str, path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "asset": name,
        "exists": exists,
        "path": rel(path),
        "bytes": path.stat().st_size if exists else None,
        "sha256": sha256(path) if exists and path.is_file() else None,
    }


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    modules = [module_record(name) for name in MODULES]
    files = [file_record(name, path) for name, path in KNOWN_FILES.items()]

    face_authority = load_json(KNOWN_FILES["latest_face_landmark_authority"])
    lapa_eval = load_json(KNOWN_FILES["lapa_supplied_landmark_route_eval"])

    module_available = {item["module"]: item["available"] for item in modules}
    runtime_106_candidates = [
        name
        for name in ("face_alignment", "insightface", "dlib", "facexlib")
        if module_available.get(name)
    ]
    mediapipe_landmark_count = None
    if face_authority:
        mediapipe_landmark_count = face_authority.get("landmark_detection", {}).get("landmark_count")

    lapa_eye_pass = False
    if lapa_eval:
        for result in lapa_eval.get("region_results", []):
            if result.get("region") == "mf70_eyes_full":
                lapa_eye_pass = bool(result.get("best_pass_gate"))

    runtime_106_available = bool(runtime_106_candidates)
    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "local runtime 106-point face landmark source audit after LaPa supplied-landmark eye pass",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "modules": modules,
        "assets": files,
        "existing_face_landmark_authority": {
            "evidence": rel(KNOWN_FILES["latest_face_landmark_authority"]),
            "result": face_authority.get("result") if face_authority else None,
            "landmark_count": mediapipe_landmark_count,
            "models_available": face_authority.get("model_backed_geometry_authority", {}).get("models_available") if face_authority else [],
            "model_backed_geometry_authority_pass": face_authority.get("model_backed_geometry_authority", {}).get("model_backed_geometry_authority_pass") if face_authority else False,
        },
        "lapa_supplied_landmark_finding": {
            "evidence": rel(KNOWN_FILES["lapa_supplied_landmark_route_eval"]),
            "mf70_eyes_full_lapa_pass": lapa_eye_pass,
            "is_runtime_source": False,
        },
        "runtime_106_landmark_source_available": runtime_106_available,
        "runtime_106_candidate_modules": runtime_106_candidates,
        "mediapipe_runtime_available": bool(module_available.get("mediapipe")),
        "result": (
            "runtime_106_landmark_source_available_pending_gold_route_validation"
            if runtime_106_available
            else "blocked_runtime_106_landmark_source_not_available_local_only"
        ),
        "next_required_action": (
            "Run gold-backed downstream route validation for the available runtime 106-point landmark source."
            if runtime_106_available
            else "Register/install a local 106-point runtime face-landmark route, or keep the LaPa supplied-landmark eye pass "
            "as diagnostic-only and continue semantic parsing/policy repair for brows."
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
                "runtime_106_landmark_source_available": evidence["runtime_106_landmark_source_available"],
                "mediapipe_runtime_available": evidence["mediapipe_runtime_available"],
                "runtime_106_candidate_modules": runtime_106_candidates,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
