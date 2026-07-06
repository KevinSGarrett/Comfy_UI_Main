#!/usr/bin/env python3
"""Validate a Wave 24 multi-character instance layout contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_INSTANCE_FIELDS = [
    "character_instance_id",
    "character_identity_id",
    "person_instance_mask_id",
    "skeleton_id",
    "region_ownership_map_id",
    "frame_bbox",
    "depth_layer",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    obj = json.loads(Path(args.input).read_text(encoding="utf-8"))
    errors: list[str] = []

    for field in ["contract_version", "scene_id", "character_count_target", "instances"]:
        if field not in obj:
            errors.append(f"missing root field: {field}")

    instances = obj.get("instances", [])
    if not isinstance(instances, list) or not instances:
        errors.append("instances must be a non-empty list")
    else:
        if obj.get("character_count_target") != len(instances):
            errors.append("character_count_target must match number of instances")
        seen: set[str] = set()
        for idx, inst in enumerate(instances):
            for field in REQUIRED_INSTANCE_FIELDS:
                if field not in inst:
                    errors.append(f"instances[{idx}] missing field: {field}")
            cid = inst.get("character_instance_id")
            if cid in seen:
                errors.append(f"duplicate character_instance_id: {cid}")
            if cid:
                seen.add(cid)

    if errors:
        print("FAIL")
        for err in errors:
            print(f"- {err}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
