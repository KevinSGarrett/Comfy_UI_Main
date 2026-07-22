#!/usr/bin/env python3
"""Validate the exact LatentSync package/project import-canary admission."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_IMPORTS = [
    "antlr4", "insightface", "python_speech_features", "decord", "torch", "torchvision",
    "diffusers", "transformers", "onnx", "onnxruntime", "cv2", "mediapipe", "omegaconf",
    "accelerate", "DeepCache", "latentsync.models.unet",
    "latentsync.pipelines.lipsync_pipeline", "latentsync.whisper.audio2feature",
]
ALLOWED_TRUE = {
    "package_import", "project_code_import", "module_origin_inspection", "decord_binary_hash_read"
}


def validate(admission: dict) -> list[str]:
    errors: list[str] = []
    if admission.get("status") != "PACKAGE_AND_PROJECT_IMPORT_CANARY_ADMITTED_EXECUTION_PENDING":
        errors.append("import canary admission status mismatch")
    if admission.get("imports") != EXPECTED_IMPORTS:
        errors.append("import canary module set mismatch")
    environment = admission.get("environment", {})
    if environment.get("receipt_sha256") != "a13ba52cb63e871ada18550db06544fee51c58341d546edb276b3ecdf4c3f68e":
        errors.append("import canary environment receipt binding mismatch")
    code = admission.get("code", {})
    if code.get("commit") != "a229c3948406bc2cf6eaf4873e662e70c6a04746" or code.get("tree") != "51f62bc8aea02da92b1a349077cfb78d0456f742":
        errors.append("import canary code identity mismatch")
    authority = admission.get("authority", {})
    if any(authority.get(name) is not True for name in ALLOWED_TRUE):
        errors.append("required import-canary authority missing")
    if any(value is not False for name, value in authority.items() if name not in ALLOWED_TRUE):
        errors.append("import canary admission exceeds import-only authority")
    if admission.get("environment_controls") != {
        "CUDA_VISIBLE_DEVICES": "", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"
    }:
        errors.append("import canary environment controls mismatch")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("admission", type=Path)
    args = parser.parse_args()
    admission = json.loads(args.admission.read_text(encoding="utf-8"))
    errors = validate(admission)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("W64_AQA_LATENTSYNC_IMPORT_CANARY_ADMISSION_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
