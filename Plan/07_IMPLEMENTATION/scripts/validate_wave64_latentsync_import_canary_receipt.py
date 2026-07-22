#!/usr/bin/env python3
"""Validate the retained LatentSync import-only canary receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


RECEIPT_SHA256 = "a5b8f074a3ab8ed02c8e2d1c2eb84777fd97e46fa158c9728cabb537f0ffc8dd"
EXPECTED_IMPORTS = [
    "antlr4", "insightface", "python_speech_features", "decord", "torch", "torchvision",
    "diffusers", "transformers", "onnx", "onnxruntime", "cv2", "mediapipe", "omegaconf",
    "accelerate", "DeepCache", "latentsync.models.unet",
    "latentsync.pipelines.lipsync_pipeline", "latentsync.whisper.audio2feature",
]
EXPECTED_CLAIMS = {
    "audio_visual_authority": False,
    "gpu_or_lease_polled": False,
    "inference_performed": False,
    "model_config_read": False,
    "model_constructed": False,
    "package_imported": True,
    "product_authority": False,
    "project_code_imported": True,
    "role_activated": False,
    "service_changed": False,
    "tensor_allocated": False,
    "weights_accessed": False,
}


def validate(receipt: dict, receipt_path: Path) -> list[str]:
    errors: list[str] = []
    if hashlib.sha256(receipt_path.read_bytes()).hexdigest() != RECEIPT_SHA256:
        errors.append("LatentSync import receipt hash mismatch")
    if receipt.get("status") != "PACKAGE_AND_PROJECT_IMPORTS_PASS_MODEL_LOAD_PENDING":
        errors.append("LatentSync import canary status mismatch")
    imports = receipt.get("imports", [])
    if receipt.get("import_count") != 18 or [item.get("name") for item in imports] != EXPECTED_IMPORTS:
        errors.append("LatentSync imported module set mismatch")
    environment_root = Path(receipt.get("environment_root", ""))
    code_root = Path(receipt.get("code", {}).get("root", ""))
    for item in imports:
        origin = Path(item.get("origin", ""))
        if not (origin.is_relative_to(environment_root) or origin.is_relative_to(code_root)):
            errors.append(f"module origin outside admitted roots: {item.get('name')}")
    code = receipt.get("code", {})
    if code.get("commit") != "a229c3948406bc2cf6eaf4873e662e70c6a04746" or code.get("tree") != "51f62bc8aea02da92b1a349077cfb78d0456f742" or code.get("clean") is not True:
        errors.append("LatentSync imported checkout identity mismatch")
    decord = receipt.get("decord_binary", {})
    if decord.get("bytes") != 12465984 or decord.get("sha256") != "98b260c5812106648ba299279916fbe98439893e346d4efdcf5cde66ba8973da":
        errors.append("decord imported binary identity mismatch")
    if receipt.get("runtime_claims") != EXPECTED_CLAIMS:
        errors.append("LatentSync import receipt authority claims mismatch")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    errors = validate(receipt, args.receipt)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("W64_AQA_LATENTSYNC_IMPORT_CANARY_RECEIPT_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
