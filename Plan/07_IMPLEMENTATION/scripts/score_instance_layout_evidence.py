#!/usr/bin/env python3
"""Score Wave 24 multi-character instance-layout evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


CHECK_KEYS = [
    "character_count_pass",
    "identity_binding_pass",
    "mask_ownership_pass",
    "skeleton_binding_pass",
    "region_ownership_pass",
    "depth_order_pass",
    "frame_placement_pass",
    "no_merged_body_pass",
    "wrong_character_edit_blocked",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    raw_checks = data.get("checks", {})
    checks = {key: bool(raw_checks.get(key)) for key in CHECK_KEYS}
    score = sum(1 for value in checks.values() if value) / len(CHECK_KEYS)
    report = {
        "evidence_version": "wave24.v1",
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
