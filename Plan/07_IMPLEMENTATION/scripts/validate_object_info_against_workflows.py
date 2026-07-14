#!/usr/bin/env python3
"""
Validate that every node type used by one or more ComfyUI workflows is visible
in a captured ComfyUI /object_info snapshot.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Set, Tuple


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def workflow_node_types(path: Path) -> Tuple[Set[str], str]:
    data = load_json(path)
    if isinstance(data, dict) and isinstance(data.get("nodes"), list):
        node_types = {
            node.get("type", "")
            for node in data["nodes"]
            if isinstance(node, dict) and node.get("type")
        }
        return node_types, "ui_workflow"

    prompt = data.get("prompt") if isinstance(data, dict) else None
    graph = prompt if isinstance(prompt, dict) else data
    if isinstance(graph, dict):
        node_types = {
            node.get("class_type", "")
            for node in graph.values()
            if isinstance(node, dict) and node.get("class_type")
        }
        if node_types:
            return node_types, "prompt_request" if isinstance(prompt, dict) else "api_workflow"

    return set(), "unrecognized_or_empty"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--object-info", required=True)
    parser.add_argument("--workflow", action="append", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    snapshot = load_json(Path(args.object_info))
    object_info = snapshot.get("object_info", snapshot)
    visible = set(object_info.keys())

    workflow_types = set()
    per_workflow = {}
    workflow_formats = {}
    invalid_workflows = []
    for workflow in args.workflow:
        types, workflow_format = workflow_node_types(Path(workflow))
        per_workflow[workflow] = sorted(types)
        workflow_formats[workflow] = workflow_format
        if not types:
            invalid_workflows.append(workflow)
        workflow_types |= types

    missing = sorted(t for t in workflow_types if t not in visible)
    report = {
        "schema_version": "wave03.object_info_validation_report.v1",
        "object_info_source": args.object_info,
        "workflow_sources": args.workflow,
        "workflow_node_type_count": len(workflow_types),
        "visible_node_type_count": len(visible),
        "missing_node_types": missing,
        "per_workflow_node_types": per_workflow,
        "workflow_formats": workflow_formats,
        "invalid_or_empty_workflows": invalid_workflows,
        "result": "PASS" if not missing and not invalid_workflows else "FAIL",
    }
    write_json(Path(args.out), report)
    print(
        json.dumps(
            {
                "result": report["result"],
                "missing_node_type_count": len(missing),
                "invalid_or_empty_workflow_count": len(invalid_workflows),
            },
            indent=2,
        )
    )
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
