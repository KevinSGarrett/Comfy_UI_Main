#!/usr/bin/env python3
"""
Wave 05 pack validator.

Validates Wave 05 registries and verifies App Mode/module/subgraph planning files exist.
This is static validation only. It does not claim runtime proof.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED = [
    "10_REGISTRIES/wave05_module_catalog.json",
    "10_REGISTRIES/wave05_app_mode_control_surface.json",
    "10_REGISTRIES/wave05_workflow_template_contracts.json",
    "10_REGISTRIES/wave05_module_extraction_map.json",
    "02_TARGET_ARCHITECTURE/WAVE05_WORKFLOW_MODULES_SUBGRAPHS_APP_MODE_ARCHITECTURE.md",
    "02_TARGET_ARCHITECTURE/WAVE05_APP_MODE_ORCHESTRATOR_BOUNDARY.md",
    "06_QA_TESTING/WAVE05_MODULE_SUBGRAPH_APPMODE_QA_GATES.md",
]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-root", default=".")
    args = parser.parse_args()
    root = Path(args.pack_root)

    missing = [p for p in REQUIRED if not (root / p).exists()]
    if missing:
        raise SystemExit(f"Missing required Wave 05 files: {missing}")

    module_catalog = read_json(root / "10_REGISTRIES/wave05_module_catalog.json")
    app_surface = read_json(root / "10_REGISTRIES/wave05_app_mode_control_surface.json")
    template_contracts = read_json(root / "10_REGISTRIES/wave05_workflow_template_contracts.json")
    extraction_map = read_json(root / "10_REGISTRIES/wave05_module_extraction_map.json")

    if not isinstance(module_catalog, list) or len(module_catalog) < 10:
        raise SystemExit("Module catalog is too small or invalid.")

    module_ids = {m["module_id"] for m in module_catalog}
    template_module_ids = {t["module_id"] for t in template_contracts}
    missing_templates = sorted(module_ids - template_module_ids)
    if missing_templates:
        raise SystemExit(f"Missing template contracts for modules: {missing_templates}")

    required_groups = {
        "project_runtime", "output_mode", "scene_environment", "characters",
        "camera_framing", "engine_and_modules", "qa_promotion"
    }
    actual_groups = {g["group_id"] for g in app_surface.get("control_groups", [])}
    if not required_groups.issubset(actual_groups):
        raise SystemExit(f"App Mode controls missing groups: {sorted(required_groups - actual_groups)}")

    hidden = set(app_surface.get("hidden_or_advanced_only", []))
    required_hidden = {"raw_model_file_paths", "raw_lora_file_paths", "api_tokens"}
    if not required_hidden.issubset(hidden):
        raise SystemExit("App Mode hidden controls do not include required sensitive internals.")

    if extraction_map.get("wave05_summary", {}).get("save_lanes", 0) < 1:
        raise SystemExit("Extraction map has no SaveImage lanes.")

    print("Wave 05 validation PASS")
    print(f"Modules: {len(module_catalog)}")
    print(f"App control groups: {len(app_surface.get('control_groups', []))}")
    print(f"Workflow template contracts: {len(template_contracts)}")
    print("Runtime proof: REQUIRED LATER")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
