from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
COMFYUI_ROOT = PROJECT_ROOT / "ComfyUI"
COMFYUI_VENV_PYTHON = COMFYUI_ROOT / ".venv/Scripts/python.exe"
SYSTEM_PYTHON = Path(sys.executable)
LORA_OPENPOSE_MODELS = Path(r"C:\Comfy_UI_Lora\OpenPose\models")

SEARCH_ROOTS = [
    PROJECT_ROOT,
    COMFYUI_ROOT,
    COMFYUI_ROOT / "models",
    COMFYUI_ROOT / "custom_nodes/comfyui_controlnet_aux",
    PROJECT_ROOT / "models",
    LORA_OPENPOSE_MODELS,
    Path.home() / ".cache/huggingface",
    Path.home() / ".cache/torch",
]

KNOWN_ASSETS = {
    "mediapipe_face_landmarker_task": [
        LORA_OPENPOSE_MODELS / "mediapipe/face_landmarker.task",
        COMFYUI_ROOT / "models/mediapipe/face_landmarker.task",
        COMFYUI_ROOT / "custom_nodes/comfyui_controlnet_aux/src/custom_controlnet_aux/mediapipe/face_landmarker.task",
    ],
    "mediapipe_pose_landmarker_task": [
        LORA_OPENPOSE_MODELS / "mediapipe/pose_landmarker_heavy.task",
    ],
    "mediapipe_hand_landmarker_task": [
        COMFYUI_ROOT / "custom_nodes/comfyui_controlnet_aux/src/custom_controlnet_aux/mesh_graphormer/hand_landmarker.task",
        LORA_OPENPOSE_MODELS / "mediapipe/hand_landmarker.task",
    ],
    "sam2_hiera_tiny_checkpoint": [
        LORA_OPENPOSE_MODELS / "sam2/sam2.1_hiera_tiny.pt",
    ],
    "bisenet_face_parsing_checkpoint": [
        LORA_OPENPOSE_MODELS / "face_parsing/79999_iter.pth",
    ],
    "schp_lip_checkpoint": [
        LORA_OPENPOSE_MODELS / "schp/exp-schp-201908261155-lip.pth",
    ],
    "dwpose_detector_onnx": [
        LORA_OPENPOSE_MODELS / "dwpose/yolox_l.onnx",
    ],
    "dwpose_pose_onnx": [
        LORA_OPENPOSE_MODELS / "dwpose/dw-ll_ucoco_384.onnx",
    ],
    "ultralytics_yolo_pose": [
        LORA_OPENPOSE_MODELS / "ultralytics/yolo11x-pose.pt",
    ],
    "openpose_body_model": [
        COMFYUI_ROOT / "custom_nodes/comfyui_controlnet_aux/ckpts/lllyasviel/Annotators/body_pose_model.pth",
    ],
    "openpose_hand_model": [
        COMFYUI_ROOT / "custom_nodes/comfyui_controlnet_aux/ckpts/lllyasviel/Annotators/hand_pose_model.pth",
    ],
    "openpose_face_model": [
        COMFYUI_ROOT / "custom_nodes/comfyui_controlnet_aux/ckpts/lllyasviel/Annotators/facenet.pth",
    ],
}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256_file(path: Path, limit: int | None = None) -> str:
    digest = hashlib.sha256()
    remaining = limit
    with path.open("rb") as handle:
        while True:
            chunk_size = 1024 * 1024 if remaining is None else min(1024 * 1024, remaining)
            if chunk_size <= 0:
                break
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
            if remaining is not None:
                remaining -= len(chunk)
    return digest.hexdigest()


def file_record(path: Path, hash_limit: int | None = 256 * 1024 * 1024) -> dict[str, object]:
    record: dict[str, object] = {
        "path": str(path),
        "relative_path": rel(path) if path.exists() else str(path),
        "exists": path.exists(),
    }
    if path.exists():
        record.update(
            {
                "size_bytes": path.stat().st_size,
                "suffix": path.suffix.lower(),
                "sha256": sha256_file(path, hash_limit),
                "sha256_limited": hash_limit is not None and path.stat().st_size > hash_limit,
            }
        )
    return record


def first_existing_asset(asset_id: str) -> Path | None:
    for path in KNOWN_ASSETS.get(asset_id, []):
        if path.exists():
            return path
    return None


def known_asset_records() -> dict[str, object]:
    return {
        asset_id: {
            "candidates": [file_record(path) for path in paths],
            "selected_path": str(first_existing_asset(asset_id) or ""),
        }
        for asset_id, paths in KNOWN_ASSETS.items()
    }


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


def python_environment_probe(python_path: Path, modules: list[str]) -> dict[str, object]:
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
            timeout=45,
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


def discover_candidates(tokens: list[str], suffixes: set[str]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    seen: set[str] = set()
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            lower = str(path).lower()
            if not any(token.lower() in lower for token in tokens):
                continue
            resolved = str(path.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            records.append(file_record(path))
    return records


def registry_snapshot() -> dict[str, object]:
    return {
        "project_root": str(PROJECT_ROOT),
        "comfyui_root": str(COMFYUI_ROOT),
        "comfyui_venv_python": str(COMFYUI_VENV_PYTHON),
        "system_python": str(SYSTEM_PYTHON),
        "search_roots": [{"path": str(path), "exists": path.exists()} for path in SEARCH_ROOTS],
        "known_assets": known_asset_records(),
    }
