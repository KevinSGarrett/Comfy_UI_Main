#!/usr/bin/env python3
"""Inventory a ComfyUI workflow for Wave16 refine/bridge hooks."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict


def inventory(path: Path) -> Dict[str, Any]:
    workflow = json.loads(path.read_text(encoding="utf-8"))
    nodes = workflow.get("nodes", [])
    type_counts = Counter(n.get("type") for n in nodes)
    ksamplers = []
    masks = []
    saves = []
    for n in nodes:
        if n.get("type") == "KSampler":
            widgets = n.get("widgets_values", [])
            ksamplers.append({
                "node_id": n.get("id"),
                "steps": widgets[2] if len(widgets) > 2 else None,
                "cfg": widgets[3] if len(widgets) > 3 else None,
                "denoise": widgets[6] if len(widgets) > 6 else None,
            })
        if n.get("type") == "SaveImage":
            widgets = n.get("widgets_values", [])
            saves.append({"node_id": n.get("id"), "prefix": widgets[0] if widgets else ""})
        for inp in n.get("inputs", []) or []:
            if inp.get("type") == "MASK":
                masks.append({"node_id": n.get("id"), "node_type": n.get("type"), "input_name": inp.get("name"), "linked": inp.get("link") is not None})
    return {
        "workflow_id": workflow.get("id"),
        "nodes": len(nodes),
        "links": len(workflow.get("links", [])),
        "type_counts": dict(type_counts),
        "save_lanes": saves,
        "ksamplers": ksamplers,
        "low_denoise_ksamplers": [k for k in ksamplers if isinstance(k.get("denoise"), (int, float)) and k["denoise"] < 0.5],
        "mask_inputs": masks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = inventory(args.workflow)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
