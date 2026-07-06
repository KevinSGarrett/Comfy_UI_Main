#!/usr/bin/env python3
"""Inventory body-shape hooks in a ComfyUI workflow JSON."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

SHAPE_RE = re.compile(r"\b(body|shape|proportion|waist|stomach|belly|abdomen|hip|hips|thigh|thighs|silhouette|bbw|cellulite|curvy|thick|fat|slim|hourglass|chubby|booty|butt)\b", re.I)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def inventory(path: Path) -> dict[str, Any]:
    flow = load_json(path)
    nodes = flow.get("nodes", [])
    links = flow.get("links", [])
    save_lanes = []
    mask_slots = []
    ksamplers = []
    body_loras = []
    for node in nodes:
        node_type = node.get("type")
        if node_type == "SaveImage":
            save_lanes.append({"node_id": node.get("id"), "prefix": (node.get("widgets_values") or [""])[0]})
        if node_type == "KSampler":
            vals = node.get("widgets_values", [])
            ksamplers.append({
                "node_id": node.get("id"),
                "steps": vals[2] if len(vals) > 2 else None,
                "cfg": vals[3] if len(vals) > 3 else None,
                "sampler": vals[4] if len(vals) > 4 else None,
                "scheduler": vals[5] if len(vals) > 5 else None,
                "denoise": vals[6] if len(vals) > 6 else None,
            })
        for inp in node.get("inputs", []):
            if inp.get("type") == "MASK":
                mask_slots.append({"node_id": node.get("id"), "node_type": node_type, "input_name": inp.get("name"), "link": inp.get("link")})
        if node_type == "LoraLoader":
            props = node.get("properties", {})
            vals = node.get("widgets_values", [])
            text = " ".join(str(x) for x in [node.get("title", ""), props.get("engine"), props.get("category"), props.get("scene_role"), vals[0] if vals else ""])
            if SHAPE_RE.search(text):
                body_loras.append({
                    "node_id": node.get("id"),
                    "title": node.get("title", ""),
                    "engine": props.get("engine"),
                    "category": props.get("category"),
                    "scene_role": props.get("scene_role"),
                    "status": props.get("status"),
                    "mode": node.get("mode"),
                    "disabled_by_default": props.get("disabled_by_default"),
                })
    return {
        "workflow_id": flow.get("id"),
        "revision": flow.get("revision"),
        "node_count": len(nodes),
        "link_count": len(links),
        "save_lanes": save_lanes,
        "mask_slots": mask_slots,
        "ksamplers": ksamplers,
        "low_denoise_anchors": [k for k in ksamplers if isinstance(k.get("denoise"), (int, float)) and k["denoise"] < 0.35],
        "body_lora_count": len(body_loras),
        "body_lora_by_engine": dict(Counter(x.get("engine") for x in body_loras)),
        "body_lora_by_category": dict(Counter(x.get("category") for x in body_loras)),
        "body_lora_by_status": dict(Counter(x.get("status") for x in body_loras)),
        "body_lora_records": body_loras,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = inventory(Path(args.workflow))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
