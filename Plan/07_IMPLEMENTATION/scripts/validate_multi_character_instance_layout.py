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


def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_bbox(value: object, idx: int, errors: list[str]) -> None:
    if not isinstance(value, list) or len(value) != 4:
        errors.append(f"instances[{idx}] frame_bbox must be [x,y,width,height]")
        return
    x, y, width, height = value
    if not all(is_number(item) for item in value):
        errors.append(f"instances[{idx}] frame_bbox values must be numeric")
        return
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        errors.append(f"instances[{idx}] frame_bbox has invalid origin or size")
    if x + width > 1.0 or y + height > 1.0:
        errors.append(f"instances[{idx}] frame_bbox exceeds normalized canvas bounds")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    obj = json.loads(Path(args.input).read_text(encoding="utf-8"))
    errors: list[str] = []

    for field in ["contract_version", "scene_id", "character_count_target", "instances"]:
        if field not in obj:
            errors.append(f"missing root field: {field}")

    instances = obj.get("instances", [])
    instance_ids: set[str] = set()
    if not isinstance(instances, list) or not instances:
        errors.append("instances must be a non-empty list")
    else:
        if obj.get("character_count_target") != len(instances):
            errors.append("character_count_target must match number of instances")
        for idx, inst in enumerate(instances):
            if not isinstance(inst, dict):
                errors.append(f"instances[{idx}] must be an object")
                continue
            for field in REQUIRED_INSTANCE_FIELDS:
                if field not in inst:
                    errors.append(f"instances[{idx}] missing field: {field}")
            cid = inst.get("character_instance_id")
            if cid in instance_ids:
                errors.append(f"duplicate character_instance_id: {cid}")
            if cid:
                instance_ids.add(cid)
            validate_bbox(inst.get("frame_bbox"), idx, errors)
            if not isinstance(inst.get("depth_layer"), int):
                errors.append(f"instances[{idx}] depth_layer must be integer")
            if not str(inst.get("person_instance_mask_id", "")).strip():
                errors.append(f"instances[{idx}] person_instance_mask_id must be non-empty")
            if not str(inst.get("region_ownership_map_id", "")).strip():
                errors.append(f"instances[{idx}] region_ownership_map_id must be non-empty")

    depth_order = obj.get("depth_order", [])
    if not isinstance(depth_order, list) or not depth_order:
        errors.append("depth_order must be a non-empty list")
    else:
        depth_ids = [str(item) for item in depth_order]
        if len(depth_ids) != len(set(depth_ids)):
            errors.append("depth_order contains duplicate instance ids")
        missing = sorted(instance_ids.difference(set(depth_ids)))
        extra = sorted(set(depth_ids).difference(instance_ids))
        if missing:
            errors.append(f"depth_order missing instances: {','.join(missing)}")
        if extra:
            errors.append(f"depth_order contains unknown instances: {','.join(extra)}")

    region_maps = obj.get("region_ownership_maps", [])
    if region_maps is not None:
        if not isinstance(region_maps, list):
            errors.append("region_ownership_maps must be a list when supplied")
        else:
            map_ids = {str(item.get("region_ownership_map_id")) for item in region_maps if isinstance(item, dict)}
            for idx, inst in enumerate(instances if isinstance(instances, list) else []):
                if isinstance(inst, dict) and map_ids and str(inst.get("region_ownership_map_id")) not in map_ids:
                    errors.append(f"instances[{idx}] references missing region_ownership_map_id: {inst.get('region_ownership_map_id')}")

    report = {
        "validation_version": "wave24.v1",
        "input": args.input,
        "passed": not errors,
        "errors": errors,
        "instance_count": len(instances) if isinstance(instances, list) else 0,
        "depth_order_count": len(depth_order) if isinstance(depth_order, list) else 0,
        "region_ownership_map_count": len(region_maps) if isinstance(region_maps, list) else 0,
    }
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if errors:
        print("FAIL")
        for err in errors:
            print(f"- {err}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
