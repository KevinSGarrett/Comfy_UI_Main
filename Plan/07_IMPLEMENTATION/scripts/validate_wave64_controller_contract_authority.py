#!/usr/bin/env python3
"""Validate the first synthetic Wave64 durable-controller contract slice."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCHEMA = Path("Plan/08_SCHEMAS/controller_contract_authority_registry.schema.json")
DEFAULT_REGISTRY = Path("Plan/10_REGISTRIES/wave64_controller_contract_authority_registry.json")
FORBIDDEN_FINAL_AUTHORITIES = {"llm", "vlm", "critic", "app_mode", "comfyui_frontend"}


class ContractValidationError(ValueError):
    """Raised when a controller contract invariant fails closed."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_schema(schema: dict[str, Any], registry: dict[str, Any]) -> None:
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(registry),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise ContractValidationError(f"schema_validation_failed:{location}:{first.message}")


def validate_components_and_authority(registry: dict[str, Any]) -> dict[str, int]:
    components = registry["component_responsibilities"]
    component_ids = [component["component_id"] for component in components]
    if len(component_ids) != len(set(component_ids)):
        raise ContractValidationError("duplicate_component_id")

    owned_types: dict[str, str] = {}
    for component in components:
        for record_type in component["owns_record_types"]:
            if record_type in owned_types:
                raise ContractValidationError(
                    f"record_type_has_multiple_owners:{record_type}:{owned_types[record_type]}:{component['component_id']}"
                )
            owned_types[record_type] = component["component_id"]

    component_by_id = {component["component_id"]: component for component in components}
    decisions = registry["decision_authority_matrix"]
    decision_types = [decision["decision_type"] for decision in decisions]
    if len(decision_types) != len(set(decision_types)):
        raise ContractValidationError("duplicate_decision_type")
    for decision in decisions:
        authority = decision["final_authority"]
        if authority not in component_ids:
            raise ContractValidationError(f"unknown_final_authority:{authority}")
        if authority in FORBIDDEN_FINAL_AUTHORITIES or decision["llm_vlm_final_authority_allowed"]:
            raise ContractValidationError(f"llm_vlm_or_ui_final_authority_forbidden:{decision['decision_type']}")
        if decision["decision_type"] in component_by_id[authority]["forbidden_authorities"]:
            raise ContractValidationError(
                f"component_forbidden_final_authority:{authority}:{decision['decision_type']}"
            )
        if not decision["required_evidence"]:
            raise ContractValidationError(f"decision_evidence_missing:{decision['decision_type']}")

    required = {
        "contract_revision_admission",
        "state_transition_acceptance",
        "execution_submission_authorization",
        "qa_gate_decision",
        "promotion_decision",
        "exception_admission",
    }
    missing = sorted(required - set(decision_types))
    if missing:
        raise ContractValidationError("required_decisions_missing:" + ",".join(missing))
    return {"component_count": len(components), "decision_type_count": len(decisions)}


def _read_ids(path: Path, id_field: str, pattern_text: str) -> tuple[list[str], list[int]]:
    pattern = re.compile(pattern_text)
    ids: list[str] = []
    rows: list[int] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for record in csv.DictReader(handle):
            value = record.get(id_field, "")
            match = pattern.fullmatch(value)
            if not match:
                raise ContractValidationError(f"namespace_id_pattern_mismatch:{path.as_posix()}:{value}")
            ids.append(value)
            rows.append(int(match.group("row")))
    return ids, rows


def validate_namespaces(root: Path, registry: dict[str, Any]) -> dict[str, int]:
    reservations = sorted(registry["namespace_reservations"], key=lambda entry: entry["first_row"])
    all_item_ids: set[str] = set()
    all_tracker_ids: set[str] = set()
    all_rows: set[int] = set()
    for index, reservation in enumerate(reservations):
        first = reservation["first_row"]
        last = reservation["last_row"]
        if first > last:
            raise ContractValidationError(f"namespace_range_invalid:{reservation['package_id']}")
        if index and first <= reservations[index - 1]["last_row"]:
            raise ContractValidationError(f"namespace_range_overlap:{reservation['package_id']}")
        expected_rows = list(range(first, last + 1))
        item_ids, item_rows = _read_ids(
            root / reservation["item_csv"],
            reservation["item_id_field"],
            reservation["item_id_pattern"],
        )
        tracker_ids, tracker_rows = _read_ids(
            root / reservation["tracker_csv"],
            reservation["tracker_id_field"],
            reservation["tracker_id_pattern"],
        )
        if item_rows != expected_rows:
            raise ContractValidationError(f"item_row_sequence_mismatch:{reservation['package_id']}")
        if tracker_rows != expected_rows:
            raise ContractValidationError(f"tracker_row_sequence_mismatch:{reservation['package_id']}")
        if len(item_ids) != len(set(item_ids)) or all_item_ids.intersection(item_ids):
            raise ContractValidationError(f"item_id_collision:{reservation['package_id']}")
        if len(tracker_ids) != len(set(tracker_ids)) or all_tracker_ids.intersection(tracker_ids):
            raise ContractValidationError(f"tracker_id_collision:{reservation['package_id']}")
        if all_rows.intersection(expected_rows):
            raise ContractValidationError(f"row_collision:{reservation['package_id']}")
        all_item_ids.update(item_ids)
        all_tracker_ids.update(tracker_ids)
        all_rows.update(expected_rows)
    return {
        "namespace_count": len(reservations),
        "item_id_count": len(all_item_ids),
        "tracker_id_count": len(all_tracker_ids),
        "reserved_row_count": len(all_rows),
    }


