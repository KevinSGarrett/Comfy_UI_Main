#!/usr/bin/env python3
"""
Extract model/checkpoint/LoRA/VAE/upscale/control asset references from a ComfyUI
workflow JSON. This is a static inventory only. It does not prove files exist.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ASSET_EXTENSIONS = (".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf", ".onnx", ".yaml", ".json")


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else [
        "node_id", "node_type", "title", "widget_index", "asset_reference",
        "engine_property", "category_property", "scene_role_property", "status_property",
        "verification_tier_property", "mode", "disabled_by_default", "sha256_property", "size_mb_property"
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--out-csv", required=True)
    args = parser.parse_args()

    data = load_json(Path(args.workflow))
    rows = []

    for node in data.get("nodes", []):
        props = node.get("properties") or {}
        widgets = node.get("widgets_values") or []
        for idx, value in enumerate(widgets):
            if isinstance(value, str) and any(ext in value.lower() for ext in ASSET_EXTENSIONS):
                rows.append({
                    "node_id": node.get("id"),
                    "node_type": node.get("type"),
                    "title": node.get("title", ""),
                    "widget_index": idx,
                    "asset_reference": value,
                    "engine_property": props.get("engine", ""),
                    "category_property": props.get("category", ""),
                    "scene_role_property": props.get("scene_role", ""),
                    "status_property": props.get("status", ""),
                    "verification_tier_property": props.get("verification_tier", ""),
                    "mode": node.get("mode", 0),
                    "disabled_by_default": props.get("disabled_by_default", ""),
                    "sha256_property": props.get("sha256", ""),
                    "size_mb_property": props.get("size_mb", ""),
                })

    write_csv(Path(args.out_csv), rows)
    print(json.dumps({"result": "PASS", "reference_count": len(rows), "out_csv": args.out_csv}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
