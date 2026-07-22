#!/usr/bin/env python3
"""Validate Wave42's static object-info admission contract and optional snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = Path("Plan/10_REGISTRIES/wave64_wave42_object_info_admission_contract.json")
SCHEMA_PATH = Path("Plan/08_SCHEMAS/runpod_wave42_object_info_admission_contract.schema.json")


class AdmissionContractError(ValueError):
    """Raised when static identity or object-info evidence drifts."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AdmissionContractError(f"JSON root must be an object: {path}")
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


def validate_contract(root: Path, value: dict[str, Any]) -> None:
    Draft202012Validator(load_json(root / SCHEMA_PATH)).validate(value)
    if value["contract_id"] != content_id(value):
        raise AdmissionContractError("admission contract identity drift")
    for binding in value["evidence_bindings"]:
        path = root / binding["path"]
        if path.stat().st_size != binding["bytes"] or sha256_file(path) != binding["sha256"]:
            raise AdmissionContractError(f"bound evidence drift: {binding['path']}")

    node_reconciliation = load_json(root / value["evidence_bindings"][0]["path"])
    if node_reconciliation["quarantine_pins"] != value["quarantine"]["custom_node_pins"]:
        raise AdmissionContractError("custom-node pin set drift")
    if node_reconciliation["core_compatibility"]["current_pod_head"] != value["candidate"]["comfyui_commit"]:
        raise AdmissionContractError("candidate ComfyUI commit drift")
    if node_reconciliation["core_compatibility"]["current_pod_version"] != value["candidate"]["comfyui_version"]:
        raise AdmissionContractError("candidate ComfyUI version drift")
    observed_workflows = {
        Path(item["path"]).name: (item["sha256"], item["nodes"], item["unique_types"])
        for item in node_reconciliation["raw_workflows"]
    }
    contracted_workflows = {
        Path(item["path"]).name: (item["sha256"], item["nodes"], item["unique_types"])
        for item in value["quarantine"]["workflows"]
    }
    if observed_workflows != contracted_workflows:
        raise AdmissionContractError("workflow identity drift")

    model_reconciliation = load_json(root / value["evidence_bindings"][1]["path"])
    if set(model_reconciliation["workflow_hashes"].values()) != {item["sha256"] for item in value["quarantine"]["workflows"]}:
        raise AdmissionContractError("model-selection workflow binding drift")
    staging = load_json(root / value["evidence_bindings"][4]["path"])
    overlay = value["candidate"]["commercial_dwpose"]
    for key, staging_key in (("overlay_path", "path"), ("overlay_manifest_sha256", "manifest_sha256"), ("node_sha256", "node_sha256"), ("gpu_distribution", "gpu_distribution"), ("cpu_distribution_metadata_present", "cpu_distribution_metadata_present"), ("imported", "imported")):
        if overlay[key] != staging["overlay"][staging_key]:
            raise AdmissionContractError(f"commercial DWPose overlay drift: {key}")

    required = value["required_object_info_types"]
    if required != sorted(required) or len(required) != value["candidate"]["executable_object_info_types"]:
        raise AdmissionContractError("required object-info set must be sorted and exact")
    if "Note" in required or "DWPreprocessor" in required or overlay["node_type"] not in required:
        raise AdmissionContractError("candidate executable type partition drift")
    forbidden_false = (
        "coordinator_admission", "custom_node_import", "object_info", "model_resolution", "model_load",
        "workflow_execution", "quality", "activation", "promotion",
    )
    if any(value["authority"][key] for key in forbidden_false):
        raise AdmissionContractError("unsupported runtime authority")


def _required_inputs(node_info: dict[str, Any]) -> set[str]:
    inputs = node_info.get("input", {})
    required = inputs.get("required", {}) if isinstance(inputs, dict) else {}
    return set(required) if isinstance(required, dict) else set()


def evaluate_object_info(value: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    required = set(value["required_object_info_types"])
    missing = sorted(required - set(snapshot))
    forbidden = sorted(set(value["forbidden_object_info_types"]) & set(snapshot))
    signature_mismatches: dict[str, list[str]] = {}
    for node_type, expected_inputs in value["signature_requirements"].items():
        if node_type in snapshot:
            absent = sorted(set(expected_inputs) - _required_inputs(snapshot[node_type]))
            if absent:
                signature_mismatches[node_type] = absent
    if missing or forbidden or signature_mismatches:
        raise AdmissionContractError(
            f"object-info admission failed: missing={missing}, forbidden={forbidden}, signatures={signature_mismatches}"
        )
    return {
        "status": "PASS",
        "required_types": len(required),
        "frontend_only_exemptions": value["frontend_only_exemptions"],
        "custom_node_import": True,
        "object_info": True,
        "model_load": False,
        "workflow_execution": False,
        "activation": False,
        "promotion": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    parser.add_argument("--object-info", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    contract_path = args.contract if args.contract.is_absolute() else root / args.contract
    value = load_json(contract_path)
    validate_contract(root, value)
    result: dict[str, Any] = {
        "status": "PASS",
        "contract_id": value["contract_id"],
        "static_contract": True,
        "coordinator_admission": False,
        "object_info": False,
    }
    if args.object_info:
        snapshot_path = args.object_info if args.object_info.is_absolute() else root / args.object_info
        result = evaluate_object_info(value, load_json(snapshot_path))
        result["contract_id"] = value["contract_id"]
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