def validate_revisions_and_exceptions(registry: dict[str, Any]) -> dict[str, int]:
    revisions = registry["revision_history_fixture"]
    revision_ids: set[str] = set()
    revision_record: dict[str, str] = {}
    record_ids: set[str] = set()
    active_by_record: dict[str, int] = {}
    for revision in revisions:
        revision_id = revision["revision_id"]
        record_id = revision["record_id"]
        if revision_id in revision_ids:
            raise ContractValidationError(f"duplicate_revision_id:{revision_id}")
        first_for_record = record_id not in record_ids
        for ref_name in ("parent_revision_id", "supersedes_revision_id"):
            reference = revision[ref_name]
            if reference is not None and reference not in revision_ids:
                raise ContractValidationError(f"revision_reference_not_prior:{revision_id}:{ref_name}:{reference}")
            if reference is not None and revision_record[reference] != record_id:
                raise ContractValidationError(f"cross_record_revision_reference:{revision_id}:{reference}")
        if first_for_record and (
            revision["parent_revision_id"] is not None
            or revision["supersedes_revision_id"] is not None
        ):
            raise ContractValidationError(f"initial_revision_has_parent:{revision_id}")
        if not first_for_record and revision["parent_revision_id"] is None:
            raise ContractValidationError(f"non_initial_revision_missing_parent:{revision_id}")
        revision_ids.add(revision_id)
        revision_record[revision_id] = record_id
        record_ids.add(record_id)
        if revision["status"] == "active":
            active_by_record[record_id] = active_by_record.get(record_id, 0) + 1
    if any(active_by_record.get(record_id, 0) != 1 for record_id in record_ids):
        raise ContractValidationError("each_revision_chain_requires_one_active_head")

    never_waivable = set(registry["never_waivable_rules"])
    exception_ids: set[str] = set()
    component_ids = {component["component_id"] for component in registry["component_responsibilities"]}
    for exception in registry["exception_fixture"]:
        exception_id = exception["exception_id"]
        if exception_id in exception_ids:
            raise ContractValidationError(f"duplicate_exception_id:{exception_id}")
        exception_ids.add(exception_id)
        if exception["applies_to_revision_id"] not in revision_ids:
            raise ContractValidationError(f"exception_revision_unknown:{exception_id}")
        if exception["rollback_revision_id"] not in revision_ids:
            raise ContractValidationError(f"exception_rollback_unknown:{exception_id}")
        if exception["authority"] not in component_ids:
            raise ContractValidationError(f"exception_authority_unknown:{exception_id}")
        if not exception["bounded_scope"] or not exception["evidence_refs"]:
            raise ContractValidationError(f"exception_not_bounded_or_evidenced:{exception_id}")
        created = datetime.fromisoformat(exception["created_at"])
        expires = datetime.fromisoformat(exception["expires_at"])
        if expires <= created:
            raise ContractValidationError(f"exception_expiry_invalid:{exception_id}")
        waived = never_waivable.intersection(exception["waives_rules"])
        if waived:
            raise ContractValidationError(f"exception_waives_never_waivable_rule:{exception_id}:{sorted(waived)[0]}")
    return {"revision_count": len(revisions), "exception_count": len(exception_ids)}


