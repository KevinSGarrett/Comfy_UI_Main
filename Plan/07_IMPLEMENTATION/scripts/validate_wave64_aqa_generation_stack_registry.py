#!/usr/bin/env python3
"""Validate the storage-bound, deliberately inactive W64-AQA generation stacks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = Path("Plan/10_REGISTRIES/wave64_aqa_generation_stack_registry.json")
SCHEMA_PATH = Path("Plan/08_SCHEMAS/runpod_autonomous_generation_stack_registry.schema.json")
DEPENDENCY_SCHEMA_PATH = Path("Plan/08_SCHEMAS/runpod_autonomous_flux2_klein_dependency_bundle.schema.json")


class GenerationStackError(ValueError):
    """Raised when a generation candidate drifts or gains unsupported authority."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GenerationStackError(f"JSON root must be an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_registry(root: Path, registry: dict[str, Any]) -> dict[str, Any]:
    Draft202012Validator(load_json(root / SCHEMA_PATH)).validate(registry)
    stacks = registry["stacks"]
    if [item["priority"] for item in stacks] != [1, 2, 3, 4]:
        raise GenerationStackError("generation stack priority must be contiguous")
    ids = [item["stack_id"] for item in stacks]
    if len(ids) != len(set(ids)):
        raise GenerationStackError("generation stack ids must be unique")
    selected = [item for item in stacks if item["selection_state"] == "SELECTED_INACTIVE"]
    if len(selected) != 1 or selected[0]["stack_id"] != registry["selected_stack_id"]:
        raise GenerationStackError("exactly one selected inactive stack must match selected_stack_id")
    if selected[0]["asset"]["package_id"] != "W64-AQA-PROMOTED-FLUX2-KLEIN-4B-FP8":
        raise GenerationStackError("smallest exact promoted candidate must remain the selected first stack")
    dependency_binding = selected[0]["dependency_bundle"]
    if not dependency_binding:
        raise GenerationStackError("selected stack must bind its exact dependency bundle")
    dependency_path = root / Path(dependency_binding["path"])
    if sha256_file(dependency_path) != dependency_binding["sha256"]:
        raise GenerationStackError("selected dependency bundle hash drift")
    dependency = load_json(dependency_path)
    Draft202012Validator(load_json(root / DEPENDENCY_SCHEMA_PATH)).validate(dependency)
    if (
        dependency.get("stack_id") != selected[0]["stack_id"]
        or dependency.get("authority", {}).get("component_identity") is not True
        or dependency.get("authority", {}).get("current_pod_complete") is not False
        or dependency.get("workflow", {}).get("exact_workflow_hash_bound") is not True
        or selected[0]["execution"].get("workflow_bound") is not True
    ):
        raise GenerationStackError("selected dependency bundle identity or authority drift")
    if any(stack["execution"]["workflow_bound"] for stack in stacks[1:]):
        raise GenerationStackError("unselected generation workflow gained authority")
    for stack in stacks:
        binding = stack["package_binding"]
        package_path = root / Path(binding["path"])
        if sha256_file(package_path) != binding["sha256"]:
            raise GenerationStackError(f"promoted package hash drift: {binding['path']}")
        package = load_json(package_path)
        asset = stack["asset"]
        if (
            package.get("package_id") != asset["package_id"]
            or package.get("repository") != asset["repository"]
            or package.get("revision") != asset["revision"]
            or package.get("license_metadata") != asset["license_metadata"]
            or package.get("root") != asset["root"]
            or package.get("file_count") != 1
            or package.get("total_bytes") != asset["bytes"]
            or len(package.get("files", [])) != 1
        ):
            raise GenerationStackError(f"promoted package identity drift: {stack['stack_id']}")
        file_record = package["files"][0]
        if any(file_record.get(key) != asset[key] for key in ("path", "bytes", "sha256")):
            raise GenerationStackError(f"promoted package file drift: {stack['stack_id']}")
        if package.get("license_acceptance_authority") is not False:
            raise GenerationStackError(f"unsupported license authority: {stack['stack_id']}")
        execution = stack["execution"]
        if execution["executable"] or not execution["inactive"]:
            raise GenerationStackError(f"inactive candidate became executable: {stack['stack_id']}")
        if stack is not selected[0] and stack["dependency_bundle"] is not None:
            raise GenerationStackError(f"unselected candidate gained a dependency bundle: {stack['stack_id']}")
        if any(registry["authority"][key] for key in ("license_acceptance", "dependency_bundle", "workflow", "runtime", "capacity", "quality", "activation", "promotion")):
            raise GenerationStackError("registry grants unsupported execution authority")
    return selected[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    args = parser.parse_args()
    root = args.root.resolve()
    registry_path = args.registry if args.registry.is_absolute() else root / args.registry
    selected = validate_registry(root, load_json(registry_path))
    print(json.dumps({
        "status": "PASS",
        "selected_stack_id": selected["stack_id"],
        "selected_package_id": selected["asset"]["package_id"],
        "executable": selected["execution"]["executable"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
