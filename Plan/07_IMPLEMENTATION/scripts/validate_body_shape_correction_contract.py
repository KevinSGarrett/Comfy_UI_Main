#!/usr/bin/env python3
"""Validate a Wave17 body-shape correction contract without external dependencies."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_TOP = [
    "contract_id", "scene_id", "character_id", "source_image", "target_profile",
    "target_regions", "mask_plan", "pass_plan", "qa_goals", "promotion_policy",
]
AUTO_FAIL_FORBIDDEN = {"face_identity", "pose", "camera_crop", "background", "character_count"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_contract(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_TOP:
        if key not in doc:
            errors.append(f"missing top-level key: {key}")

    if doc.get("promotion_policy", {}).get("allows_global_redraw") is not False:
        errors.append("promotion_policy.allows_global_redraw must be false")

    if not doc.get("target_regions"):
        errors.append("target_regions must not be empty")

    masks = doc.get("mask_plan", [])
    if not isinstance(masks, list) or not masks:
        errors.append("mask_plan must contain at least one mask")
    mask_ids = set()
    for idx, mask in enumerate(masks):
        for key in ["mask_id", "character_id", "owner_instance_id", "region_id", "mask_scale", "artifact_path", "feather_px", "protected_exclusions"]:
            if key not in mask:
                errors.append(f"mask_plan[{idx}] missing {key}")
        if mask.get("character_id") != doc.get("character_id"):
            errors.append(f"mask_plan[{idx}] character_id mismatch")
        mask_ids.add(mask.get("mask_id"))

    passes = doc.get("pass_plan", [])
    if not isinstance(passes, list) or not passes:
        errors.append("pass_plan must contain at least one pass")
    for idx, p in enumerate(passes):
        denoise = p.get("denoise")
        if not isinstance(denoise, (int, float)) or denoise < 0 or denoise > 1:
            errors.append(f"pass_plan[{idx}] denoise must be between 0 and 1")
        if denoise and denoise > 0.40:
            errors.append(f"pass_plan[{idx}] denoise is too high for body correction")
        for mid in p.get("masks", []):
            if mid not in mask_ids:
                errors.append(f"pass_plan[{idx}] references unknown mask {mid}")
        if p.get("qa_required") is not True:
            errors.append(f"pass_plan[{idx}] qa_required must be true")
        forbidden = set(p.get("forbidden_changes", []))
        if not AUTO_FAIL_FORBIDDEN.intersection(forbidden):
            errors.append(f"pass_plan[{idx}] should declare protected forbidden changes")

    goals = doc.get("qa_goals", [])
    goal_metrics = {g.get("metric_id") for g in goals}
    for required_metric in ["identity_preservation", "pose_preservation", "target_region_improvement", "mask_edge_blend"]:
        if required_metric not in goal_metrics:
            errors.append(f"missing required QA metric: {required_metric}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract_json")
    args = parser.parse_args()
    doc = load_json(Path(args.contract_json))
    errors = validate_contract(doc)
    if errors:
        print("FAIL: body shape contract validation failed")
        for e in errors:
            print(f"- {e}")
        return 1
    print("PASS: body shape contract validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
