#!/usr/bin/env python3
"""Validate a Wave15 image base generation plan with lightweight stdlib checks."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_FIELDS = ["plan_id", "selected_lane_id", "engine_family", "passes", "qa_gates", "promotion_allowed"]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(plan: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for field in REQUIRED_FIELDS:
        if field not in plan:
            errors.append(f"missing_required_field:{field}")

    if plan.get("promotion_allowed") is not False:
        errors.append("promotion_allowed_must_be_false_before_runtime_evidence")

    passes = plan.get("passes", [])
    if plan.get("selected_lane_id") and not passes:
        errors.append("selected_lane_requires_at_least_one_pass")

    for idx, item in enumerate(passes):
        for field in ("pass_id", "pass_type", "lane_id", "engine_family", "workflow_template_id"):
            if field not in item:
                errors.append(f"pass_{idx}_missing:{field}")
        if item.get("dry_run_first") is not True:
            errors.append(f"pass_{idx}_dry_run_first_must_be_true")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    args = parser.parse_args()

    plan = load_json(Path(args.plan))
    errors = validate(plan)

    if errors:
        print("Wave15 base generation plan validation FAILED")
        for err in errors:
            print(f"- {err}")
        return 1

    print("Wave15 base generation plan validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
