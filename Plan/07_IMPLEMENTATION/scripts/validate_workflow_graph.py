#!/usr/bin/env python3
"""
Wave03 static ComfyUI workflow graph validator.

Purpose:
- Validate that a ComfyUI UI workflow JSON can be loaded.
- Validate node/link references.
- Validate source/target slot ranges.
- Validate declared link types against node input/output types when available.
- Extract terminal outputs and upstream runtime lanes.
- Produce JSON + CSV reports that can run locally with EC2 turned off.

This is a static validator. It does not prove custom node availability,
model loading, or image quality. Pair this with collect_comfyui_object_info.py
and validate_object_info_against_workflows.py.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple


def sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def validate_graph(flow: Dict[str, Any]) -> Dict[str, Any]:
    nodes = flow.get("nodes", [])
    links = flow.get("links", [])
    node_by_id = {node["id"]: node for node in nodes if "id" in node}
    link_by_id = {link[0]: link for link in links if isinstance(link, list) and len(link) >= 6}

    issues: List[Dict[str, Any]] = []

    for link in links:
        if not isinstance(link, list) or len(link) < 6:
            issues.append({"severity": "error", "type": "malformed_link", "link": link})
            continue

        link_id, source_node, source_slot, target_node, target_slot, declared_type = link[:6]

        if source_node not in node_by_id:
            issues.append({"severity": "error", "type": "missing_source_node", "link_id": link_id, "source_node": source_node})
            continue

        if target_node not in node_by_id:
            issues.append({"severity": "error", "type": "missing_target_node", "link_id": link_id, "target_node": target_node})
            continue

        source_outputs = node_by_id[source_node].get("outputs", [])
        target_inputs = node_by_id[target_node].get("inputs", [])

        if not isinstance(source_slot, int) or source_slot < 0 or source_slot >= len(source_outputs):
            issues.append({
                "severity": "error",
                "type": "source_slot_out_of_range",
                "link_id": link_id,
                "source_node": source_node,
                "slot": source_slot,
                "output_count": len(source_outputs),
            })
        else:
            output_type = source_outputs[source_slot].get("type")
            if output_type and declared_type and output_type != declared_type:
                issues.append({
                    "severity": "warning",
                    "type": "source_type_mismatch",
                    "link_id": link_id,
                    "source_node": source_node,
                    "declared_type": declared_type,
                    "source_output_type": output_type,
                })

        if not isinstance(target_slot, int) or target_slot < 0 or target_slot >= len(target_inputs):
            issues.append({
                "severity": "error",
                "type": "target_slot_out_of_range",
                "link_id": link_id,
                "target_node": target_node,
                "slot": target_slot,
                "input_count": len(target_inputs),
            })
        else:
            input_type = target_inputs[target_slot].get("type")
            if input_type and declared_type and input_type != declared_type:
                issues.append({
                    "severity": "warning",
                    "type": "target_type_mismatch",
                    "link_id": link_id,
                    "target_node": target_node,
                    "declared_type": declared_type,
                    "target_input_type": input_type,
                })

    for node in nodes:
        for inp in node.get("inputs", []):
            link_id = inp.get("link")
            if link_id is not None and link_id not in link_by_id:
                issues.append({
                    "severity": "error",
                    "type": "input_references_missing_link",
                    "node_id": node.get("id"),
                    "node_type": node.get("type"),
                    "link_id": link_id,
                })
        for out in node.get("outputs", []):
            out_links = out.get("links")
            if out_links:
                for link_id in out_links:
                    if link_id not in link_by_id:
                        issues.append({
                            "severity": "error",
                            "type": "output_references_missing_link",
                            "node_id": node.get("id"),
                            "node_type": node.get("type"),
                            "link_id": link_id,
                        })

    incoming = defaultdict(list)
    for link in links:
        if isinstance(link, list) and len(link) >= 6:
            link_id, source_node, _source_slot, target_node, _target_slot, declared_type = link[:6]
            incoming[target_node].append((source_node, link_id, declared_type))

    def upstream_nodes(start_id: int) -> set[int]:
        seen = set()
        stack = [start_id]
        while stack:
            node_id = stack.pop()
            if node_id in seen:
                continue
            seen.add(node_id)
            for source_node, _link_id, _declared_type in incoming.get(node_id, []):
                if source_node not in seen:
                    stack.append(source_node)
        return seen

    terminal_nodes = [node for node in nodes if node.get("type") in ("SaveImage", "PreviewImage")]
    terminal_reports = []
    enabled_upstream = set()
    for node in terminal_nodes:
        upstream = upstream_nodes(node["id"])
        if node.get("mode", 0) == 0:
            enabled_upstream |= upstream
        terminal_reports.append({
            "node_id": node["id"],
            "node_type": node.get("type", ""),
            "mode": node.get("mode", 0),
            "save_prefix": (node.get("widgets_values") or [""])[0] if node.get("type") == "SaveImage" and node.get("widgets_values") else "",
            "upstream_node_count": len(upstream),
            "upstream_sampler_ids": sorted(nid for nid in upstream if node_by_id.get(nid, {}).get("type") == "KSampler"),
        })

    errors = [issue for issue in issues if issue.get("severity") == "error"]

    return {
        "schema_version": "wave03.workflow_graph_validation_report.v1",
        "checked_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "workflow_id": flow.get("id"),
        "workflow_version": flow.get("version"),
        "revision": flow.get("revision"),
        "last_node_id": flow.get("last_node_id"),
        "last_link_id": flow.get("last_link_id"),
        "node_count": len(nodes),
        "link_count": len(links),
        "node_type_count": dict(Counter(node.get("type", "") for node in nodes)),
        "mode_count": dict(Counter(str(node.get("mode", 0)) for node in nodes)),
        "terminal_outputs": terminal_reports,
        "enabled_upstream_node_count": len(enabled_upstream),
        "not_upstream_of_enabled_terminal_count": len([node for node in nodes if node.get("id") not in enabled_upstream]),
        "static_graph_issues": issues,
        "static_validation_result": "PASS" if not errors else "FAIL",
        "runtime_validation_result": "NOT_RUN_OBJECT_INFO_REQUIRED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True, help="Path to ComfyUI workflow JSON.")
    parser.add_argument("--out-dir", required=True, help="Directory for validation reports.")
    args = parser.parse_args()

    workflow_path = Path(args.workflow)
    out_dir = Path(args.out_dir)
    flow = load_json(workflow_path)
    report = validate_graph(flow)
    report["source_file"] = str(workflow_path)
    report["source_sha256"] = sha256_file(workflow_path)

    write_json(out_dir / "workflow_graph_validation_report.json", report)

    terminal_rows = report.get("terminal_outputs", [])
    write_csv(out_dir / "terminal_outputs.csv", terminal_rows)

    node_type_rows = [{"node_type": k, "count": v} for k, v in sorted(report["node_type_count"].items(), key=lambda item: (-item[1], item[0]))]
    write_csv(out_dir / "node_type_counts.csv", node_type_rows)

    print(json.dumps({
        "result": report["static_validation_result"],
        "node_count": report["node_count"],
        "link_count": report["link_count"],
        "issue_count": len(report["static_graph_issues"]),
        "out_dir": str(out_dir),
    }, indent=2))
    return 0 if report["static_validation_result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
