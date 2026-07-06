#!/usr/bin/env python3
"""Run local validation for the Wave 24 multi-character instance-layout pack."""
from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path
from typing import Any


REQUIRED_FILES = [
    "10_REGISTRIES/wave24_instance_layout_contract_profiles.json",
    "10_REGISTRIES/wave24_character_instance_field_requirements.json",
    "10_REGISTRIES/wave24_depth_order_profiles.json",
    "10_REGISTRIES/wave24_frame_placement_profiles.json",
    "10_REGISTRIES/wave24_region_ownership_rules.json",
    "10_REGISTRIES/wave24_instance_qa_scoring_rules.json",
    "10_REGISTRIES/wave24_instance_layout_rerun_policy.json",
    "10_REGISTRIES/wave24_main_flow_instance_layout_inventory.json",
    "08_SCHEMAS/multi_character_instance_layout.schema.json",
    "08_SCHEMAS/character_instance.schema.json",
    "09_EXAMPLES/wave24_multi_character_instance_layout.example.json",
]

SCRIPT_FILES = [
    "07_IMPLEMENTATION/scripts/compile_multi_character_instance_layout.py",
    "07_IMPLEMENTATION/scripts/validate_multi_character_instance_layout.py",
    "07_IMPLEMENTATION/scripts/score_instance_layout_evidence.py",
    "07_IMPLEMENTATION/scripts/inventory_main_flow_instance_layout_wave24.py",
    "07_IMPLEMENTATION/scripts/run_wave24_local_validation.py",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    errors: list[str] = []

    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            errors.append(f"missing required file: {rel}")

    json_files = list(root.rglob("*.json"))
    for path in json_files:
        try:
            load_json(path)
        except Exception as exc:
            errors.append(f"invalid JSON: {path.relative_to(root)}: {exc}")

    for rel in SCRIPT_FILES:
        path = root / rel
        if not path.exists():
            errors.append(f"missing script: {rel}")
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            errors.append(f"script compile failed: {rel}: {exc}")

    inv_path = root / "10_REGISTRIES/wave24_main_flow_instance_layout_inventory.json"
    if inv_path.exists():
        inv = load_json(inv_path)
        if inv.get("node_count", 0) <= 0:
            errors.append("main flow inventory node_count is zero")
        if len(inv.get("mask_capable_anchors", [])) < 1:
            errors.append("main flow inventory has no mask-capable anchors")
        if len(inv.get("low_denoise_anchors", [])) < 1:
            errors.append("main flow inventory has no low-denoise anchors")

    if errors:
        print("FAIL: Wave24 validation failed")
        for err in errors:
            print(f"- {err}")
        return 1

    print("PASS: Wave24 multi-character instance-layout pack validated")
    print(f"JSON files checked: {len(json_files)}")
    print(f"Required files checked: {len(REQUIRED_FILES)}")
    print(f"Scripts checked: {len(SCRIPT_FILES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
