#!/usr/bin/env python3
"""Analyze a ComfyUI workflow for Wave 11 control-map readiness."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from collections import Counter

CONTROL_TERMS = ["controlnet", "control net", "canny", "dwpose", "openpose", "depth", "normal", "lineart", "pose", "skeleton", "ipadapter", "mask"]

def read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def node_text(node: dict) -> str:
    return " ".join([
        str(node.get("id", "")),
        node.get("type") or "",
        node.get("title") or "",
        json.dumps(node.get("widgets_values", []), ensure_ascii=False),
        json.dumps(node.get("properties", {}), ensure_ascii=False),
    ]).lower()

def classify(node: dict) -> str:
    node_type = node.get("type", "")
    props = node.get("properties") or {}
    widgets = node.get("widgets_values") or []
    text = node_text(node)

    if node_type == "Note":
        return "note_only_boundary"
    if node_type in {"ControlNetLoader", "ControlNetApplyAdvanced"}:
        return "wired_controlnet_runtime_node"
    if node_type == "LoadImage" and any("canny" in str(w).lower() for w in widgets):
        return "wired_control_image"
    if node_type in {"IPAdapter", "IPAdapterUnifiedLoader"}:
        return "wired_reference_runtime_node"
    if props.get("category") == "pose_camera":
        return "pose_camera_lora_catalog_reference"
    if any(term in text for term in CONTROL_TERMS):
        return "control_related_reference"
    return "other"

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-csv", required=True)
    args = parser.parse_args()

    workflow = Path(args.workflow)
    data = read_json(workflow)
    nodes = data.get("nodes", [])
    links = data.get("links", [])

    rows = []
    for node in nodes:
        if any(term in node_text(node) for term in CONTROL_TERMS) or node.get("type") in {"ControlNetLoader", "ControlNetApplyAdvanced", "LoadImage", "IPAdapter", "IPAdapterUnifiedLoader"}:
            props = node.get("properties") or {}
            rows.append({
                "node_id": node.get("id"),
                "node_type": node.get("type"),
                "title": node.get("title", ""),
                "mode": node.get("mode", 0),
                "classification": classify(node),
                "engine": props.get("engine", ""),
                "category": props.get("category", ""),
                "scene_role": props.get("scene_role", ""),
                "widgets_values": json.dumps(node.get("widgets_values", []), ensure_ascii=False),
            })

    summary = {
        "workflow": str(workflow),
        "workflow_sha256": hashlib.sha256(workflow.read_bytes()).hexdigest(),
        "nodes": len(nodes),
        "links": len(links),
        "control_related_records": len(rows),
        "classifications": Counter(r["classification"] for r in rows),
        "status": "PASS_STATIC_INVENTORY",
        "runtime_proof_required": True,
    }
    summary["classifications"] = dict(summary["classifications"])

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps({"summary": summary, "records": rows}, indent=2, ensure_ascii=False), encoding="utf-8")

    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["node_id", "node_type", "title", "mode", "classification", "engine", "category", "scene_role", "widgets_values"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps(summary, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
