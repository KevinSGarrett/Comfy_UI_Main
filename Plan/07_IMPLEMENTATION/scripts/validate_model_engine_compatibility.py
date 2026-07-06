#!/usr/bin/env python3
"""
Validate that a model stack does not mix incompatible engine families.

Input stack example:
{
  "engine_family": "sdxl",
  "checkpoint_family": "sdxl",
  "loras": [{"name":"detail.safetensors","family":"sdxl"}]
}
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stack", required=True, help="Path to stack JSON")
    args = ap.parse_args()

    stack = json.loads(Path(args.stack).read_text(encoding="utf-8"))
    errors = []

    engine_family = stack.get("engine_family")
    checkpoint_family = stack.get("checkpoint_family")
    if engine_family != checkpoint_family:
        errors.append(f"checkpoint_family {checkpoint_family} does not match engine_family {engine_family}")

    for lora in stack.get("loras", []):
        lf = lora.get("family")
        if lf != engine_family:
            errors.append(f"LoRA {lora.get('name')} family {lf} does not match engine_family {engine_family}")

    for item in stack.get("blocked_assets", []):
        errors.append(f"Blocked asset present in stack: {item}")

    if errors:
        for e in errors:
            print("ERROR:", e)
        return 1
    print("PASS: stack families are compatible")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
