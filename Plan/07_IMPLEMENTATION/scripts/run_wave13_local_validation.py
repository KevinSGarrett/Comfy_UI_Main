#!/usr/bin/env python3
"""Run Wave13 local validation checks."""

from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path
from typing import Any, Dict, List


def parse_json_files(root: Path) -> Dict[str, Any]:
    errors: List[str] = []
    count = 0
    for path in root.rglob("*.json"):
        count += 1
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{path}: {exc}")
    return {"json_files_checked": count, "json_errors": errors}


def compile_python_files(root: Path) -> Dict[str, Any]:
    errors: List[str] = []
    count = 0
    for path in root.rglob("*.py"):
        count += 1
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            errors.append(f"{path}: {exc}")
    return {"python_files_checked": count, "python_errors": errors}


def validate_optional_contract(path: Path | None) -> Dict[str, Any]:
    if not path:
        return {"contract_checked": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    required = ["contract_id", "scene_id", "required_mask_scales", "person_instances", "promotion_gates"]
    missing = [key for key in required if key not in data]
    return {"contract_checked": True, "contract_path": str(path), "missing_required": missing, "passed": not missing}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--workflow", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    root = args.project_root
    report: Dict[str, Any] = {
        "wave": "13",
        "validation_name": "Ultimate Mask Factory local validation",
        "project_root": str(root),
    }
    report.update(parse_json_files(root))
    report.update(compile_python_files(root))
    report.update(validate_optional_contract(args.contract))

    if args.workflow and args.workflow.exists():
        workflow = json.loads(args.workflow.read_text(encoding="utf-8"))
        report["workflow_checked"] = True
        report["workflow_node_count"] = len(workflow.get("nodes", []))
        report["workflow_link_count"] = len(workflow.get("links", []))
    else:
        report["workflow_checked"] = False

    passed = not report["json_errors"] and not report["python_errors"] and report.get("missing_required", []) == []
    report["passed"] = passed

    text = json.dumps(report, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
