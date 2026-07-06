#!/usr/bin/env python3
"""Validate a Wave 11 control-map plan JSON at a practical level."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_TOP = ["plan_id", "scene_plan_id", "engine_family", "control_maps", "promotion_policy"]
REQUIRED_MAP = ["map_id", "type", "source", "output", "strength"]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--allow-missing-runtime-files", action="store_true")
    args = parser.parse_args()

    plan_path = Path(args.plan)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    errors = []

    for key in REQUIRED_TOP:
        if key not in plan:
            errors.append(f"Missing top-level key: {key}")

    for i, m in enumerate(plan.get("control_maps", [])):
        for key in REQUIRED_MAP:
            if key not in m:
                errors.append(f"control_maps[{i}] missing {key}")
        if not args.allow_missing_runtime_files:
            for key in ["source", "output"]:
                p = Path(str(m.get(key, "")))
                if p and not p.exists():
                    errors.append(f"control_maps[{i}] {key} file does not exist: {p}")

    status = "PASS" if not errors else "FAIL"
    print(json.dumps({"status": status, "errors": errors}, indent=2))
    return 0 if not errors else 2

if __name__ == "__main__":
    raise SystemExit(main())
