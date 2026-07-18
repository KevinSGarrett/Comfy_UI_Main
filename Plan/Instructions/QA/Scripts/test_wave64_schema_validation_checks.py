from __future__ import annotations

import importlib.util
import json
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
VALIDATOR_PATH = PROJECT_ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_schema_validation_checks.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("row051_schema_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable_to_load_row051_schema_validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate(module, name: str, payload: object) -> dict[str, object]:
    path = PROJECT_ROOT / f"Plan/08_SCHEMAS/_row051_{name}.schema.json"
    result = module.validate_schema_file(path, payload)
    return {
        "schema_valid": result["schema_valid"],
        "schema_role": result["schema_role"],
        "has_nonempty_defs": result["has_nonempty_defs"],
        "structure_pass": module.has_required_schema_structure(result),
    }


def main() -> int:
    module = load_validator()
    draft = "https://json-schema.org/draft/2020-12/schema"
    cases: list[dict[str, object]] = []

    def record(name: str, actual: bool, expected: bool) -> None:
        cases.append({"name": name, "expected": expected, "actual": actual, "pass": actual is expected})

    defs = evaluate(module, "defs", {"$schema": draft, "$defs": {"Sha256": {"type": "string"}}})
    record("nonempty_defs_module_valid", bool(defs["schema_valid"]), True)
    record("nonempty_defs_module_classified", defs["schema_role"] == "shared_definition_module", True)
    record("nonempty_defs_module_structure_pass", bool(defs["structure_pass"]), True)

    empty_defs = evaluate(module, "empty_defs", {"$schema": draft, "$defs": {}})
    record("empty_defs_rejected", bool(empty_defs["structure_pass"]), False)

    metadata_only = evaluate(module, "metadata", {"$schema": draft, "title": "metadata only"})
    record("metadata_only_rejected", bool(metadata_only["structure_pass"]), False)

    malformed_defs = evaluate(module, "malformed_defs", {"$schema": draft, "$defs": {"Thing": {"type": "not-a-json-schema-type"}}})
    record("malformed_defs_meta_schema_rejected", bool(malformed_defs["schema_valid"]), False)
    record("malformed_defs_structure_rejected", bool(malformed_defs["structure_pass"]), False)

    object_root = evaluate(module, "object", {"$schema": draft, "type": "object", "properties": {"id": {"type": "string"}}})
    record("ordinary_object_schema_retained", bool(object_root["structure_pass"]), True)

    ref_root = evaluate(module, "ref", {"$schema": draft, "$ref": "#/$defs/Thing", "$defs": {"Thing": {"type": "string"}}})
    record("top_level_ref_schema_retained", bool(ref_root["structure_pass"]), True)
    record("top_level_ref_not_misclassified_as_defs_only", ref_root["schema_role"] == "instance_root", True)

    legacy = evaluate(module, "legacy", {"schema_name": "legacy", "required_fields": ["id"]})
    record("legacy_descriptor_retained", bool(legacy["structure_pass"]), True)

    payload = {
        "status": "PASS" if all(case["pass"] for case in cases) else "FAIL",
        "classification": "ROW051_SHARED_DEFINITION_MODULE_VALIDATION_REGRESSION_PASS",
        "validator_path": VALIDATOR_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "case_count": len(cases),
        "failure_count": sum(not bool(case["pass"]) for case in cases),
        "cases": cases,
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["failure_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
