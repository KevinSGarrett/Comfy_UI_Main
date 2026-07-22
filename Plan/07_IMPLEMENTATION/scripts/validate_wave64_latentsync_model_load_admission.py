#!/usr/bin/env python3
"""Validate the exact LatentSync UNet model-load-only admission."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ALLOWED_TRUE = {
    "lease_receipt_validation",
    "model_config_read",
    "checkpoint_weight_load",
    "cuda_model_residency",
    "parameter_inventory",
    "process_exit_cleanup",
}


def validate(value: dict) -> list[str]:
    errors: list[str] = []
    if value.get("status") != "LATENTSYNC_UNET_MODEL_LOAD_CANARY_ADMITTED_EXECUTION_PENDING":
        errors.append("model-load admission status mismatch")
    code = value.get("code", {})
    if code.get("commit") != "a229c3948406bc2cf6eaf4873e662e70c6a04746":
        errors.append("model-load code commit mismatch")
    if code.get("tree") != "51f62bc8aea02da92b1a349077cfb78d0456f742":
        errors.append("model-load code tree mismatch")
    if code.get("config_sha256") != "652bbf469d3baf68f1b364fd47409901cd8d1bf8bb7754133aa69a28132312e6":
        errors.append("model-load config identity mismatch")
    model = value.get("model", {})
    if model.get("checkpoint_sha256") != "0a478e89eb660f82da4c35dbdde8a5adfb27f99d1b4e50edd03729e1e98316d3":
        errors.append("model-load checkpoint identity mismatch")
    if model.get("checkpoint_bytes") != 5072222488:
        errors.append("model-load checkpoint size mismatch")
    lease = value.get("lease", {})
    if lease.get("project") != "comfyui_main" or lease.get("profile") != "comfyui_model_qualification":
        errors.append("model-load lease scope mismatch")
    if lease.get("mode") != "exclusive" or lease.get("minimum_reserved_peak_gib", 0) < 12:
        errors.append("model-load lease capacity mismatch")
    execution = value.get("execution", {})
    if execution.get("isolated_child_process") is not True:
        errors.append("model-load must use an isolated child process")
    if execution.get("forward_inference") is not False or execution.get("fixture_consumption") is not False:
        errors.append("model-load admission exceeds load-only execution")
    authority = value.get("authority", {})
    if any(authority.get(name) is not True for name in ALLOWED_TRUE):
        errors.append("required model-load authority missing")
    if any(flag is not False for name, flag in authority.items() if name not in ALLOWED_TRUE):
        errors.append("model-load admission exceeds load-only authority")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("admission", type=Path)
    args = parser.parse_args()
    errors = validate(json.loads(args.admission.read_text(encoding="utf-8")))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("W64_AQA_LATENTSYNC_MODEL_LOAD_ADMISSION_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
