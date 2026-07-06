#!/usr/bin/env python3
"""Run local static validation for the Wave16 cumulative pack."""
from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path
from typing import List


REQUIRED = [
    "10_REGISTRIES/wave16_main_flow_refine_bridge_inventory.json",
    "10_REGISTRIES/wave16_refine_engine_bridge_matrix.json",
    "10_REGISTRIES/wave16_refine_pass_catalog.json",
    "10_REGISTRIES/wave16_low_denoise_policy.json",
    "10_REGISTRIES/wave16_base_preservation_rules.json",
    "08_SCHEMAS/image_refine_bridge_plan.schema.json",
    "09_EXAMPLES/wave16_refine_bridge_plan.example.json",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()

    errors: List[str] = []
    for rel in REQUIRED:
        if not (root / rel).exists():
            errors.append(f"missing required file: {rel}")

    json_count = 0
    for path in root.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
            json_count += 1
        except Exception as exc:  # pragma: no cover
            errors.append(f"json parse failed: {path.relative_to(root)}: {exc}")

    script_count = 0
    for path in (root / "07_IMPLEMENTATION" / "scripts").glob("*.py"):
        try:
            py_compile.compile(str(path), doraise=True)
            script_count += 1
        except Exception as exc:  # pragma: no cover
            errors.append(f"python compile failed: {path.name}: {exc}")

    inv_path = root / "10_REGISTRIES/wave16_main_flow_refine_bridge_inventory.json"
    inv = json.loads(inv_path.read_text(encoding="utf-8")) if inv_path.exists() else {}
    if inv.get("low_denoise_ksampler_count", 0) < 2:
        errors.append("expected at least two low-denoise sampler anchors in inventory")
    if inv.get("save_image_lane_count") != 8:
        errors.append("expected 8 SaveImage lanes in current Main Flow inventory")

    report = {
        "wave": 16,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "json_files_checked": json_count,
        "python_scripts_checked": script_count,
        "main_flow_nodes": inv.get("node_count"),
        "main_flow_save_lanes": inv.get("save_image_lane_count"),
        "low_denoise_ksamplers": inv.get("low_denoise_ksampler_count"),
        "runtime_execution_proven": False,
        "ec2_required_now": False,
    }

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
