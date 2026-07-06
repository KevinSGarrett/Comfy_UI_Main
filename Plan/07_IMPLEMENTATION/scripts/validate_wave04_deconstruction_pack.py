#!/usr/bin/env python3
"""
validate_wave04_deconstruction_pack.py

Validates the Wave 04 deconstruction artifacts.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


REQUIRED_FILES = [
    "01_CURRENT_SYSTEM_REVIEW/WAVE04_MAIN_FLOW_DECONSTRUCTION_REPORT.md",
    "01_CURRENT_SYSTEM_REVIEW/WAVE04_ACTIVE_RUNTIME_LANES.md",
    "02_TARGET_ARCHITECTURE/WAVE04_MODULE_EXTRACTION_PLAN.md",
    "06_QA_TESTING/WAVE04_MAIN_FLOW_DECONSTRUCTION_QA_GATES.md",
    "07_IMPLEMENTATION/WAVE04_MAIN_FLOW_FIX_UPDATE_CONNECT_IMPROVE_LIST.md",
    "07_IMPLEMENTATION/scripts/deconstruct_main_flow_wave04.py",
    "07_IMPLEMENTATION/templates/powershell/Run-Wave04-MainFlowDeconstruction.ps1",
    "08_SCHEMAS/main_flow_node_classification.schema.json",
    "08_SCHEMAS/main_flow_runtime_lane.schema.json",
    "08_SCHEMAS/main_flow_deconstruction_summary.schema.json",
    "10_REGISTRIES/main_flow_wave04_deconstruction_summary.json",
    "10_REGISTRIES/main_flow_wave04_runtime_lanes.json",
    "10_REGISTRIES/main_flow_wave04_node_classification.json",
    "10_REGISTRIES/main_flow_wave04_note_boundaries.json",
    "10_REGISTRIES/main_flow_wave04_lora_catalog_inventory_raw.json",
    "11_RELEASES/WAVE04_VALIDATION_REPORT.json",
]


def load_json(root: Path, rel: str):
    path = root / rel
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    failures = []

    for rel in REQUIRED_FILES:
        path = root / rel
        if not path.exists() or path.stat().st_size == 0:
            failures.append(f"missing_or_empty:{rel}")

    try:
        summary = load_json(root, "10_REGISTRIES/main_flow_wave04_deconstruction_summary.json")
        if summary.get("node_count", 0) <= 0:
            failures.append("node_count_not_positive")
        if summary.get("save_image_lanes", 0) <= 0:
            failures.append("save_image_lanes_not_positive")
        if summary.get("lora_catalog_nodes", 0) <= 0:
            failures.append("lora_catalog_nodes_not_positive")
    except Exception as exc:
        failures.append(f"summary_json_error:{exc}")

    try:
        lanes = load_json(root, "10_REGISTRIES/main_flow_wave04_runtime_lanes.json")
        if len(lanes) != 8:
            failures.append(f"expected_8_runtime_lanes_found_{len(lanes)}")
    except Exception as exc:
        failures.append(f"runtime_lanes_json_error:{exc}")

    try:
        notes = load_json(root, "10_REGISTRIES/main_flow_wave04_note_boundaries.json")
        if len(notes) != 13:
            failures.append(f"expected_13_note_boundaries_found_{len(notes)}")
    except Exception as exc:
        failures.append(f"note_boundaries_json_error:{exc}")

    try:
        catalog = load_json(root, "10_REGISTRIES/main_flow_wave04_lora_catalog_inventory_raw.json")
        if len(catalog) != 274:
            failures.append(f"expected_274_lora_catalog_nodes_found_{len(catalog)}")
        if any(item.get("mode") != 2 for item in catalog):
            failures.append("catalog_contains_non_mode2_node")
    except Exception as exc:
        failures.append(f"catalog_json_error:{exc}")

    print(json.dumps({"status": "PASS" if not failures else "FAIL", "failures": failures}, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
