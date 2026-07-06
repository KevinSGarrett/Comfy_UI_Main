#!/usr/bin/env python3
"""Score Wave 23 deformation evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


CHECK_KEYS = [
    "ownership_pass",
    "mask_alignment_pass",
    "deformation_intent_pass",
    "contact_boundary_realism_pass",
    "anatomy_preservation_pass",
    "texture_continuity_pass",
    "identity_pose_preservation_pass",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    raw_checks = data.get("checks", {})
    checks = {key: bool(raw_checks.get(key)) for key in CHECK_KEYS}
    score = sum(1 for v in checks.values() if v) / len(CHECK_KEYS)
    report = {
        "evidence_version": "wave23.v1",
        "event_id": data.get("event_id"),
        "checks": checks,
        "score": round(score, 4),
        "pass": score >= 0.9 and all(checks.values()),
        "failure_flags": data.get("failure_flags", []),
    }
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
