#!/usr/bin/env python3
"""Inventory mask-related slots and nodes in a ComfyUI workflow JSON."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


MASK_KEYWORDS = ["mask", "inpaint", "segment", "sam", "birefnet", "bbox", "contact", "fabric"]


def load_workflow(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Workflow must be a JSON object")
    return data


def inventory(workflow: Dict[str, Any]) -> Dict[str, Any]:
    nodes = workflow.get("nodes", [])
    links = workflow.get("links", [])
    type_counts = Counter(n.get("type") for n in nodes if isinstance(n, dict))

    mask_slots: List[Dict[str, Any]] = []
    keyword_nodes: List[Dict[str, Any]] = []
    save_lanes: List[Dict[str, Any]] = []

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_text = json.dumps(node, ensure_ascii=False).lower()
        if any(keyword in node_text for keyword in MASK_KEYWORDS):
            keyword_nodes.append(
                {
                    "node_id": node.get("id"),
                    "node_type": node.get("type"),
                    "title": node.get("title", ""),
                    "mode": node.get("mode"),
                }
            )
        if node.get("type") == "SaveImage":
            values = node.get("widgets_values") or [""]
            save_lanes.append({"node_id": node.get("id"), "output_prefix": values[0]})
        for input_slot in node.get("inputs", []) or []:
            name = str(input_slot.get("name", ""))
            slot_type = str(input_slot.get("type", ""))
            if slot_type == "MASK" or "mask" in name.lower():
                mask_slots.append(
                    {
                        "node_id": node.get("id"),
                        "node_type": node.get("type"),
                        "input_name": name,
                        "slot_type": slot_type,
                        "link": input_slot.get("link"),
                    }
                )

    return {
        "node_count": len(nodes),
        "link_count": len(links),
        "node_type_counts": dict(type_counts),
        "mask_input_slots": mask_slots,
        "mask_keyword_nodes": keyword_nodes,
        "save_image_lanes": save_lanes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    report = inventory(load_workflow(args.workflow))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote workflow mask inventory: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
