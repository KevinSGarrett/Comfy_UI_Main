#!/usr/bin/env python3
"""Validate a Wave09 Environment Bible or environment registry JSON file."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_ENV_FIELDS = [
    "environment_id",
    "environment_version",
    "display_name",
    "environment_type",
    "room_profile_id",
    "lighting_rig_id",
    "prop_registry_id",
    "material_surface_profile_ids",
    "scale_reference_id",
    "continuity_rules",
]

def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)

def validate_environment_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_ENV_FIELDS:
        if field not in record:
            errors.append(f"missing required environment field: {field}")
    env_id = record.get("environment_id", "")
    if env_id and not str(env_id).startswith("env_"):
        errors.append("environment_id must start with env_")
    if not isinstance(record.get("material_surface_profile_ids", []), list):
        errors.append("material_surface_profile_ids must be a list")
    if not isinstance(record.get("continuity_rules", {}), dict):
        errors.append("continuity_rules must be an object")
    return errors

def extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and "environments" in payload:
        return [x for x in payload["environments"] if isinstance(x, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path", type=Path)
    args = parser.parse_args()

    payload = load_json(args.json_path)
    records = extract_records(payload)
    if not records:
        print("FAIL: no environment records found")
        return 1

    all_errors: list[str] = []
    seen_ids: set[str] = set()
    for idx, record in enumerate(records):
        env_id = str(record.get("environment_id", f"index_{idx}"))
        key = f"{env_id}:{record.get('environment_version', '')}"
        if key in seen_ids:
            all_errors.append(f"duplicate environment/version: {key}")
        seen_ids.add(key)
        for err in validate_environment_record(record):
            all_errors.append(f"{key}: {err}")

    if all_errors:
        print("FAIL")
        for error in all_errors:
            print(f"- {error}")
        return 1

    print(f"PASS: validated {len(records)} environment record(s)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
