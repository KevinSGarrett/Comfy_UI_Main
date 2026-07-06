#!/usr/bin/env python3
"""Compile a Wave15 image base generation plan from a route decision.

The compiled plan is intentionally execution-neutral. It says what should run,
what must be patched, and which QA gates are required. It does not run ComfyUI.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def find_lane(registry: List[Dict[str, Any]], lane_id: str) -> Dict[str, Any]:
    for lane in registry:
        if lane.get("lane_id") == lane_id:
            return lane
    raise ValueError(f"Unknown lane_id: {lane_id}")


def compile_plan(request: Dict[str, Any], decision: Dict[str, Any], registry: List[Dict[str, Any]], qa_gates: List[Dict[str, Any]]) -> Dict[str, Any]:
    selected = decision.get("selected_lane_id")
    if not selected:
        return {
            "plan_id": request.get("request_id", "request") + "__base_generation_plan",
            "selected_lane_id": None,
            "engine_family": None,
            "passes": [],
            "qa_gates": [gate["gate_id"] for gate in qa_gates],
            "promotion_allowed": False,
            "blocked_reasons": decision.get("blocked_reasons", [])
        }

    lane = find_lane(registry, selected)
    return {
        "plan_id": request.get("request_id", "request") + "__base_generation_plan",
        "scene_director_plan_id": request.get("scene_director_plan_id"),
        "selected_lane_id": selected,
        "engine_family": lane.get("engine_family"),
        "fallback_lane_ids": decision.get("fallback_lane_ids", []),
        "passes": [
            {
                "pass_id": "base_pass_001",
                "pass_type": "image_base_generation",
                "lane_id": selected,
                "engine_family": lane.get("engine_family"),
                "workflow_template_id": f"{selected}_template",
                "patch_required": True,
                "dry_run_first": True,
                "promotion_allowed": False
            }
        ],
        "required_patch_groups": [
            "positive_prompt",
            "negative_prompt",
            "seed",
            "sampler",
            "latent_resolution",
            "model_assets",
            "lora_stack_profile",
            "save_prefix"
        ],
        "qa_gates": [gate["gate_id"] for gate in qa_gates],
        "promotion_allowed": False,
        "notes": [
            "Base generation plan is not proof of runtime execution.",
            "Every output must be scored before downstream use."
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--decision", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--qa-gates", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    request = load_json(Path(args.request))
    decision = load_json(Path(args.decision))
    registry = load_json(Path(args.registry))
    qa_gates = load_json(Path(args.qa_gates))

    plan = compile_plan(request, decision, registry, qa_gates)
    save_json(Path(args.out), plan)
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
