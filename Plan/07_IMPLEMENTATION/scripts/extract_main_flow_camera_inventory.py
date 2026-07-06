#!/usr/bin/env python3
"""Extract camera/framing inventory signals from a ComfyUI workflow JSON."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict


def extract(workflow: Dict[str, Any]) -> Dict[str, Any]:
    nodes = workflow.get("nodes", [])
    links = workflow.get("links", [])
    loras = [n for n in nodes if n.get("type") == "LoraLoader"]
    latent_nodes = [n for n in nodes if n.get("type") in {"EmptyLatentImage", "EmptySD3LatentImage"}]
    save_nodes = [n for n in nodes if n.get("type") == "SaveImage"]
    notes = [n for n in nodes if n.get("type") == "Note"]
    controlnet_nodes = [n for n in nodes if "ControlNet" in str(n.get("type"))]
    ipadapter_nodes = [n for n in nodes if "IPAdapter" in str(n.get("type"))]

    camera_re = re.compile(r"camera|pose|pov|view|angle|front|behind|side|close", re.I)
    camera_loras = []
    for node in loras:
        props = node.get("properties") or {}
        haystack = " ".join([str(node.get("title", "")), str(props.get("category", "")), str(props.get("scene_role", "")), " ".join(map(str, node.get("widgets_values", [])))])
        if camera_re.search(haystack):
            camera_loras.append({
                "node_id": node.get("id"),
                "title": node.get("title"),
                "engine": props.get("engine"),
                "category": props.get("category"),
                "scene_role": props.get("scene_role"),
                "already_active_in_main_chain": props.get("already_active_in_main_chain"),
                "disabled_by_default": props.get("disabled_by_default"),
            })

    return {
        "node_count": len(nodes),
        "link_count": len(links),
        "save_image_lanes": [((n.get("widgets_values") or [""])[0]) for n in save_nodes],
        "latent_nodes": [
            {"node_id": n.get("id"), "type": n.get("type"), "widgets_values": n.get("widgets_values", [])}
            for n in latent_nodes
        ],
        "controlnet_node_count": len(controlnet_nodes),
        "ipadapter_node_count": len(ipadapter_nodes),
        "note_count": len(notes),
        "lora_node_count": len(loras),
        "camera_related_lora_count": len(camera_loras),
        "camera_related_loras": camera_loras,
        "lora_category_counts": dict(Counter((n.get("properties") or {}).get("category", "") for n in loras)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    workflow = json.loads(Path(args.workflow).read_text(encoding="utf-8"))
    inventory = extract(workflow)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote camera inventory: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
