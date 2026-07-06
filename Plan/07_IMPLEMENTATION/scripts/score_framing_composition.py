#!/usr/bin/env python3
"""Score basic framing/composition evidence from a camera plan and optional image metadata.

This is not visual QA. It is a local metadata/evidence check that prepares the output
for later visual review by a vision model or human reviewer.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def score(plan: Dict[str, Any], evidence: Dict[str, Any] | None = None) -> Dict[str, Any]:
    evidence = evidence or {}
    score_value = 100
    issues = []
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
    if len(plan.get("subjects", [])) > 1 and plan.get("depth_plan", {}).get("depth_profile") not in {"layered_depth", "deep_focus"}:
        score_value -= 15
        issues.append("Multi-character scene is not using layered/deep focus.")
    if "no_unintentional_crop" not in plan.get("qa_goals", []):
        score_value -= 10
        issues.append("No explicit crop QA goal found.")

    return {
        "camera_plan_id": plan.get("camera_plan_id", "unknown"),
        "metadata_score": max(score_value, 0),
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
