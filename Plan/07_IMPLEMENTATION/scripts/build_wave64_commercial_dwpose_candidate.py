from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_candidates(source_dir: Path, output_dir: Path, contract_path: Path) -> dict[str, Any]:
    source_dir = source_dir.resolve()
    output_dir = output_dir.resolve()
    if source_dir == output_dir:
        raise ValueError("in-place workflow transformation is forbidden")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    transform = contract["transform"]
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {"contract_id": contract["contract_id"], "workflows": []}

    for expected in contract["source_workflows"]:
        source = source_dir / expected["filename"]
        actual_hash = _sha256(source)
        if actual_hash != expected["sha256"]:
            raise ValueError(f"source workflow hash mismatch: {expected['filename']}")
        data = json.loads(source.read_text(encoding="utf-8"))
        candidate = copy.deepcopy(data)
        expected_ids = set(expected["node_ids"])
        corrected_ids: set[int] = set()
        for node in candidate.get("nodes", []):
            if node.get("id") not in expected_ids:
                continue
            if node.get("type") != transform["source_node_type"]:
                raise ValueError(f"unexpected source node type for node {node.get('id')}")
            widgets = node.get("widgets_values")
            if not isinstance(widgets, list) or len(widgets) < 7:
                raise ValueError(f"invalid DWPreprocessor widgets for node {node.get('id')}")
            if widgets[4] != transform["required_source_bbox_model"] or widgets[5] != transform["required_source_pose_model"]:
                raise ValueError(f"unexpected DWPreprocessor model selection for node {node.get('id')}")
            node["type"] = transform["candidate_node_type"]
            for index, value in transform["replace_widget_values"].items():
                widgets[int(index)] = value
            properties = node.setdefault("properties", {})
            properties["wave64_replacement_contract_id"] = contract["contract_id"]
            properties["wave64_replaced_node_type"] = transform["source_node_type"]
            corrected_ids.add(node["id"])
        if corrected_ids != expected_ids:
            raise ValueError(f"required DWPreprocessor node set mismatch: {expected['filename']}")
        destination = output_dir / expected["filename"]
        destination.write_text(json.dumps(candidate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        manifest["workflows"].append(
            {
                "filename": expected["filename"],
                "source_sha256": actual_hash,
                "candidate_sha256": _sha256(destination),
                "corrected_node_ids": sorted(corrected_ids),
            }
        )

    manifest_path = output_dir / "W64_AQA_018_COMMERCIAL_DWPOSE_CANDIDATE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    args = parser.parse_args()
    build_candidates(args.source_dir, args.output_dir, args.contract)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
