#!/usr/bin/env python3
"""Validate a Wave 23 deformation/collision contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_EVENT_FIELDS = [
    "event_id",
    "contact_edge_id",
    "deformation_mode",
    "source_owner_id",
    "target_owner_id",
    "target_material_profile_id",
    "mask_bundle_id",
    "pass_sequence",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    obj = json.loads(Path(args.input).read_text(encoding="utf-8"))
    errors: list[str] = []

    if "contract_version" not in obj:
        errors.append("missing contract_version")
    events = obj.get("deformation_events", [])
    if not isinstance(events, list) or not events:
        errors.append("deformation_events must be a non-empty list")
    else:
        for idx, event in enumerate(events):
            for field in REQUIRED_EVENT_FIELDS:
                if field not in event:
                    errors.append(f"event[{idx}] missing field: {field}")

    if errors:
        print("FAIL")
        for err in errors:
            print(f"- {err}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
