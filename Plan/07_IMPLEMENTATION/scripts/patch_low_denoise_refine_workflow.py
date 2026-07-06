#!/usr/bin/env python3
"""Patch a ComfyUI workflow JSON for a low-denoise refine pass.

This script performs conservative JSON patching only. It does not execute ComfyUI.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def patch_workflow(workflow: Dict[str, Any], ksampler_id: int, denoise: float, output_prefix: str | None = None) -> Dict[str, Any]:
    if not (0 <= denoise <= 0.4):
        raise ValueError("denoise must be between 0 and 0.4 for Wave16 refinement")
    changed = False
    for node in workflow.get("nodes", []):
        if node.get("id") == ksampler_id and node.get("type") == "KSampler":
            widgets = list(node.get("widgets_values", []))
            if len(widgets) < 7:
                raise ValueError(f"KSampler {ksampler_id} does not expose expected denoise widget")
            widgets[6] = denoise
            node["widgets_values"] = widgets
            changed = True
        if output_prefix and node.get("type") == "SaveImage":
            widgets = list(node.get("widgets_values", []))
            if widgets:
                widgets[0] = output_prefix
                node["widgets_values"] = widgets
    if not changed:
        raise ValueError(f"KSampler {ksampler_id} not found")
    return workflow


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ksampler-id", required=True, type=int)
    parser.add_argument("--denoise", required=True, type=float)
    parser.add_argument("--output-prefix")
    args = parser.parse_args()

    workflow = patch_workflow(load_json(args.workflow), args.ksampler_id, args.denoise, args.output_prefix)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(workflow, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote patched workflow: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
