#!/usr/bin/env python3
"""Validate a Wave 22 physical contact graph contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_EDGE_FIELDS = [
    "edge_id",
    "source_owner_id",
    "source_region_id",
    "target_owner_id",
    "target_region_id",
    "contact_edge_type",
    "pressure",
    "intensity",
    "occlusion",
    "duration",
    "audio_force_class",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    obj = json.loads(Path(args.input).read_text(encoding="utf-8"))
    errors: list[str] = []

    for key in ["contract_version", "contact_graph_id", "contact_edges"]:
        if key not in obj:
            errors.append(f"missing root field: {key}")

    edges = obj.get("contact_edges", [])
    if not isinstance(edges, list) or not edges:
        errors.append("contact_edges must be a non-empty list")
    else:
        for idx, edge in enumerate(edges):
            missing = [key for key in REQUIRED_EDGE_FIELDS if key not in edge]
            for key in missing:
                errors.append(f"edge[{idx}] missing field: {key}")

    if errors:
        print("FAIL")
        for err in errors:
            print(f"- {err}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
