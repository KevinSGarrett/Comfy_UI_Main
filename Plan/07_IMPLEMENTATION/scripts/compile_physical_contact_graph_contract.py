#!/usr/bin/env python3
"""Compile a Wave 22 physical contact graph contract."""
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
    edges = src.get("contact_edges", [])
    out = {
        "contract_version": "wave22.v1",
        "contact_graph_id": src.get("contact_graph_id", "contact_graph_unset"),
        "scene_id": src.get("scene_id"),
        "source_image_id": src.get("source_image_id"),
        "contact_edges": edges,
        "qa_goals": src.get("qa_goals", [
            "source_target_ownership",
            "pressure_intensity_valid",
            "occlusion_valid",
            "duration_valid",
            "audio_force_valid",
            "preservation_pass"
        ]),
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
