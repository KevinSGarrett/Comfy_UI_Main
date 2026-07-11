#!/usr/bin/env python3
"""Score metadata-level framing evidence before mandatory visual camera QA."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def score(plan: Dict[str, Any], evidence: Dict[str, Any] | None = None) -> Dict[str, Any]:
    evidence = evidence or {}
    score_value = 100
    issues = []
    checks = []
    shot = plan.get("shot_size")
    resolution = plan.get("resolution", {})
    width = int(resolution.get("width", evidence.get("width", 0)) or 0)
    height = int(resolution.get("height", evidence.get("height", 0)) or 0)

    if shot == "full_body" and height <= width:
        score_value -= 15
        issues.append("Full-body shot is not vertical/tall; check crop risk.")
    if shot in {"wide_shot", "two_shot", "group_shot"} and width < height:
        score_value -= 10
        issues.append("Wide/two/group shot is vertical; verify this is intentional.")
    if len(plan.get("subjects", [])) > 1 and plan.get("depth_plan", {}).get("depth_profile") not in {
        "layered_depth",
        "deep_focus",
    }:
        score_value -= 15
        issues.append("Multi-character scene is not using layered/deep focus.")
    if "no_unintentional_crop" not in plan.get("qa_goals", []):
        score_value -= 10
        issues.append("No explicit crop QA goal found.")

    instructions = plan.get("workflow_instructions") or {}
    crop_guard = str(instructions.get("negative_prompt_crop_guard", "")).lower()
    required_guard_terms = {"cropped head", "cropped hands", "cropped feet"} if shot == "full_body" else {"unintentional crop"}
    guard_ok = all(term in crop_guard for term in required_guard_terms)
    checks.append({"check": "negative_crop_guard_present", "pass": guard_ok})
    if not guard_ok:
        score_value -= 20
        issues.append("Compiled negative crop guard is missing required shot-specific terms.")

    profile = evidence.get("profile") or evidence.get("compiled_profile") or {}
    profile_resolution = ((profile.get("request_patch_values") or {}).get("latent_resolution") or {}) if isinstance(profile, dict) else {}
    if profile_resolution:
        resolution_match = profile_resolution.get("width") == width and profile_resolution.get("height") == height
        checks.append({"check": "profile_resolution_matches_plan", "pass": resolution_match})
        if not resolution_match:
            score_value -= 25
            issues.append("Compiled profile latent resolution does not match camera plan resolution.")

    reference_route = instructions.get("reference_routing_plan") or {}
    control_plan = instructions.get("control_plan") or {}
    for name, route in (("reference", reference_route), ("control", control_plan)):
        proof_ok = not route.get("enabled") or route.get("proof_status") == "proven"
        checks.append({"check": f"{name}_claim_proof_valid", "pass": proof_ok})
        if not proof_ok:
            score_value -= 30
            issues.append(f"{name.title()} route is enabled without explicit proven status.")

    return {
        "camera_plan_id": plan.get("camera_plan_id", "unknown"),
        "metadata_score": max(score_value, 0),
        "checks": checks,
        "issues": issues,
        "requires_visual_qa": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--evidence", required=False)
    parser.add_argument("--out", required=False)
    args = parser.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8")) if args.evidence else {}
    result = score(plan, evidence)
    text = json.dumps(result, indent=2) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
