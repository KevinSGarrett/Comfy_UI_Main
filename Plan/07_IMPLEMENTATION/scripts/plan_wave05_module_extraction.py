#!/usr/bin/env python3
"""
Wave 05 module extraction planner.

This script reads a ComfyUI workflow JSON, finds SaveImage terminal lanes, computes
upstream nodes for each lane, and writes a module extraction map. It does not modify
the workflow and does not start ComfyUI.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_link_index(links: list[Any]) -> dict[int, list[Any]]:
    link_by_id: dict[int, list[Any]] = {}
    for link in links:
        if isinstance(link, list) and len(link) >= 6:
            link_by_id[int(link[0])] = link
    return link_by_id


def upstream_nodes(start_id: int, node_by_id: dict[int, dict[str, Any]], link_by_id: dict[int, list[Any]]) -> set[int]:
    seen: set[int] = set()
    stack = [start_id]
    while stack:
        node_id = stack.pop()
        if node_id in seen:
            continue
        seen.add(node_id)
        node = node_by_id.get(node_id)
        if not node:
            continue
        for inp in node.get("inputs", []) or []:
            link_id = inp.get("link")
            if link_id is None:
                continue
            link = link_by_id.get(int(link_id))
            if not link:
                continue
            origin_id = int(link[1])
            if origin_id not in seen:
                stack.append(origin_id)
    return seen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-json", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    workflow_path = Path(args.workflow_json)
    out_path = Path(args.out)
    workflow = load_json(workflow_path)

    nodes = workflow.get("nodes", [])
    links = workflow.get("links", [])
    node_by_id = {int(n["id"]): n for n in nodes if "id" in n}
    link_by_id = build_link_index(links)

    save_nodes = [n for n in nodes if n.get("type") == "SaveImage"]
    lanes = []

    for save in save_nodes:
        upstream = upstream_nodes(int(save["id"]), node_by_id, link_by_id)
        type_counts = Counter(node_by_id[i].get("type") for i in upstream if i in node_by_id)
        lanes.append({
            "save_node_id": save["id"],
            "save_prefix": (save.get("widgets_values") or [""])[0],
            "upstream_node_ids": sorted(upstream),
            "upstream_node_count": len(upstream),
            "upstream_type_counts": dict(type_counts),
        })

    report = {
        "workflow_json": str(workflow_path),
        "workflow_id": workflow.get("id"),
        "nodes": len(nodes),
        "links": len(links),
        "save_lanes": lanes,
        "strict_rule": "Treat each SaveImage lane as a module candidate, not as proof of production readiness."
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
