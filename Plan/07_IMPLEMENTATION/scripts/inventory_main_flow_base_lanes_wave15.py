#!/usr/bin/env python3
"""Inventory base generation lanes in a ComfyUI UI workflow JSON."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    path = Path(args.workflow)
    workflow = json.loads(path.read_text(encoding="utf-8"))
    nodes = workflow.get("nodes", [])
    type_counts = collections.Counter(n.get("type") for n in nodes)

    save_lanes = []
    for node in nodes:
        if node.get("type") == "SaveImage":
            widgets = node.get("widgets_values") or []
            save_lanes.append({
                "node_id": node.get("id"),
                "prefix": widgets[0] if widgets else None
            })

    inventory = {
        "workflow_sha256": sha256_file(path),
        "workflow_id": workflow.get("id"),
        "revision": workflow.get("revision"),
        "node_count": len(nodes),
        "link_count": len(workflow.get("links", [])),
        "type_counts": dict(type_counts),
        "save_image_lanes": save_lanes,
        "ksampler_nodes": [n.get("id") for n in nodes if n.get("type") == "KSampler"],
        "checkpoint_loader_nodes": [
            {"node_id": n.get("id"), "widgets": n.get("widgets_values")}
            for n in nodes if n.get("type") == "CheckpointLoaderSimple"
        ],
        "unet_loader_nodes": [
            {"node_id": n.get("id"), "widgets": n.get("widgets_values")}
            for n in nodes if n.get("type") == "UNETLoader"
        ],
        "lora_nodes": sum(1 for n in nodes if "Lora" in str(n.get("type", ""))),
        "disabled_or_catalog_nodes": sum(1 for n in nodes if n.get("mode") == 2)
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
