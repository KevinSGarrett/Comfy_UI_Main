from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import jsonschema
from referencing import Registry, Resource


def load_builder(root: Path):
    path = root / "Plan/07_IMPLEMENTATION/scripts/build_wave64_maskfactory_autonomous_bridge_package.py"
    spec = importlib.util.spec_from_file_location("wave64_maskfactory_bridge_builder", path)
    if not spec or not spec.loader:
        raise RuntimeError("unable to load builder")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def schema_for_record_type(schemas: dict[str, dict[str, Any]], record_type: str) -> dict[str, Any]:
    matches = [schema for schema in schemas.values() if schema.get("properties", {}).get("record_type", {}).get("const") == record_type]
    if len(matches) != 1:
        raise ValueError(f"record_type {record_type} maps to {len(matches)} schemas")
    return matches[0]


def validate(root: Path, producer_root: Path | None = None) -> dict[str, Any]:
    builder = load_builder(root)
    builder_result = builder.write_or_check(root, "check")
    rows = builder.build_rows()
    schemas = builder.build_schemas()
    registries = builder.build_registries(schemas)
    examples = builder.build_examples()
    builder.validate_rows(rows)
    builder.validate_examples(examples, registries)

    registry = Registry().with_resources([(schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()])
    for name, schema in schemas.items():
        jsonschema.Draft202012Validator.check_schema(schema)
        if schema["$schema"] != "https://json-schema.org/draft/2020-12/schema":
            raise ValueError(f"{name} is not Draft 2020-12")
        if name != "wave64_maskfactory_bridge_common_v2.schema.json" and schema.get("additionalProperties") is not False:
            raise ValueError(f"{name} is not strict at top level")
    for name, example in examples.items():
        schema = schema_for_record_type(schemas, example["record_type"])
        validator = jsonschema.Draft202012Validator(schema, registry=registry, format_checker=jsonschema.FormatChecker())
        errors = sorted(validator.iter_errors(example), key=lambda error: list(error.path))
        if errors:
            raise ValueError(f"{name} failed schema validation: {errors[0].message}")
    mapping = registries["wave64_maskfactory_producer_wire_to_main_port_mapping_v2.json"]
    mapping_schema = schemas["wave64_maskfactory_producer_wire_to_main_port_mapping_v2.schema.json"]
    mapping_errors = sorted(
        jsonschema.Draft202012Validator(mapping_schema, registry=registry, format_checker=jsonschema.FormatChecker()).iter_errors(mapping),
        key=lambda error: list(error.path),
    )
    if mapping_errors:
        raise ValueError(f"producer/Main mapping registry failed schema validation: {mapping_errors[0].message}")
    builder.validate_mapping_registry(mapping, schemas)

    item_req = root / "Plan/Items/Waves/Wave64/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_REQUIREMENTS.json"
    tracker_req = root / "Plan/Tracker/Waves/Wave64/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_REQUIREMENTS.json"
    if item_req.read_bytes() != tracker_req.read_bytes():
        raise ValueError("Items/Tracker requirements mirrors differ")
    item_csv = root / "Plan/Items/Waves/Wave64/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_ITEM_ROWS.csv"
    tracker_csv = root / "Plan/Tracker/Waves/Wave64/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_TRACKER_ROWS.csv"
    with item_csv.open(encoding="utf-8", newline="") as handle:
        item_rows = list(csv.DictReader(handle))
    with tracker_csv.open(encoding="utf-8", newline="") as handle:
        tracker_rows = list(csv.DictReader(handle))
    if len(item_rows) != 28 or len(tracker_rows) != 28:
        raise ValueError("Items/Tracker row sidecars do not contain 28 rows")
    if [row["item_id"] for row in item_rows] != [row["item_id"] for row in tracker_rows]:
        raise ValueError("Items/Tracker row identities differ")

    coverage_a = root / "Plan/Instructions/QA/Evidence/Wave64/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_PLANNING_COVERAGE.json"
    coverage_b = root / "Plan/Tracker/Evidence/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_PLANNING_COVERAGE.json"
    if coverage_a.read_bytes() != coverage_b.read_bytes():
        raise ValueError("coverage mirrors differ")
    coverage = json.loads(coverage_a.read_text(encoding="utf-8"))
    if coverage["runtime_completion_claimed"] or coverage["runtime_adapter_implemented"] or coverage["runtime_release_published"]:
        raise ValueError("coverage overclaims runtime completion")

    preservation_path = root / "Plan/Instructions/Hydration_Rehydration/WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_PRESERVATION_MANIFEST.json"
    preservation = json.loads(preservation_path.read_text(encoding="utf-8"))
    if preservation["runtime_completion_claimed"]:
        raise ValueError("preservation manifest overclaims completion")
    paths: set[str] = set()
    for entry in preservation["entries"]:
        if entry["path"] in paths:
            raise ValueError(f"duplicate preservation path {entry['path']}")
        paths.add(entry["path"])
        content = (root / entry["path"]).read_bytes()
        if len(content) != entry["bytes"] or hashlib.sha256(content).hexdigest() != entry["sha256"]:
            raise ValueError(f"preservation mismatch {entry['path']}")

    migration = registries["wave64_maskfactory_bridge_legacy_migration_crosswalk_v2.json"]
    required_migration_surfaces = {
        "Plan/02_TARGET_ARCHITECTURE/APP_MODE_ORCHESTRATOR_DESIGN.md#qa_strictness_live_control",
        "Plan/08_SCHEMAS/mask_factory_contract.schema.json#promotion_gates_string_array",
        "Plan/Tracker/README.md#wave70_manual_gold_blocker",
        "Plan/05_AUDIO_SYSTEM/WAVE64_FOLEY_FORCE_ALIGNMENT_GATE_SPEC.md#gold_mask_dependency",
        "Plan/Items/Reports/ITEM-W64-012_image_mask_control.json",
    }
    if {entry["legacy_surface"] for entry in migration["migrations"]} != required_migration_surfaces or not all(entry["validator_required"] for entry in migration["migrations"]):
        raise ValueError("legacy migration crosswalk is incomplete")
    if migration["legacy_string_gate_can_authorize_promotion"] or migration["live_qa_dial_can_mutate_core_decision"]:
        raise ValueError("legacy authority was retained")

    index_expectations = {
        "Plan/Items/Waves/Wave64/README.md": ["Rows321-348", "WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_ITEM_ROWS.csv", "optional non-blocking profiles"],
        "Plan/Tracker/Waves/Wave64/README.md": ["Rows321-348", "WAVE64_MASKFACTORY_AUTONOMOUS_BRIDGE_TRACKER_ROWS.csv", "Row348 directly depends on Row218"],
        "Plan/Items/README.md": ["Wave64 MaskFactory Autonomous Bridge Sidecar", "Rows321-348", "core_autonomous_runtime"],
        "Plan/Tracker/README.md": ["Wave64 MaskFactory Autonomous Bridge Sidecar", "Rows321-348", "string-only legacy gate", "active, unrevoked", "Blocked_Independent_Anchor_Dependency_Missing"],
        "Plan/Instructions/WAVE_NAMESPACE_AND_SEQUENCE_CONTROL.md": ["Rows321-348", "Independent Anchor Mask Dependency Rule", "not a global dependency"],
        "Plan/Instructions/QA/GOLD_STANDARD_MASK_DEPENDENCY_GATE_PROTOCOL.md": ["not a dependency for", "maskfactory_autonomous", "Blocked_Independent_Anchor_Dependency_Missing", "must not hard-code human issuance"],
        "Plan/Instructions/COMPLETION_DEFINITION_AND_DONE_GATE.md": ["For `core_autonomous_runtime`", "maskfactory_autonomous", "Legacy `Blocked_Gold_Mask_Dependency_Missing` statuses migrate"],
        "Plan/Instructions/Hydration_Rehydration/BLOCKERS.md": ["Current Mask Authority Supersession - 2026-07-17", "Re-evaluate any active legacy blocker"],
        "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md": ["Current Mask Authority Supersession - 2026-07-17", "Do not interpret historical manual body-gold language"],
        "Plan/Instructions/Hydration_Rehydration/RECENT_DECISIONS.md": ["Current Mask Authority Supersession - 2026-07-17", "supersedes the operational interpretation"],
        "Plan/Instructions/Hydration_Rehydration/CURRENT_PURSUING_GOAL.md": ["Current Mask Authority Supersession - 2026-07-17", "not current global"],
        "Plan/Instructions/Hydration_Rehydration/KNOWN_ISSUES.md": ["Current Mask Authority Supersession - 2026-07-17", "pending v2 re-evaluation"],
        "Plan/README.md": ["Autonomous core and independent-anchor mask boundary", "not a global or `core_autonomous_runtime` dependency"],
        "Plan/03_IMAGE_SYSTEM/MASK_FACTORY_SPEC.md": ["For core, the issuer may be `maskfactory_autonomous`", "human-anchor masks are optional"],
        "Plan/03_IMAGE_SYSTEM/IMAGE_PIPELINE_BLUEPRINT.md": ["Core authority may come from", "manual/human anchors are optional"],
        "Plan/07_IMPLEMENTATION/mask_factory/ULTIMATE_MASK_FACTORY_PROMOTION_GATES.md": ["Blocked_Independent_Anchor_Dependency_Missing", "maskfactory_autonomous"],
        "Plan/02_TARGET_ARCHITECTURE/APP_MODE_ORCHESTRATOR_DESIGN.md": ["display/proposal only", "maskfactory_promotion_gate_policy_v2", "cannot mutate that policy"],
        "Plan/Instructions/AUTOMATION_CRON_FLEET_SUPERVISION_STRATEGY.md": ["independent_real_accuracy", "maskfactory_autonomous", "core_autonomous_runtime"],
        "Plan/Instructions/QA/FACIAL_NECK_HAIR_GOLD_STANDARD_BENCHMARK_PROTOCOL.md": ["optional dependency", "maskfactory_autonomous", "not a blocker for"],
        "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md": ["optional", "maskfactory_autonomous", "Waves71+ remain separately deferred"],
        "Plan/05_AUDIO_SYSTEM/WAVE64_FOLEY_FORCE_ALIGNMENT_GATE_SPEC.md": ["authority-qualified exact mask", "human/manual annotation", "maskfactory_autonomous"],
    }
    for relative, phrases in index_expectations.items():
        text = (root / relative).read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase not in text:
                raise ValueError(f"index/crosswalk missing {phrase!r} in {relative}")
    stale_active_sentences = {
        "Plan/Instructions/AUTOMATION_CRON_FLEET_SUPERVISION_STRATEGY.md": "Manual gold masks remain a dependency boundary.",
        "Plan/Instructions/QA/FACIAL_NECK_HAIR_GOLD_STANDARD_BENCHMARK_PROTOCOL.md": "the manual body/body-part dependency remains active and unchanged",
        "Plan/Tracker/README.md": "For Wave 70 rows that require manual gold-standard masks, use `Blocked_Gold_Mask_Dependency_Missing`",
        "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md": "Manual body gold masks are not ready. Do not promote candidate masks",
    }
    for relative, stale in stale_active_sentences.items():
        if stale in (root / relative).read_text(encoding="utf-8"):
            raise ValueError(f"active manual-gold authority language remains in {relative}")
    historical_report = root / "Plan/Items/Reports/ITEM-W64-012_image_mask_control.json"
    if hashlib.sha256(historical_report.read_bytes()).hexdigest() != "d743e5c38fa591ed22a4b7926b02a71d7305574ebb9c8eb77f9a569259571995":
        raise ValueError("historical ITEM-W64-012 evidence changed")
    project_manifest = json.loads((root / "Plan/PROJECT_MANIFEST.json").read_text(encoding="utf-8"))
    maskfactory_manifest = project_manifest["wave70_ultimate_mask_factory_extension"]
    if maskfactory_manifest["blocked_status_code"] != "Blocked_Independent_Anchor_Dependency_Missing":
        raise ValueError("project manifest retains legacy global gold-mask blocker")
    if "maskfactory_autonomous" not in maskfactory_manifest["non_mask_work_rule"]:
        raise ValueError("project manifest omits autonomous core authority path")

    producer_crosscheck = builder.validate_producer_schema_bindings_against_files(producer_root) if producer_root is not None else {"status": "NOT_REQUESTED", "contracts_checked": 0}
    return {
        "status": "PASS", "package_id": builder.PACKAGE_ID, "rows": len(rows), "workstreams": len(builder.WORKSTREAMS),
        "schemas": len(schemas), "registries": len(registries), "examples": len(examples),
        "preserved_files": len(preservation["entries"]), "runtime_completion_claimed": False,
        "producer_schema_crosscheck": producer_crosscheck,
        "builder": builder_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--producer-root", type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.root.resolve(), args.producer_root.resolve() if args.producer_root else None)
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
