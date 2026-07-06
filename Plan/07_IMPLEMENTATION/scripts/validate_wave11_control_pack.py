#!/usr/bin/env python3
"""Validate the static Wave 11 pack."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

REQUIRED_FILES = [
    "10_REGISTRIES/wave11_control_map_type_registry.json",
    "10_REGISTRIES/wave11_pose_preprocessor_registry.json",
    "10_REGISTRIES/wave11_controlnet_model_router_rules.json",
    "10_REGISTRIES/wave11_main_flow_control_map_inventory.json",
    "08_SCHEMAS/control_map_plan.schema.json",
    "08_SCHEMAS/per_character_skeleton.schema.json",
    "09_EXAMPLES/wave11_control_map_plan.example.json",
]

BLOCKED_EXTS = {".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf", ".onnx"}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    errors = []
    json_checked = 0

    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            errors.append(f"Missing required Wave 11 file: {rel}")

    for path in root.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
            json_checked += 1
        except Exception as e:
            errors.append(f"Invalid JSON {path.relative_to(root)}: {e}")

    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in BLOCKED_EXTS:
            errors.append(f"Model/binary file should not be in Git pack: {path.relative_to(root)}")

    status = "PASS" if not errors else "FAIL"
    report = {
        "status": status,
        "root": str(root),
        "json_checked": json_checked,
        "errors": errors,
        "runtime_proof_required_later": True,
        "ec2_required_now": False,
    }
    print(json.dumps(report, indent=2))
    return 0 if not errors else 2

if __name__ == "__main__":
    raise SystemExit(main())