def validate_entity_graph(registry: dict[str, Any]) -> dict[str, int]:
    namespace_by_type = {entry["entity_type"]: entry for entry in registry["id_namespaces"]}
    if len(namespace_by_type) != len(registry["id_namespaces"]):
        raise ContractValidationError("duplicate_entity_namespace")
    graph = registry["synthetic_entity_graph"]
    entities: dict[str, dict[str, Any]] = {}
    fingerprints: dict[tuple[str, str], str] = {}
    for entity in graph["entities"]:
        entity_id = entity["entity_id"]
        entity_type = entity["entity_type"]
        namespace = namespace_by_type.get(entity_type)
        if namespace is None:
            raise ContractValidationError(f"entity_namespace_unknown:{entity_type}")
        if not re.fullmatch(namespace["pattern"], entity_id):
            raise ContractValidationError(f"entity_id_pattern_mismatch:{entity_id}")
        if entity_id in entities:
            raise ContractValidationError(f"entity_id_collision:{entity_id}")
        if entity["reusable_definition"] != namespace["reusable_definition"] or entity["scope"] != namespace["scope"]:
            raise ContractValidationError(f"entity_namespace_semantics_mismatch:{entity_id}")
        key = (entity_id, entity["revision"])
        prior = fingerprints.get(key)
        if prior is not None and prior != entity["fingerprint_sha256"]:
            raise ContractValidationError(f"immutable_entity_revision_changed:{entity_id}:{entity['revision']}")
        fingerprints[key] = entity["fingerprint_sha256"]
        entities[entity_id] = entity

    rule_keys = {
        (rule["source_type"], rule["target_type"], rule["relation"]): rule
        for rule in registry["relationship_rules"]
    }
    seen_relations: set[tuple[str, str, str]] = set()
    for relation in graph["relations"]:
        source = entities.get(relation["source_id"])
        target = entities.get(relation["target_id"])
        if source is None or target is None:
            raise ContractValidationError(
                f"dangling_entity_relation:{relation['source_id']}:{relation['target_id']}"
            )
        rule_key = (source["entity_type"], target["entity_type"], relation["relation"])
        if rule_key not in rule_keys:
            raise ContractValidationError(f"relationship_not_allowed:{rule_key}")
        seen_relations.add((relation["source_id"], relation["target_id"], relation["relation"]))

    for rule_key, rule in rule_keys.items():
        if not rule["required"]:
            continue
        sources = [entity for entity in entities.values() if entity["entity_type"] == rule["source_type"]]
        for source in sources:
            if not any(
                relation[0] == source["entity_id"] and relation[2] == rule["relation"]
                for relation in seen_relations
            ):
                raise ContractValidationError(
                    f"required_relationship_missing:{source['entity_id']}:{rule['relation']}"
                )
    return {"entity_count": len(entities), "relationship_count": len(seen_relations)}


def validate_all(root: Path, registry: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    validate_schema(schema, registry)
    result: dict[str, Any] = {
        "status": "PASS",
        "classification": "WAVE64_CONTROLLER_CONTRACT_SLICE_PASS",
        "rows_covered": registry["rows_covered"],
        "runtime_scope": registry["runtime_scope"],
        "runtime_completion_claimed": registry["runtime_completion_claimed"],
    }
    result.update(validate_components_and_authority(registry))
    result.update(validate_namespaces(root, registry))
    result.update(validate_revisions_and_exceptions(registry))
    result.update(validate_entity_graph(registry))
    return result


def build_evidence(root: Path, result: dict[str, Any], registry_path: Path, schema_path: Path) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "evidence_type": "wave64_controller_contract_slice_validation",
        **result,
        "authority": {
            "registry_path": registry_path.as_posix(),
            "registry_sha256": sha256_file(root / registry_path),
            "schema_path": schema_path.as_posix(),
            "schema_sha256": sha256_file(root / schema_path),
            "validator_path": "Plan/07_IMPLEMENTATION/scripts/validate_wave64_controller_contract_authority.py",
            "validator_sha256": sha256_file(root / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_controller_contract_authority.py"),
        },
        "boundaries": {
            "planning_package_status_changed": False,
            "model_execution_activated": False,
            "maskfactory_authority_changed": False,
            "promotion_authority_granted": False,
            "wave71_plus_activated": False,
        }
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--evidence-out", type=Path)
    parser.add_argument("--tracker-evidence-out", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    registry = load_json(root / args.registry)
    schema = load_json(root / args.schema)
    result = validate_all(root, registry, schema)
    if args.evidence_out or args.tracker_evidence_out:
        evidence = build_evidence(root, result, args.registry, args.schema)
        if args.evidence_out:
            write_json(root / args.evidence_out, evidence)
        if args.tracker_evidence_out:
            write_json(root / args.tracker_evidence_out, evidence)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
