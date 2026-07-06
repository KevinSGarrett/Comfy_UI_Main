#!/usr/bin/env python3
"""Run Wave10 local validation over JSON files and camera example plans."""
from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path
from typing import Any, Dict, List

from validate_camera_plan import validate_plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default="11_RELEASES/WAVE10_LOCAL_VALIDATION_REPORT.json")
    args = parser.parse_args()

    root = Path(args.root)
    report: Dict[str, Any] = {
        "validation": "PASS",
        "json_files_checked": 0,
        "python_files_checked": 0,
        "camera_examples_checked": 0,
        "errors": [],
        "warnings": [],
    }

    for json_path in root.rglob("*.json"):
        try:
            json.loads(json_path.read_text(encoding="utf-8"))
            report["json_files_checked"] += 1
        except Exception as exc:  # noqa: BLE001
            report["errors"].append({"file": str(json_path), "error": str(exc)})

    for py_path in root.rglob("*.py"):
        try:
            py_compile.compile(str(py_path), doraise=True)
            report["python_files_checked"] += 1
        except Exception as exc:  # noqa: BLE001
            report["errors"].append({"file": str(py_path), "error": str(exc)})

    for plan_path in root.glob("09_EXAMPLES/wave10_camera_plan*.json"):
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            validation = validate_plan(plan)
            report["camera_examples_checked"] += 1
            if validation["validation"] == "FAIL":
                report["errors"].append({"file": str(plan_path), "error": validation})
            elif validation["validation"] == "WARN":
                report["warnings"].append({"file": str(plan_path), "warning": validation})
        except Exception as exc:  # noqa: BLE001
            report["errors"].append({"file": str(plan_path), "error": str(exc)})

    if report["errors"]:
        report["validation"] = "FAIL"

    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wave10 local validation: {report['validation']} -> {out}")
    return 0 if report["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
