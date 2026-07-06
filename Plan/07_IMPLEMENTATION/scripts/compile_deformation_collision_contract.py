#!/usr/bin/env python3
"""Compile a Wave 23 deformation/collision contract."""
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
        "contract_version": "wave23.v1",
        "scene_id": src.get("scene_id"),
        "source_image_id": src.get("source_image_id"),
        "deformation_events": src.get("deformation_events", []),
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
