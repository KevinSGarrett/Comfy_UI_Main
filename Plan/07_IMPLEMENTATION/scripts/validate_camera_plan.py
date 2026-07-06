#!/usr/bin/env python3
"""Validate a Wave10 camera plan locally before workflow patching or EC2 use."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


REQUIRED = ["camera_plan_id", "shot_size", "lens_profile", "camera_angle", "framing", "depth_plan", "subjects", "qa_goals"]


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
    subjects = plan.get("subjects") or []
    resolution = plan.get("resolution") or {}
    framing = plan.get("framing") or {}
    depth_plan = plan.get("depth_plan") or {}

    if shot_size == "full_body":
        must_not_crop = set(framing.get("must_not_crop", []))
        for required in ["head", "hands", "feet"]:
            if required not in must_not_crop:
                warnings.append(f"Full-body camera plan should include {required} in must_not_crop.")
        if resolution.get("height", 0) <= resolution.get("width", 0):
            warnings.append("Full-body shots usually need vertical or 4:5 framing unless explicitly wide/action.")

    if len(subjects) > 1:
        for subject in subjects:
            if not subject.get("screen_position"):
                blocking.append(f"Subject {subject.get('subject_id')} missing screen_position.")
            if subject.get("occlusion_allowed") is None:
                blocking.append(f"Subject {subject.get('subject_id')} missing occlusion_allowed.")
        if depth_plan.get("depth_profile") not in {"layered_depth", "deep_focus"}:
            warnings.append("Multi-character camera plans should default to layered_depth or deep_focus.")

    blur = depth_plan.get("background_blur_strength")
    if blur is not None and not (0 <= float(blur) <= 1):
        blocking.append("background_blur_strength must be between 0 and 1.")

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
