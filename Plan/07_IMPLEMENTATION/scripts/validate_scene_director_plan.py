#!/usr/bin/env python3
"""
validate_scene_director_plan.py

Validate required Wave07 Scene Director plan fields and common structural rules.
This is intentionally lightweight and stdlib-only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_TOP_LEVEL = [
    "plan_id",
    "request_id",
    "director_profile_id",
    "intent_classification",
    "ambiguity_resolution",
    "scene_graph",
    "camera_plan",
    "mask_plan",
    "model_selection_plan",
    "engine_route",
    "pass_plan",
    "qa_goal_plan",
    "promotion_requirements",
    "evidence_requirements",
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_plan(plan: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for field in REQUIRED_TOP_LEVEL:
        if field not in plan:
            errors.append(f"missing top-level field: {field}")

    passes = plan.get("pass_plan", {}).get("passes", [])
    if not isinstance(passes, list) or not passes:
        errors.append("pass_plan.passes must be a non-empty list")
    else:
        for i, p in enumerate(passes):
            for field in ["pass_id", "pass_type", "engine_id", "workflow_module_id", "inputs", "outputs", "qa_goal_ids", "promotion_gate"]:
                if field not in p:
                    errors.append(f"pass {i} missing field: {field}")
            if not p.get("qa_goal_ids"):
                errors.append(f"pass {i} has no qa_goal_ids")

    qa_goals = plan.get("qa_goal_plan", [])
    if not isinstance(qa_goals, list) or not qa_goals:
        errors.append("qa_goal_plan must be a non-empty list")
    else:
        qa_ids = {q.get("qa_goal_id") for q in qa_goals if isinstance(q, dict)}
        for p in passes:
            for qid in p.get("qa_goal_ids", []):
                if qid not in qa_ids:
                    errors.append(f"pass {p.get('pass_id')} references missing qa goal: {qid}")

    if not plan.get("promotion_requirements"):
        errors.append("promotion_requirements cannot be empty")
    if not plan.get("evidence_requirements"):
        errors.append("evidence_requirements cannot be empty")

    route = plan.get("engine_route", {})
    if route.get("cross_engine_policy") != "image_bridge_only_no_latent_or_lora_mixing":
        errors.append("engine_route.cross_engine_policy must enforce image_bridge_only_no_latent_or_lora_mixing")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    args = parser.parse_args()

    plan = load_json(args.plan)
    errors = validate_plan(plan)
    if errors:
        print("FAIL: Scene Director plan validation failed")
        for e in errors:
            print(f"- {e}")
        return 1
    print("PASS: Scene Director plan validates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
