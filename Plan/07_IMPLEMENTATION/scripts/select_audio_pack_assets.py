#!/usr/bin/env python3
"""Select deterministic, hash-bound audio assets from a functional JSONL index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def select_assets(index_path: Path, criteria: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    if limit < 1:
        raise ValueError("limit must be positive")
    allowed = {
        "event_type", "material", "role", "intensity_band", "duration_band",
        "attack_characteristic", "sync_class", "license_classification", "loopability",
    }
    unknown = set(criteria) - allowed
    if unknown:
        raise ValueError(f"unsupported criteria: {','.join(sorted(unknown))}")
    selected: list[dict[str, Any]] = []
    with index_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record.get("quality_defects"):
                continue
            if all(record.get(key) == value for key, value in criteria.items()):
                selected.append(record)
    selected.sort(key=lambda item: (item["duration_seconds"] or float("inf"), item["sha256"], item["relative_path"].casefold()))
    return selected[:limit]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True)
    parser.add_argument("--criteria-json")
    parser.add_argument("--criterion", action="append", default=[])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        criteria = json.loads(args.criteria_json) if args.criteria_json else {}
        if not isinstance(criteria, dict):
            raise ValueError("criteria-json must decode to an object")
        for raw in args.criterion:
            if "=" not in raw:
                raise ValueError("criterion must use key=value")
            key, value = raw.split("=", 1)
            if not key or not value:
                raise ValueError("criterion must use non-empty key=value")
            criteria[key] = value
        if not criteria:
            raise ValueError("at least one criterion is required")
        selected = select_assets(Path(args.index), criteria, args.limit)
        output = Path(args.output)
        if output.exists():
            raise ValueError(f"output already exists: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({"criteria": criteria, "count": len(selected), "assets": selected}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps({"status": "PASS", "selected": len(selected)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
