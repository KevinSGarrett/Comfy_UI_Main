#!/usr/bin/env python3
"""Validate the Wave10 cumulative package."""
from __future__ import annotations

import json
import py_compile
from pathlib import Path


REQUIRED_FILES = [
    "PROJECT_MANIFEST.json",
    "README.md",
    "00_PROJECT_CONTROL/WAVE10_DELIVERY_REPORT.md",
    "02_TARGET_ARCHITECTURE/WAVE10_CAMERA_LENS_FRAMING_ARCHITECTURE.md",
    "08_SCHEMAS/camera_plan.schema.json",
    "10_REGISTRIES/wave10_camera_lens_registry.json",
    "10_REGISTRIES/wave10_shot_size_taxonomy.json",
    "10_REGISTRIES/wave10_main_flow_camera_inventory.json",
    "11_RELEASES/WAVE10_VALIDATION_REPORT.json",
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = []
    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            errors.append(f"Missing required file: {rel}")

    json_count = 0
    for path in root.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
            json_count += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Invalid JSON: {path.relative_to(root)}: {exc}")

    py_count = 0
    for path in root.rglob("*.py"):
        try:
            py_compile.compile(str(path), doraise=True)
            py_count += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Invalid Python: {path.relative_to(root)}: {exc}")

    report = {
        "validation": "PASS" if not errors else "FAIL",
        "json_files_checked": json_count,
        "python_scripts_checked": py_count,
        "errors": errors,
    }
    out = root / "11_RELEASES" / "WAVE10_PACK_SELF_VALIDATION.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
