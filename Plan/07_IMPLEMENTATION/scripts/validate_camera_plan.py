#!/usr/bin/env python3
"""Validate a Wave10 camera plan locally before workflow patching or runtime use."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from compile_camera_plan import (
    ALLOWED_CAMERA_ANGLES,
    ALLOWED_LENS_PROFILES,
    ALLOWED_SHOT_SIZES,
    FULL_BODY_REQUIRED_CROP_ANCHORS,
    FULL_BODY_REQUIRED_SUBJECT_ANCHORS,
)


REQUIRED = [
    "camera_plan_id",
    "shot_size",
    "lens_profile",
    "camera_angle",
    "resolution",
    "framing",
    "depth_plan",
    "subjects",
    "qa_goals",
]


def _dimension_valid(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 512 <= value <= 2048 and value % 64 == 0


def validate_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    blocking: List[str] = []
    warnings: List[str] = []

    for field in REQUIRED:
        ok = field in plan and plan[field] not in (None, "", [], {})
        checks.append({"check": f"required_{field}", "pass": ok})
        if not ok:
            blocking.append(f"Missing required field: {field}")

    shot_size = plan.get("shot_size")
    lens_profile = plan.get("lens_profile")
    camera_angle = plan.get("camera_angle")
    for name, value, allowed in (
        ("shot_size", shot_size, ALLOWED_SHOT_SIZES),
        ("lens_profile", lens_profile, ALLOWED_LENS_PROFILES),
        ("camera_angle", camera_angle, ALLOWED_CAMERA_ANGLES),
    ):
        ok = value in allowed
        checks.append({"check": f"known_{name}", "pass": ok, "actual": value})
        if not ok:
            blocking.append(f"Unknown {name}: {value}")

    subjects = plan.get("subjects") or []
    resolution = plan.get("resolution") or {}
    framing = plan.get("framing") or {}
    depth_plan = plan.get("depth_plan") or {}
    width_ok = _dimension_valid(resolution.get("width"))
    height_ok = _dimension_valid(resolution.get("height"))
    checks.extend(
        [
            {"check": "resolution_width_runtime_safe", "pass": width_ok, "actual": resolution.get("width")},
            {"check": "resolution_height_runtime_safe", "pass": height_ok, "actual": resolution.get("height")},
        ]
    )
    if not width_ok:
        blocking.append("Resolution width must be an integer from 512 through 2048 and divisible by 64.")
    if not height_ok:
        blocking.append("Resolution height must be an integer from 512 through 2048 and divisible by 64.")

    if shot_size == "full_body":
        must_not_crop = set(framing.get("must_not_crop", []))
        missing = FULL_BODY_REQUIRED_CROP_ANCHORS.difference(must_not_crop)
        crop_anchors_ok = not missing
        checks.append(
            {
                "check": "full_body_crop_anchors_present",
                "pass": crop_anchors_ok,
                "missing": sorted(missing),
            }
        )
        if missing:
            blocking.append(f"Full-body must_not_crop missing: {', '.join(sorted(missing))}.")
        if framing.get("intentional_crop_allowed") is not False:
            blocking.append("Full-body intentional_crop_allowed must be false.")
        if framing.get("crop_policy") not in {"blocked_unintentional_crop", "full_visible"}:
            blocking.append("Full-body crop policy must block unintentional cropping.")
        for subject in subjects:
            if subject.get("crop_policy") != "full_visible":
                blocking.append(f"Full-body subject {subject.get('subject_id')} must use crop_policy full_visible.")
            subject_missing = FULL_BODY_REQUIRED_SUBJECT_ANCHORS.difference(subject.get("must_show", []))
            if subject_missing:
                blocking.append(
                    f"Full-body subject {subject.get('subject_id')} must_show missing: {', '.join(sorted(subject_missing))}."
                )
        if width_ok and height_ok and resolution["height"] <= resolution["width"]:
            warnings.append("Full-body shot is not portrait-oriented; visual crop review must justify the framing.")

    if len(subjects) > 1:
        for subject in subjects:
            if not subject.get("screen_position"):
                blocking.append(f"Subject {subject.get('subject_id')} missing screen_position.")
            if subject.get("occlusion_allowed") is None:
                blocking.append(f"Subject {subject.get('subject_id')} missing occlusion_allowed.")
        if depth_plan.get("depth_profile") not in {"layered_depth", "deep_focus"}:
            warnings.append("Multi-character camera plans should default to layered_depth or deep_focus.")

    blur = depth_plan.get("background_blur_strength")
    try:
        blur_ok = blur is not None and 0 <= float(blur) <= 1
    except (TypeError, ValueError):
        blur_ok = False
    checks.append({"check": "background_blur_strength_in_range", "pass": blur_ok, "actual": blur})
    if not blur_ok:
        blocking.append("background_blur_strength must be between 0 and 1.")

    instructions = plan.get("workflow_instructions")
    if instructions is not None:
        if not isinstance(instructions, dict):
            blocking.append("workflow_instructions must be an object.")
        else:
            for field in (
                "positive_prompt_camera_module",
                "negative_prompt_crop_guard",
                "latent_resolution",
                "reference_routing_plan",
                "control_plan",
                "save_prefix",
                "qa_goals",
            ):
                if instructions.get(field) in (None, "", [], {}):
                    blocking.append(f"workflow_instructions missing {field}.")
            latent = instructions.get("latent_resolution") or {}
            latent_match = latent.get("width") == resolution.get("width") and latent.get("height") == resolution.get("height")
            checks.append({"check": "latent_resolution_matches_camera_plan", "pass": latent_match})
            if not latent_match:
                blocking.append("workflow_instructions latent resolution does not match camera plan resolution.")
            for route_name in ("reference_routing_plan", "control_plan"):
                route = instructions.get(route_name) or {}
                if route.get("enabled") and route.get("proof_status") != "proven":
                    blocking.append(f"{route_name} is enabled without proof_status proven.")
    else:
        warnings.append("No workflow_instructions found; this plan cannot directly patch a runtime profile.")

    validation = "PASS" if not blocking else "FAIL"
    if validation == "PASS" and warnings:
        validation = "WARN"
    return {
        "camera_plan_id": plan.get("camera_plan_id", "unknown"),
        "validation": validation,
        "checks": checks,
        "blocking_issues": blocking,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--out", required=False)
    args = parser.parse_args()

    plan_path = Path(args.plan)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    report = validate_plan(plan)
    text = json.dumps(report, indent=2) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"Wrote validation report: {out}")
    else:
        print(text)
    return 0 if report["validation"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
