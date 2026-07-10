#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
COMFYUI_ROOT = PROJECT_ROOT / "ComfyUI"
COMFYUI_VENV_PYTHON = COMFYUI_ROOT / ".venv" / "Scripts" / "python.exe"
LORA_OPENPOSE_MODELS = Path(r"C:\Comfy_UI_Lora\OpenPose\models")
QA_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_DIR = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence"
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_HAIR_PERSON_SEGMENTATION_AUTHORITY_AUDIT_{RUN_STAMP}"

MODULES = [
    "sam2",
    "segment_anything",
    "rembg",
    "transparent_background",
    "onnxruntime",
    "mediapipe",
    "torch",
    "torchvision",
]

KNOWN_ASSETS = {
    "sam2_hiera_tiny_checkpoint": LORA_OPENPOSE_MODELS / "sam2" / "sam2.1_hiera_tiny.pt",
    "bisenet_face_parsing_checkpoint": LORA_OPENPOSE_MODELS / "face_parsing" / "79999_iter.pth",
    "schp_lip_checkpoint": LORA_OPENPOSE_MODELS / "schp" / "exp-schp-201908261155-lip.pth",
    "background_removal_models_dir": COMFYUI_ROOT / "models" / "background_removal",
}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def module_probe(module_name: str) -> dict[str, Any]:
    record: dict[str, Any] = {
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
        if spec is not None:
            module = __import__(module_name)
            record["imported"] = True
            record["version"] = getattr(module, "__version__", None)
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def python_module_probe(python_path: Path) -> dict[str, Any]:
    if not python_path.exists():
        return {"python": str(python_path), "exists": False, "modules": {}, "error": "python_not_found"}
    code = (
        "import importlib.util, json\n"
        f"mods={MODULES!r}\n"
        "out={}\n"
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
        "    out[m]=rec\n"
        "print(json.dumps(out))\n"
    )
    proc = subprocess.run(
        [str(python_path), "-c", code],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    if proc.returncode != 0:
        return {
            "python": str(python_path),
            "exists": True,
            "modules": {},
            "error": proc.stderr.strip() or f"exit_{proc.returncode}",
        }
    return {"python": str(python_path), "exists": True, "modules": json.loads(proc.stdout), "error": None}


def path_record(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": str(path),
        "relative_path": rel(path),
        "exists": path.exists(),
        "is_dir": path.is_dir(),
        "is_file": path.is_file(),
    }
    if path.exists() and path.is_file():
        record["size_bytes"] = path.stat().st_size
    if path.exists() and path.is_dir():
        files = [item for item in path.rglob("*") if item.is_file() and item.stat().st_size > 0]
        record["nonempty_file_count"] = len(files)
        record["sample_files"] = [rel(item) for item in files[:20]]
    return record


def bounded_file_scan(root: Path, tokens: tuple[str, ...]) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    suffixes = {".pt", ".pth", ".onnx", ".safetensors", ".ckpt", ".task", ".yaml", ".json"}
    out: list[dict[str, Any]] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        lower = str(path).lower()
        if any(token in lower for token in tokens):
            out.append(path_record(path))
        if len(out) >= 200:
            break
    return out


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    system_modules = {module: module_probe(module) for module in MODULES}
    comfyui_modules = python_module_probe(COMFYUI_VENV_PYTHON)
    known_assets = {name: path_record(path) for name, path in KNOWN_ASSETS.items()}
    candidate_files = {
        "comfyui_models": bounded_file_scan(COMFYUI_ROOT / "models", ("sam", "biref", "u2net", "isnet", "rembg", "schp", "lip", "seg")),
        "lora_openpose_models": bounded_file_scan(LORA_OPENPOSE_MODELS, ("sam", "biref", "u2net", "isnet", "rembg", "schp", "lip", "seg", "parsing")),
    }
    sam2_importable = bool(system_modules["sam2"]["available"] or comfyui_modules.get("modules", {}).get("sam2", {}).get("available"))
    sam2_checkpoint_exists = bool(known_assets["sam2_hiera_tiny_checkpoint"]["exists"])
    background_removal_model_count = int(known_assets["background_removal_models_dir"].get("nonempty_file_count", 0))
    result = (
        "hair_person_segmentation_authority_audit_sam2_candidate_checkpoint_present"
        if sam2_importable and sam2_checkpoint_exists
        else "hair_person_segmentation_authority_audit_no_promotable_local_authority"
    )
    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "local audit for stronger hair/person segmentation authority after mf70_hair foreground ownership geometry failed combined gold",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "system_python": str(sys.executable),
        "comfyui_venv_python": str(COMFYUI_VENV_PYTHON),
        "module_probe_system_python": system_modules,
        "module_probe_comfyui_venv": comfyui_modules,
        "known_assets": known_assets,
        "candidate_files": candidate_files,
        "findings": {
            "sam2_importable": sam2_importable,
            "sam2_checkpoint_exists": sam2_checkpoint_exists,
            "background_removal_nonempty_model_count": background_removal_model_count,
            "rembg_available": bool(system_modules["rembg"]["available"] or comfyui_modules.get("modules", {}).get("rembg", {}).get("available")),
            "segment_anything_available": bool(
                system_modules["segment_anything"]["available"]
                or comfyui_modules.get("modules", {}).get("segment_anything", {}).get("available")
            ),
        },
        "result": result,
        "next_required_action": (
            "If SAM2 checkpoint and module are present, create a bounded SAM2 hair/person promptability probe on MaskedWarehouse gold samples. "
            "If not, register/download a stronger person-instance or hair segmentation model, or write a hair-row policy before target-portrait proof."
        ),
    }
    qa_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / f"{EVIDENCE_ID}.json"
    write_json(qa_path, evidence)
    write_json(tracker_path, evidence)
    print(
        json.dumps(
            {
                "evidence": str(qa_path),
                "tracker": str(tracker_path),
                "result": result,
                "findings": evidence["findings"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
