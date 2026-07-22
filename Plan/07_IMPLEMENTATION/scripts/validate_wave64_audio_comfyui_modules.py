#!/usr/bin/env python3
"""Validate the fail-closed Row107 modular ComfyUI audio boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = Path("Plan/10_REGISTRIES/wave64_row107_audio_comfyui_module_registry.json")
SCHEMA_PATH = Path("Plan/08_SCHEMAS/audio_comfyui_module_contract.schema.json")
DEFAULT_EVIDENCE = Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-107_comfyui_audio_integration.json")
REQUIRED_TYPES = {
    "analysis_request", "event_manifest", "selector_result",
    "generated_candidate", "mix_render", "qa_evaluation",
}
FORBIDDEN = {
    "reasoning", "dependency_selection", "retry_policy",
    "release_or_promotion", "evidence_acceptance",
}
DEPENDENCY_DELTAS = {
    "TRK-W64-091": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-091_VISUAL_AUDIO_EVENT_MANIFEST_CURRENT_DELTA_20260719.json"),
    "TRK-W64-097": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-097_SAMPLE_ACCURATE_MIX_MUX_CURRENT_DELTA_20260719.json"),
    "TRK-W64-105": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-105_AUDIO_END_TO_END_ORCHESTRATOR_CURRENT_DELTA_20260722.json"),
    "TRK-W64-106": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-106_AUDIO_AV_QA_MATRIX_CURRENT_DELTA_20260722.json"),
}


class AudioModuleValidationError(ValueError):
    """Raised when the Row107 registry violates its authority boundary."""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dependency_admissions(root: Path) -> dict[str, dict[str, Any]]:
    admissions = {}
    for tracker_id, relative in DEPENDENCY_DELTAS.items():
        path = root / relative
        payload = load_json(path) if path.is_file() else {}
        complete = payload.get("row_complete") is True
        status = str(payload.get("status", "ABSENT"))
        admissions[tracker_id] = {
            "path": relative.as_posix(),
            "sha256": sha256_file(path) if path.is_file() else "0" * 64,
            "row_complete": complete,
            "dependency_satisfied": complete and not status.lower().startswith("hold"),
            "status": status,
        }
    return admissions


def validate_registry(root: Path, registry: dict[str, Any]) -> dict[str, Any]:
    schema = load_json(root / SCHEMA_PATH)
    modules = registry.get("modules")
    if not isinstance(modules, list):
        raise AudioModuleValidationError("modules_not_array")
    validator = Draft202012Validator(schema)
    for index, module in enumerate(modules):
        errors = sorted(validator.iter_errors(module), key=lambda error: list(error.path))
        if errors:
            raise AudioModuleValidationError(f"module_schema_invalid:{index}:{errors[0].message}")
    types = [module["module_type"] for module in modules]
    if len(modules) != 6 or set(types) != REQUIRED_TYPES or len(types) != len(set(types)):
        raise AudioModuleValidationError("required_module_set_mismatch")
    ids = [module["module_id"] for module in modules]
    namespaces = [module["workflow_namespace"] for module in modules]
    if len(ids) != len(set(ids)):
        raise AudioModuleValidationError("duplicate_module_id")
    if len(namespaces) != len(set(namespaces)):
        raise AudioModuleValidationError("duplicate_workflow_namespace")
    for module in modules:
        if not FORBIDDEN <= set(module["forbidden_authorities"]):
            raise AudioModuleValidationError("forbidden_authority_set_incomplete")
        if module["runtime_active"] and module["status"] != "runtime_qualified":
            raise AudioModuleValidationError("unqualified_module_cannot_be_active")
        if module["status"] == "runtime_qualified" and not module["workflow_path"]:
            raise AudioModuleValidationError("qualified_module_requires_workflow_path")
    return {
        "module_count": len(modules), "module_types": sorted(types),
        "unique_ids": True, "unique_namespaces": True,
        "authority_boundary_valid": True,
        "runtime_active_count": sum(module["runtime_active"] for module in modules),
    }


def build_evidence(root: Path) -> dict[str, Any]:
    registry_path = root / REGISTRY_PATH
    registry = load_json(registry_path)
    validation = validate_registry(root, registry)
    admissions = dependency_admissions(root)
    blockers = []
    if not all(item["dependency_satisfied"] for item in admissions.values()):
        blockers.append("ROW107_DEPENDENCIES_NOT_ACCEPTED")
    if validation["runtime_active_count"] == 0:
        blockers.extend(["AUDIO_WORKFLOW_GRAPHS_NOT_MATERIALIZED", "COMFYUI_OBJECT_INFO_AND_RUNTIME_SMOKE_ABSENT"])
    return {
        "schema_version": "1.0.0", "evidence_id": "TRK-W64-107_comfyui_audio_integration",
        "tracker_id": "TRK-W64-107", "item_id": "ITEM-W64-107",
        "status": "HOLD_DEPENDENCIES_AND_RUNTIME_WORKFLOWS_ABSENT_WITH_STATIC_MODULAR_CONTRACT_PRESENT",
        "row_complete": False, "implementation_completion_claimed": True,
        "runtime_completion_claimed": False, "release_authority": False,
        "registry": {"path": REGISTRY_PATH.as_posix(), "sha256": sha256_file(registry_path), "revision": registry["revision"]},
        "schema": {"path": SCHEMA_PATH.as_posix(), "sha256": sha256_file(root / SCHEMA_PATH)},
        "static_validation": validation, "dependency_admissions": admissions,
        "decision": {"status": "blocked", "row107_acceptance": "held", "product_completion": False, "blocker_codes": blockers},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--emit-evidence", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.registry != REGISTRY_PATH:
        payload = validate_registry(root, load_json(root / args.registry))
    else:
        payload = build_evidence(root)
    output = args.output or (root / DEFAULT_EVIDENCE if args.emit_evidence else None)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
