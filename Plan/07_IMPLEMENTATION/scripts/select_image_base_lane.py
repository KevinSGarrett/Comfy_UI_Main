#!/usr/bin/env python3
"""Select a Wave15 image base generation lane from request + lane registry.

Usage:
  python select_image_base_lane.py --request request.json --registry wave15_image_base_lane_registry.json --out decision.json
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


def requested_family(request: Dict[str, Any]) -> str | None:
    prefs = request.get("routing_preferences", {})
    for key in ("required_engine_family", "preferred_engine_family", "engine_family"):
        value = prefs.get(key)
        if value:
            return str(value).lower()
    return None


def select_lane(request: Dict[str, Any], registry: List[Dict[str, Any]]) -> Dict[str, Any]:
    family = requested_family(request)
    proven_only = bool(request.get("routing_preferences", {}).get("proven_only", True))
    allow_planned = bool(request.get("routing_preferences", {}).get("allow_planned", False))

    candidates = sorted(registry, key=lambda row: row.get("default_priority", 999))
    blocked = []

    if family:
        family_candidates = [row for row in candidates if row.get("engine_family") == family]
        if family_candidates:
            candidates = family_candidates

    for lane in candidates:
        status = lane.get("status", "")
        if proven_only and "requires_runtime_proof" in status and not allow_planned:
            blocked.append({
                "lane_id": lane.get("lane_id"),
                "reason": "runtime_proof_required_and_allow_planned_false"
            })
            continue
        if lane.get("promotion_state") == "not_promoted" and proven_only and not allow_planned:
            blocked.append({
                "lane_id": lane.get("lane_id"),
                "reason": "not_promoted_and_proven_only"
            })
            continue
        return {
            "decision_id": request.get("request_id", "request") + "__base_lane_decision",
            "selected_lane_id": lane["lane_id"],
            "engine_family": lane["engine_family"],
            "decision_reasons": [
                "matched_requested_family" if family else "selected_by_default_priority",
                "planned_lanes_allowed" if allow_planned else "proven_or_ready_to_verify_preferred"
            ],
            "fallback_lane_ids": [
                row["lane_id"] for row in candidates if row["lane_id"] != lane["lane_id"]
            ],
            "blocked_reasons": blocked,
            "promotion_allowed": False
        }

    return {
        "decision_id": request.get("request_id", "request") + "__base_lane_decision",
        "selected_lane_id": None,
        "engine_family": None,
        "decision_reasons": [],
        "fallback_lane_ids": [],
        "blocked_reasons": blocked + [{"reason": "no_selectable_lane"}],
        "promotion_allowed": False
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    request = load_json(Path(args.request))
    registry = load_json(Path(args.registry))
    decision = select_lane(request, registry)
    save_json(Path(args.out), decision)
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
