#!/usr/bin/env python3
"""Validate the static FLUX.2 Klein workflow and dependency contract."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = Path("Plan/10_REGISTRIES/wave64_aqa_flux2_klein_workflow_contract.json")
SCHEMA_PATH = Path("Plan/08_SCHEMAS/runpod_autonomous_flux2_klein_workflow_contract.schema.json")


class WorkflowContractError(ValueError):
    """Raised when workflow identity, graph, dependencies, or authority drift."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise WorkflowContractError(f"JSON root must be an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def content_id(value: dict[str, Any]) -> str:
    candidate = json.loads(json.dumps(value))
    candidate["contract_id"] = "0" * 64
    payload = json.dumps(candidate, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def installed_versions(root: Path) -> dict[str, str]:
    site_packages = root / "ComfyUI/.venv/Lib/site-packages"
    result: dict[str, str] = {}
    for distribution in importlib.metadata.distributions(path=[str(site_packages)]):
        name = distribution.metadata.get("Name", "").lower().replace("_", "-")
        if name:
            result[name] = distribution.version
    return result


def validate_contract(root: Path, value: dict[str, Any], verify_local_environment: bool = True) -> None:
    Draft202012Validator(load_json(root / SCHEMA_PATH)).validate(value)
    if value["contract_id"] != content_id(value):
        raise WorkflowContractError("workflow contract identity drift")
    template = value["official_template"]
    installed_template = root / Path(template["installed_copy"]["path"])
    if installed_template.stat().st_size != template["bytes"] or sha256_file(installed_template) != template["sha256"]:
        raise WorkflowContractError("installed official template identity drift")
    template_text = installed_template.read_text(encoding="utf-8")
    for filename in ("flux-2-klein-base-4b.safetensors", "flux-2-klein-4b.safetensors"):
        if filename not in template_text:
            raise WorkflowContractError("official base/distilled template structure drift")
    candidate_binding = value["selected_api_candidate"]
    candidate_path = root / Path(candidate_binding["path"])
    if candidate_path.stat().st_size != candidate_binding["bytes"] or sha256_file(candidate_path) != candidate_binding["sha256"]:
        raise WorkflowContractError("selected API workflow identity drift")
    candidate = load_json(candidate_path)
    observed_nodes = [node["class_type"] for node in candidate.values()]
    if observed_nodes != value["required_nodes"]:
        raise WorkflowContractError("selected API workflow node order drift")
    for node_id, node in candidate.items():
        for input_value in node["inputs"].values():
            if isinstance(input_value, list) and len(input_value) == 2 and input_value[0] not in candidate:
                raise WorkflowContractError(f"workflow link target missing: {node_id}")
    serialized = json.dumps(candidate, sort_keys=True)
    exact_names = ("flux-2-klein-4b-fp8.safetensors", "qwen_3_4b.safetensors", "flux2-vae.safetensors")
    if any(name not in serialized for name in exact_names) or "flux-2-klein-base-4b.safetensors" in serialized:
        raise WorkflowContractError("selected API workflow model identity drift")
    if candidate["8"]["inputs"]["cfg"] != 1.0 or candidate["10"]["inputs"] != {"steps": 4, "width": 1024, "height": 1024}:
        raise WorkflowContractError("distilled four-step sampling contract drift")
    bound_nodes: set[str] = set()
    for binding in value["comfyui_checkout"]["source_bindings"]:
        path = root / Path(binding["path"])
        if path.stat().st_size != binding["bytes"] or sha256_file(path) != binding["sha256"]:
            raise WorkflowContractError(f"ComfyUI source binding drift: {binding['path']}")
        source = path.read_text(encoding="utf-8")
        for node_type in binding["node_types"]:
            if node_type not in source:
                raise WorkflowContractError(f"bound node missing from source: {node_type}")
            bound_nodes.add(node_type)
    if bound_nodes != set(value["required_nodes"]):
        raise WorkflowContractError("required node source coverage drift")
    if verify_local_environment:
        versions = installed_versions(root)
        for package, expected in value["dependency_environment"]["observed_versions"].items():
            if versions.get(package) != expected:
                raise WorkflowContractError(f"local dependency version drift: {package}")
    forbidden = ("current_pod_object_info", "current_pod_dependencies", "model_resolution", "runtime_smoke", "quality", "activation", "promotion")
    if any(value["authority"][key] for key in forbidden):
        raise WorkflowContractError("unsupported workflow authority")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    parser.add_argument("--skip-local-environment", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    path = args.contract if args.contract.is_absolute() else root / args.contract
    value = load_json(path)
    validate_contract(root, value, verify_local_environment=not args.skip_local_environment)
    print(json.dumps({"status": "PASS", "contract_id": value["contract_id"], "static_workflow_contract": True, "runtime_smoke": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
