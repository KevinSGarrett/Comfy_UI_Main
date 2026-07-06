#!/usr/bin/env python3
"""
deconstruct_main_flow_wave04.py

Static deconstruction utility for ComfyUI workflow JSON files.
It separates active SaveImage lanes, Note boundaries, disabled LoRA catalog nodes,
node classifications, and required repair flags.

Usage:
  python deconstruct_main_flow_wave04.py --workflow path/to/workflow.json --out-dir path/to/out
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out: dict[str, Any] = {}
            for key in fieldnames:
                value = row.get(key)
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                out[key] = value
            writer.writerow(out)


def normalize_links(links: list[Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for item in links:
        if isinstance(item, list) and len(item) >= 6:
            link_id, origin_id, origin_slot, target_id, target_slot, typ = item[:6]
            result[int(link_id)] = {
                "id": int(link_id),
                "origin_id": int(origin_id),
                "origin_slot": origin_slot,
                "target_id": int(target_id),
                "target_slot": target_slot,
                "type": typ,
            }
        elif isinstance(item, dict) and "id" in item:
            result[int(item["id"])] = item
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    workflow = load_json(args.workflow)
    nodes = workflow.get("nodes", [])
    links = normalize_links(workflow.get("links", []))
    node_by_id = {int(n["id"]): n for n in nodes if "id" in n}

    incoming: dict[int, list[tuple[int, int, dict[str, Any]]]] = defaultdict(list)
    for link_id, link in links.items():
        incoming[int(link["target_id"])].append((link_id, int(link["origin_id"]), link))

    def upstream_nodes(start_id: int) -> set[int]:
        seen: set[int] = set()
        stack = [start_id]
        while stack:
            node_id = stack.pop()
            if node_id in seen:
                continue
            seen.add(node_id)
            for _, origin_id, _ in incoming.get(node_id, []):
                if origin_id not in seen:
                    stack.append(origin_id)
        return seen

    save_nodes = [n for n in nodes if n.get("type") == "SaveImage"]
    preview_nodes = [n for n in nodes if n.get("type") == "PreviewImage"]
    terminal_nodes = save_nodes + preview_nodes

    save_up_by_prefix: dict[str, set[int]] = {}
    for save in save_nodes:
        values = save.get("widgets_values") or [f"save_{save['id']}"]
        prefix = str(values[0])
        save_up_by_prefix[prefix] = upstream_nodes(int(save["id"]))

    all_save_up = set().union(*save_up_by_prefix.values()) if save_up_by_prefix else set()
    all_terminal_up: set[int] = set()
    for terminal in terminal_nodes:
        all_terminal_up |= upstream_nodes(int(terminal["id"]))

    def classify_node(node: dict[str, Any]) -> str:
        props = node.get("properties", {})
        typ = node.get("type")
        node_id = int(node["id"])
        if typ == "Note":
            return "note_boundary"
        if typ == "SaveImage":
            return "terminal_save"
        if typ == "PreviewImage":
            return "terminal_preview"
        if typ == "LoraLoader" and props.get("wave42_lora_library_node"):
            return "disabled_lora_catalog_node"
        if typ == "Lora Loader Stack (rgthree)" and props.get("wave42_active_stack_node"):
            return "active_stack_node"
        if node_id in all_terminal_up:
            return "active_runtime_or_staged_lane_node"
        return "unclassified_or_orphan"

    node_lanes: dict[int, list[str]] = defaultdict(list)
    for prefix, upstream in save_up_by_prefix.items():
        for node_id in upstream:
            node_lanes[node_id].append(prefix)

    lane_records: list[dict[str, Any]] = []
    for save in save_nodes:
        prefix = str((save.get("widgets_values") or [f"save_{save['id']}"])[0])
        up = upstream_nodes(int(save["id"]))
        sampler_nodes = [node_by_id[i] for i in up if node_by_id[i].get("type") == "KSampler"]
        loader_nodes = [
            node_by_id[i] for i in up
            if node_by_id[i].get("type") in {
                "CheckpointLoaderSimple",
                "UNETLoader",
                "LoraLoader",
                "Lora Loader Stack (rgthree)",
                "VAELoader",
                "UpscaleModelLoader",
                "IPAdapterUnifiedLoader",
                "ControlNetLoader",
            }
        ]
        issues: list[str] = []
        loader_summary = []
        for loader in loader_nodes:
            widgets = loader.get("widgets_values") or []
            first_widget = widgets[0] if widgets else ""
            loader_summary.append({
                "node_id": loader.get("id"),
                "type": loader.get("type"),
                "first_widget": first_widget,
                "title": loader.get("title", ""),
            })
        if ("SDXL" in prefix or "RealVisXL" in prefix) and any(
            item["type"] == "CheckpointLoaderSimple" and "flux" in str(item["first_widget"]).lower()
            for item in loader_summary
        ):
            issues.append("lane_name_mentions_sdxl_or_realvisxl_but_checkpoint_widget_contains_flux")
        if "Flux_to_SDXL" in prefix and any(
            item["type"] == "UNETLoader" and "z_image" in str(item["first_widget"]).lower()
            for item in loader_summary
        ):
            issues.append("lane_name_says_flux_to_sdxl_but_upstream_source_is_z_image_lane")
        if "Inpaint" in prefix:
            issues.append("fixed_image_or_mask_input_must_be_replaced_by_pass_planner_inputs")
        if "ControlNet" in prefix:
            issues.append("static_control_image_must_be_replaced_by_control_map_preprocessing")
        if "IPAdapter" in prefix:
            issues.append("identity_reference_smoke_must_be_rebuilt_as_per_character_masked_identity_module")
        if "Schnell" in prefix:
            issues.append("smoke_test_not_production_primary_lane")

        lane_records.append({
            "save_node_id": save.get("id"),
            "save_prefix": prefix,
            "upstream_node_count": len(up),
            "sampler_count": len(sampler_nodes),
            "samplers": [
                {"node_id": s.get("id"), "widgets_values": s.get("widgets_values")}
                for s in sampler_nodes
            ],
            "loader_summary": loader_summary,
            "issues_or_required_fixes": issues,
            "promotion_status_wave04": "deconstruct_only_not_promoted",
        })

    node_records: list[dict[str, Any]] = []
    for node in sorted(nodes, key=lambda n: int(n["id"])):
        props = node.get("properties", {})
        node_records.append({
            "node_id": node.get("id"),
            "type": node.get("type"),
            "mode": node.get("mode", 0),
            "title": node.get("title", ""),
            "classification": classify_node(node),
            "save_lane_membership": node_lanes.get(int(node["id"]), []),
            "wave42_lora_library_node": bool(props.get("wave42_lora_library_node")),
            "wave42_active_stack_node": bool(props.get("wave42_active_stack_node")),
            "engine": props.get("engine"),
            "category": props.get("category"),
            "scene_role": props.get("scene_role"),
            "status": props.get("status"),
            "verification_tier": props.get("verification_tier"),
            "already_active_in_main_chain": props.get("already_active_in_main_chain"),
            "disabled_by_default": props.get("disabled_by_default"),
        })

    catalog_records: list[dict[str, Any]] = []
    for node in sorted(nodes, key=lambda n: int(n["id"])):
        props = node.get("properties", {})
        if node.get("type") != "LoraLoader" or not props.get("wave42_lora_library_node"):
            continue
        widgets = node.get("widgets_values") or []
        catalog_records.append({
            "node_id": node.get("id"),
            "title": node.get("title", ""),
            "mode": node.get("mode", 0),
            "lora_id": props.get("lora_id"),
            "engine": props.get("engine"),
            "category": props.get("category"),
            "scene_role": props.get("scene_role"),
            "status": props.get("status"),
            "verification_tier": props.get("verification_tier"),
            "deploy_tier": props.get("deploy_tier"),
            "sha256": props.get("sha256"),
            "size_mb": props.get("size_mb"),
            "profile_stacks": props.get("profile_stacks", []),
            "already_active_in_main_chain": props.get("already_active_in_main_chain"),
            "disabled_by_default": props.get("disabled_by_default"),
            "disabled_reason": props.get("disabled_reason"),
            "lora_path": widgets[0] if widgets else "",
            "strength_model": widgets[1] if len(widgets) > 1 else None,
            "strength_clip": widgets[2] if len(widgets) > 2 else None,
        })

    note_records: list[dict[str, Any]] = []
    for node in sorted(nodes, key=lambda n: int(n["id"])):
        if node.get("type") != "Note":
            continue
        text = (node.get("widgets_values") or [""])[0]
        note_records.append({
            "node_id": node.get("id"),
            "title_line": text.splitlines()[0] if text else "",
            "full_text": text,
            "implementation_status_wave04": "note_only_or_boundary_documentation",
        })

    summary = {
        "source_workflow": str(args.workflow),
        "source_sha256": hashlib.sha256(args.workflow.read_bytes()).hexdigest(),
        "workflow_id": workflow.get("id"),
        "revision": workflow.get("revision"),
        "last_node_id": workflow.get("last_node_id"),
        "last_link_id": workflow.get("last_link_id"),
        "node_count": len(nodes),
        "link_count": len(links),
        "node_type_counts": dict(Counter(n.get("type") for n in nodes)),
        "mode_counts": dict(Counter(n.get("mode", 0) for n in nodes)),
        "save_image_lanes": len(save_nodes),
        "preview_nodes": len(preview_nodes),
        "note_nodes": len(note_records),
        "lora_catalog_nodes": len(catalog_records),
        "catalog_engine_counts": dict(Counter(r.get("engine") for r in catalog_records)),
        "catalog_status_counts": dict(Counter(r.get("status") for r in catalog_records)),
        "deconstruction_status": "complete",
    }

    out = args.out_dir
    write_json(out / "main_flow_wave04_deconstruction_summary.json", summary)
    write_json(out / "main_flow_wave04_runtime_lanes.json", lane_records)
    write_json(out / "main_flow_wave04_node_classification.json", node_records)
    write_json(out / "main_flow_wave04_lora_catalog_inventory_raw.json", catalog_records)
    write_json(out / "main_flow_wave04_note_boundaries.json", note_records)
    write_csv(out / "main_flow_wave04_runtime_lanes.csv", lane_records)
    write_csv(out / "main_flow_wave04_node_classification.csv", node_records)
    write_csv(out / "main_flow_wave04_lora_catalog_inventory_raw.csv", catalog_records)
    write_csv(out / "main_flow_wave04_note_boundaries.csv", note_records)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
