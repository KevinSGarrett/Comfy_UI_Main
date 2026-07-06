#!/usr/bin/env python3
"""Patch a ComfyUI workflow JSON copy for a Wave15 base generation pass.

This script patches only a copy supplied by --workflow-in and writes --workflow-out.
It supports UI-style ComfyUI JSON enough for prompt text, KSampler widgets,
latent size, and SaveImage prefix patching.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def patch_node(node: Dict[str, Any], patch: Dict[str, Any]) -> None:
    node_type = node.get("type")
    widgets = list(node.get("widgets_values") or [])

    if node_type in ("CLIPTextEncode", "CLIPTextEncodeFlux") and "text" in patch:
        widgets = [patch["text"]]

    elif node_type == "KSampler":
        # ComfyUI UI KSampler widgets commonly:
        # seed, control_after_generate, steps, cfg, sampler_name, scheduler, denoise
        mapping = {"seed": 0, "steps": 2, "cfg": 3, "sampler_name": 4, "scheduler": 5, "denoise": 6}
        for key, index in mapping.items():
            if key in patch and len(widgets) > index:
                widgets[index] = patch[key]

    elif "LatentImage" in str(node_type):
        mapping = {"width": 0, "height": 1, "batch_size": 2}
        for key, index in mapping.items():
            if key in patch and len(widgets) > index:
                widgets[index] = patch[key]

    elif node_type == "SaveImage" and "filename_prefix" in patch:
        widgets = [patch["filename_prefix"]]

    node["widgets_values"] = widgets


def patch_workflow(workflow: Dict[str, Any], patch_plan: Dict[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(workflow)
    patches_by_node = {int(p["node_id"]): p for p in patch_plan.get("node_patches", [])}

    for node in result.get("nodes", []):
        node_id = int(node.get("id"))
        if node_id in patches_by_node:
            patch_node(node, patches_by_node[node_id])

    result.setdefault("extra", {})
    result["extra"].setdefault("wave15_patch_metadata", {})
    result["extra"]["wave15_patch_metadata"].update({
        "patch_plan_id": patch_plan.get("patch_plan_id"),
        "lane_id": patch_plan.get("lane_id"),
        "source": "wave15_patch_base_generation_workflow"
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-in", required=True)
    parser.add_argument("--patch-plan", required=True)
    parser.add_argument("--workflow-out", required=True)
    args = parser.parse_args()

    workflow = load_json(Path(args.workflow_in))
    patch_plan = load_json(Path(args.patch_plan))
    patched = patch_workflow(workflow, patch_plan)
    Path(args.workflow_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.workflow_out).write_text(json.dumps(patched, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote patched workflow: {args.workflow_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
