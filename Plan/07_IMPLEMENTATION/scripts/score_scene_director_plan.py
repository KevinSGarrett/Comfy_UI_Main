#!/usr/bin/env python3
"""
score_scene_director_plan.py

Scores a Wave07 Scene Director plan for completeness. This does not determine
creative quality or production promotion; it only checks planning completeness.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


WEIGHTS = {
    "intent_classification": 10,
    "scene_graph": 15,
    "camera_plan": 12,
    "mask_plan": 10,
    "model_selection_plan": 12,
    "engine_route": 10,
    "pass_plan": 15,
    "qa_goal_plan": 12,
    "promotion_requirements": 7,
    "evidence_requirements": 7,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))

    score = 0
    detail = {}
    for field, weight in WEIGHTS.items():
        value = plan.get(field)
        ok = bool(value)
        if field == "pass_plan":
            ok = bool(value and value.get("passes"))
        if field == "qa_goal_plan":
            ok = bool(value and isinstance(value, list))
        detail[field] = {"present": ok, "weight": weight}
        if ok:
            score += weight

    result = {"score": score, "max_score": sum(WEIGHTS.values()), "detail": detail}
    print(json.dumps(result, indent=2))
    return 0 if score >= 80 else 1


if __name__ == "__main__":
    raise SystemExit(main())
