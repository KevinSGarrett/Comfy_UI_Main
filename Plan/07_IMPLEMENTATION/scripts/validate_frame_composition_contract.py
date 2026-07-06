#!/usr/bin/env python3
"""Validate required fields in a Wave12 frame composition contract."""
import argparse
import json
import sys
from pathlib import Path

REQUIRED = ["contract_id", "expected_character_count", "body_visibility_profile", "crop_boundary_policy", "no_merged_bodies_required", "character_slots"]

def validate(contract: dict) -> list[str]:
    errors = []
    for key in REQUIRED:
        if key not in contract:
            errors.append(f"missing required field: {key}")
    count = contract.get("expected_character_count")
    slots = contract.get("character_slots", [])
    if isinstance(count, int) and isinstance(slots, list) and len(slots) != count:
        errors.append(f"character_slots length {len(slots)} does not match expected_character_count {count}")
    crop = contract.get("crop_boundary_policy", {})
    if not isinstance(crop, dict):
        errors.append("crop_boundary_policy must be object")
    else:
        if "safe_margin_ratio" not in crop:
            errors.append("crop_boundary_policy.safe_margin_ratio missing")
        if "forbidden_crop_points" not in crop:
            errors.append("crop_boundary_policy.forbidden_crop_points missing")
    return errors

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("contract")
    args = ap.parse_args()
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    errors = validate(contract)
    if errors:
        print("FAIL")
        for e in errors:
            print("-", e)
        sys.exit(1)
    print("PASS")

if __name__ == "__main__":
    main()
