#!/usr/bin/env python3
"""Wave15 local pack validation."""
from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_FILES = [
    "10_REGISTRIES/wave15_image_base_lane_registry.json",
    "10_REGISTRIES/wave15_base_lane_router_rules.json",
    "10_REGISTRIES/wave15_fallback_policy.json",
    "10_REGISTRIES/wave15_base_generation_qa_gates.json",
    "10_REGISTRIES/wave15_main_flow_base_lane_inventory.json",
    "08_SCHEMAS/base_generation_lane.schema.json",
    "08_SCHEMAS/base_generation_plan.schema.json",
    "09_EXAMPLES/wave15_image_base_generation_request.example.json",
    "09_EXAMPLES/wave15_base_generation_plan.example.json",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default="11_RELEASES/WAVE15_VALIDATION_REPORT.json")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    errors: List[str] = []

    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            errors.append(f"missing_required_file:{rel}")

    json_files_checked = 0
    for p in root.rglob("*.json"):
        try:
            load_json(p)
            json_files_checked += 1
        except Exception as exc:
            errors.append(f"json_parse_error:{p.relative_to(root)}:{type(exc).__name__}:{exc}")

    new_scripts_checked = 0
    for p in (root / "07_IMPLEMENTATION" / "scripts").glob("*wave15*.py"):
        try:
            py_compile.compile(str(p), doraise=True)
            new_scripts_checked += 1
        except Exception as exc:
            errors.append(f"python_compile_error:{p.relative_to(root)}:{type(exc).__name__}:{exc}")

    # Also compile non-wave15 scripts added by this wave.
    for name in [
        "select_image_base_lane.py",
        "compile_image_base_generation_plan.py",
        "validate_image_base_generation_plan.py",
        "patch_base_generation_workflow.py",
        "score_base_image_evidence.py",
        "fallback_base_generation_router.py"
    ]:
        p = root / "07_IMPLEMENTATION" / "scripts" / name
        if p.exists():
            try:
                py_compile.compile(str(p), doraise=True)
                new_scripts_checked += 1
            except Exception as exc:
                errors.append(f"python_compile_error:{p.relative_to(root)}:{type(exc).__name__}:{exc}")

    lane_registry = load_json(root / "10_REGISTRIES/wave15_image_base_lane_registry.json")
    main_inventory = load_json(root / "10_REGISTRIES/wave15_main_flow_base_lane_inventory.json")
    qa_gates = load_json(root / "10_REGISTRIES/wave15_base_generation_qa_gates.json")
    fallback_policy = load_json(root / "10_REGISTRIES/wave15_fallback_policy.json")

    lane_ids = {row.get("lane_id") for row in lane_registry}
    if "flux2_dev_primary_base" not in lane_ids:
        errors.append("flux2_lane_missing")
    if "flux1_dev_primary_base" not in lane_ids:
        errors.append("flux1_dev_lane_missing")
    if "sdxl_realvisxl_base_lane" not in lane_ids:
        errors.append("sdxl_lane_missing")
    if "zimage_turbo_base_lane" not in lane_ids:
        errors.append("zimage_lane_missing")
    if "pony_specialty_lane" not in lane_ids:
        errors.append("pony_lane_missing")

    report = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "json_files_checked": json_files_checked,
        "new_python_scripts_checked": new_scripts_checked,
        "image_base_lanes": len(lane_registry),
        "flux2_lanes": sum(1 for row in lane_registry if row.get("engine_family") == "flux2"),
        "main_flow_nodes": main_inventory.get("node_count"),
        "main_flow_links": main_inventory.get("link_count"),
        "main_flow_save_image_lanes": len(main_inventory.get("save_image_lanes", [])),
        "qa_gates": len(qa_gates),
        "fallback_order_count": len(fallback_policy.get("fallback_order", [])),
        "runtime_execution_proven": False,
        "ec2_required_now": False
    }

    out_path = root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Wave 15 validation {report['status']}")
    print(f"Image base lanes: {report['image_base_lanes']}")
    print(f"Main Flow SaveImage lanes: {report['main_flow_save_image_lanes']}")
    print(f"JSON files checked: {json_files_checked}")
    print(f"New Python scripts checked: {new_scripts_checked}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
