#!/usr/bin/env python3
"""Compile a Wave 24 multi-character instance layout contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    src = json.loads(Path(args.input).read_text(encoding="utf-8"))
    out = {
        "contract_version": "wave24.v1",
        "scene_id": src.get("scene_id", "scene_unset"),
        "source_image_id": src.get("source_image_id"),
        "character_count_target": src.get("character_count_target", len(src.get("instances", []))),
        "instances": src.get("instances", []),
        "depth_order": src.get("depth_order", []),
        "region_ownership_maps": src.get("region_ownership_maps", []),
        "mask_factory_evidence": src.get("mask_factory_evidence"),
        "profile_id": src.get("profile_id"),
        "qa_goals": src.get("qa_goals", [
            "correct_character_count",
            "identity_binding_pass",
            "mask_ownership_pass",
            "skeleton_binding_pass",
            "depth_order_pass",
            "no_merged_bodies",
            "no_wrong_character_edits"
        ]),
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
