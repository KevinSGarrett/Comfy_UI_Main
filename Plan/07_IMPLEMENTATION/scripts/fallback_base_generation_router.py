#!/usr/bin/env python3
"""Pick the next fallback image base lane after a Wave15 failure."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", required=True)
    parser.add_argument("--failed-lanes", nargs="*", default=[])
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    policy = load_json(Path(args.policy))
    failed = set(args.failed_lanes)
    next_lane = None
    for lane in policy.get("fallback_order", []):
        if lane not in failed:
            next_lane = lane
            break

    decision = {
        "fallback_decision_id": "wave15_next_fallback_decision",
        "failed_lanes": sorted(failed),
        "next_lane_id": next_lane,
        "hard_stop": next_lane is None,
        "reason": "next_available_lane" if next_lane else "all_fallback_lanes_exhausted"
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0 if next_lane else 1


if __name__ == "__main__":
    raise SystemExit(main())
