#!/usr/bin/env python3
"""
Inspect a ComfyUI workflow JSON for engine-significant model nodes and SaveImage lanes.
"""
from __future__ import annotations
import argparse, json, collections
from pathlib import Path

MODEL_NODE_TYPES = {
    "CheckpointLoaderSimple", "UNETLoader", "VAELoader", "CLIPLoader",
    "DualCLIPLoader", "TripleCLIPLoader", "LoraLoader", "ControlNetLoader",
    "UpscaleModelLoader", "IPAdapterModelLoader"
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", required=True)
    args = ap.parse_args()

    data = json.loads(Path(args.workflow).read_text(encoding="utf-8"))
    nodes = data.get("nodes", [])
    type_counts = collections.Counter(n.get("type") for n in nodes)

    model_nodes = []
    save_lanes = []
    for n in nodes:
        t = n.get("type")
        if t in MODEL_NODE_TYPES:
            model_nodes.append({
                "id": n.get("id"),
                "type": t,
                "title": n.get("title"),
                "mode": n.get("mode", 0),
                "widgets_values": n.get("widgets_values", []),
                "properties": n.get("properties", {})
            })
        if t == "SaveImage":
            save_lanes.append({
                "id": n.get("id"),
                "mode": n.get("mode", 0),
                "save_prefix": (n.get("widgets_values") or [""])[0]
            })

    report = {
        "workflow": args.workflow,
        "node_count": len(nodes),
        "link_count": len(data.get("links", [])),
        "type_counts": dict(type_counts),
        "model_node_count": len(model_nodes),
        "save_lanes": save_lanes,
        "model_nodes": model_nodes
    }
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
