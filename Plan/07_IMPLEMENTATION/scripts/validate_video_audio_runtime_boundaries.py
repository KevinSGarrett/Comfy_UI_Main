#!/usr/bin/env python3
"""Validate that video/audio are in scope but not falsely promoted from an image-only Main Flow."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-flow", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    workflow = json.loads(args.main_flow.read_text(encoding="utf-8"))
    nodes = workflow.get("nodes", [])
    notes = []
    save_lanes = []
    for node in nodes:
        node_type = node.get("type")
        values = node.get("widgets_values") or []
        if node_type == "Note" and values:
            notes.append(str(values[0]))
        if node_type == "SaveImage" and values:
            save_lanes.append(str(values[0]))

    video_audio_notes = [n for n in notes if "video" in n.lower() or "audio" in n.lower()]
    has_video_audio_boundary_note = any("separate runtime lanes" in n.lower() for n in video_audio_notes)
    has_only_image_save_lanes = all("Main_Flow/" in x for x in save_lanes)

    result = {
        "video_in_scope": True,
        "audio_in_scope": True,
        "main_flow_save_image_lanes": save_lanes,
        "video_audio_boundary_notes": video_audio_notes,
        "current_main_flow_proves_video_runtime": False,
        "current_main_flow_proves_audio_runtime": False,
        "boundary_note_found": has_video_audio_boundary_note,
        "image_save_lanes_found": has_only_image_save_lanes,
        "promotion_status": "blocked_missing_runtime_proof",
        "explanation": "Video/audio are in scope, but this workflow is treated as an image Main Flow unless separate video/audio modules and output evidence are provided."
    }

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if has_video_audio_boundary_note else 1

if __name__ == "__main__":
    raise SystemExit(main())
