#!/usr/bin/env python3
"""Validate Row111 reuse/adaptation dispositions without duplicating work."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = Path("Plan/10_REGISTRIES/wave64_row111_audio_component_compatibility_registry.json")
SCHEMA_PATH = Path("Plan/08_SCHEMAS/audio_component_adapter_record.schema.json")
DEFAULT_EVIDENCE = Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-111_audio_existing_component_migration.json")
DEPENDENCY_DELTAS = {
    "TRK-W64-067": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-067_PLANNING_AUTHORITY_CURRENT_DELTA_20260719.json"),
    "TRK-W64-069": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-069_FULL_AUDIO_LIBRARY_INDEX_CURRENT_DELTA_20260719.json"),
    "TRK-W64-080": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-080_HYBRID_AUDIO_RETRIEVAL_INDEX_CURRENT_DELTA_20260719.json"),
    "TRK-W64-091": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-091_VISUAL_AUDIO_EVENT_MANIFEST_CURRENT_DELTA_20260719.json"),
    "TRK-W64-097": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-097_SAMPLE_ACCURATE_MIX_MUX_CURRENT_DELTA_20260719.json"),
    "TRK-W64-105": Path("Plan/Instructions/QA/Evidence/Wave64/TRK-W64-105_AUDIO_END_TO_END_ORCHESTRATOR_CURRENT_DELTA_20260722.json"),
}
AUTHORITY_RANK = {"structural": 0, "candidate": 1, "technical_qa": 2, "production": 3}


class CompatibilityError(ValueError):
    """Raised for stale, duplicate, or authority-invalid component mappings."""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_registry(root: Path, registry: dict[str, Any]) -> dict[str, Any]:
    schema = load_json(root / SCHEMA_PATH)
    components = registry.get("components")
    if not isinstance(components, list) or not components:
        raise CompatibilityError("components_missing")
    validator = Draft202012Validator(schema)
    capabilities, component_ids, source_paths = set(), set(), set()
    dispositions: dict[str, int] = {}
    for index, component in enumerate(components):
        errors = sorted(validator.iter_errors(component), key=lambda error: list(error.path))
        if errors:
            raise CompatibilityError(f"component_schema_invalid:{index}:{errors[0].message}")
        if component["component_id"] in component_ids:
            raise CompatibilityError("duplicate_component_id")
        if component["capability"] in capabilities:
            raise CompatibilityError("duplicate_capability_owner")
        if component["source_path"] in source_paths:
            raise CompatibilityError("duplicate_source_path")
        component_ids.add(component["component_id"])
        capabilities.add(component["capability"])
        source_paths.add(component["source_path"])
        path = (root / component["source_path"]).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError as exc:
            raise CompatibilityError("source_outside_project_root") from exc
        if not path.is_file() or path.stat().st_size != component["source_bytes"] or sha256_file(path) != component["source_sha256"]:
            raise CompatibilityError(f"source_identity_mismatch:{component['component_id']}")
        disposition = component["disposition"]
        dispositions[disposition] = dispositions.get(disposition, 0) + 1
        if disposition == "adapt_once" and not component["adapter_contract"]:
            raise CompatibilityError("adapter_contract_required")
        if disposition != "adapt_once" and component["adapter_contract"] is not None:
            raise CompatibilityError("adapter_contract_forbidden_for_disposition")
        if component["authority_ceiling"] == "production":
            raise CompatibilityError("legacy_production_authority_forbidden")
        if not component["limitations"]:
            raise CompatibilityError("limitations_required")
    return {"component_count": len(components), "unique_capability_count": len(capabilities),
            "source_hashes_match": True, "disposition_counts": dispositions,
            "maximum_authority_rank": max(AUTHORITY_RANK[item["authority_ceiling"]] for item in components)}


def dependency_admissions(root: Path) -> dict[str, dict[str, Any]]:
    result = {}
    for tracker, relative in DEPENDENCY_DELTAS.items():
        path = root / relative
        payload = load_json(path) if path.is_file() else {}
        complete = payload.get("row_complete") is True
        status = str(payload.get("status", "ABSENT"))
        result[tracker] = {"path": relative.as_posix(), "sha256": sha256_file(path) if path.is_file() else "0" * 64,
                           "row_complete": complete, "dependency_satisfied": complete and not status.lower().startswith("hold"), "status": status}
    return result


def build_evidence(root: Path) -> dict[str, Any]:
    registry_path = root / REGISTRY_PATH
    validation = validate_registry(root, load_json(registry_path))
    admissions = dependency_admissions(root)
    return {
        "schema_version": "1.0.0", "evidence_id": "TRK-W64-111_audio_existing_component_migration",
        "tracker_id": "TRK-W64-111", "item_id": "ITEM-W64-111",
        "status": "HOLD_DEPENDENCIES_AND_RUNTIME_ADAPTERS_ABSENT_WITH_HASH_BOUND_COMPATIBILITY_INVENTORY_PRESENT",
        "row_complete": False, "implementation_completion_claimed": True, "runtime_completion_claimed": False,
        "registry": {"path": REGISTRY_PATH.as_posix(), "sha256": sha256_file(registry_path)},
        "schema": {"path": SCHEMA_PATH.as_posix(), "sha256": sha256_file(root / SCHEMA_PATH)},
        "validation": validation, "dependency_admissions": admissions,
        "decision": {"status": "blocked", "row111_acceptance": "held", "product_completion": False,
                     "blocker_codes": ["ROW111_DEPENDENCIES_NOT_ACCEPTED", "VERSIONED_RUNTIME_ADAPTERS_NOT_MATERIALIZED"]},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--emit-evidence", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
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
