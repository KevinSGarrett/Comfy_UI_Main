#!/usr/bin/env python3
"""Score a Wave09 environment continuity report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

CRITICAL_CHECKS = {
    "layout_consistency",
    "scale_plausibility",
    "lighting_direction",
    "prop_stability",
    "room_acoustics_match",
}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report_json", type=Path)
    parser.add_argument("--min-score", type=float, default=0.75)
    args = parser.parse_args()

    report = json.loads(args.report_json.read_text(encoding="utf-8"))
    checks = report.get("checks", [])
    if not isinstance(checks, list) or not checks:
        print("FAIL: no checks found")
        return 1

    scores = []
    failures = []
    for check in checks:
        check_id = str(check.get("check_id", "unknown"))
        status = str(check.get("status", ""))
        score = float(check.get("score", 0.0))
        scores.append(score)
        if status == "fail" or (check_id in CRITICAL_CHECKS and score < args.min_score):
            failures.append(f"{check_id}: status={status}, score={score}")

    average = sum(scores) / len(scores)
    result = "PASS" if not failures and average >= args.min_score else "FAIL"
    print(json.dumps({
        "result": result.lower(),
        "average_score": round(average, 4),
        "min_score": args.min_score,
        "failures": failures,
    }, indent=2))
    return 0 if result == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
