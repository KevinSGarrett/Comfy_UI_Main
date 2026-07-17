#!/usr/bin/env python3
"""Validate the blocked Wave64 Rows169-173 bridge and specialist slice."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = Path("Plan/10_REGISTRIES/wave64_bridge_specialist_authority.json")
DEFAULT_SCHEMA = Path("Plan/08_SCHEMAS/wave64_bridge_specialist_authority.schema.json")
BRIDGE_SCHEMA = Path("Plan/08_SCHEMAS/cross_engine_bridge_contract.schema.json")
SPECIALIST_SCHEMA = Path("Plan/08_SCHEMAS/specialist_pass_contract.schema.json")
COMMON_SCHEMA = Path("Plan/08_SCHEMAS/multimodal_contract_common.schema.json")
REQUIRED_OBJECTIVES = {
    "composition", "identity", "pose", "edit", "character_count", "motion",
    "downstream_specialists", "quality", "resources",
}
REQUIRED_TRANSLATIONS = {"prompt", "reference", "pose", "depth", "mask", "control", "denoise", "scheduler", "adapter"}
REQUIRED_QUALIFICATION_METRICS = {"identity", "geometry", "regional_fidelity", "seams", "preservation", "whole_artifact_regression"}
REQUIRED_SPECIALISTS = {"face_eyes", "hands_feet", "anatomy", "skin", "hair", "fabric", "accessories", "materials", "contact", "pressure", "deformation"}
FORBIDDEN_TRANSFERS = {"cross_family_latent", "cross_family_embedding", "lora_weight", "vae_weight", "text_encoder_weight", "controlnet_weight", "adapter_weight"}


class BridgeAuthorityError(ValueError):
    """Raised when a bridge or specialist contract crosses current authority."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(data).hexdigest()


def validate_schema(instance: Any, schema: dict[str, Any], label: str, registry: Registry | None = None) -> None:
    errors = sorted(
        Draft202012Validator(schema, registry=registry or Registry(), format_checker=FormatChecker()).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise BridgeAuthorityError(f"schema_validation_failed:{label}:{location}:{first.message}")


def load_source_route(root: Path, reference: dict[str, str]) -> dict[str, Any]:
    relative = Path(reference["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise BridgeAuthorityError("source_route_path_not_bounded_relative")
    path = (root / relative).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise BridgeAuthorityError("source_route_missing_or_outside_project")
    if sha256_file(path) != reference["sha256"]:
        raise BridgeAuthorityError("source_route_hash_mismatch")
    source = load_json(path)
    decision = source["route_decision"]
    if decision["decision_status"] != "blocked_no_eligible_stack" or decision["selected_execution_stack_id"] is not None:
        raise BridgeAuthorityError("source_route_not_blocked_no_eligible_stack")
    if source["runtime_execution_allowed"] or source["production_selection_allowed"]:
        raise BridgeAuthorityError("source_route_false_execution_or_selection_claim")
    return source


def validate_intent_classification(authority: dict[str, Any], source: dict[str, Any]) -> dict[str, int]:
    classification = authority["intent_classification"]
    if set(classification["objective_dimensions"]) != REQUIRED_OBJECTIVES:
        raise BridgeAuthorityError("intent_objective_dimension_set_mismatch")
    evaluated = {candidate["execution_stack_id"] for candidate in source["route_decision"]["evaluated_candidates"]}
    if set(classification["candidate_stack_ids"]) != evaluated:
        raise BridgeAuthorityError("intent_candidate_stack_set_mismatch")
    if classification["selected_first_pass_stack_id"] is not None:
        raise BridgeAuthorityError("first_pass_engine_hardcoded_or_selected_without_route")
    if len(classification["candidate_stack_ids"]) < 2:
        raise BridgeAuthorityError("first_pass_requires_multiple_candidates")
    return {"first_pass_candidate_count": len(evaluated), "downstream_bridge_need_count": len(classification["downstream_bridge_needs"])}


def validate_bridge(authority: dict[str, Any], source: dict[str, Any]) -> dict[str, int]:
    bridge = authority["decoded_bridge_contract"]
    evaluated = {candidate["execution_stack_id"]: candidate for candidate in source["route_decision"]["evaluated_candidates"]}
    for field in ("source_execution_stack_id", "target_execution_stack_id"):
        stack_id = bridge[field]
        if stack_id not in evaluated:
            raise BridgeAuthorityError(f"bridge_stack_not_evaluated:{field}:{stack_id}")
        if evaluated[stack_id]["eligible"]:
            raise BridgeAuthorityError(f"blocked_bridge_stack_unexpectedly_eligible:{stack_id}")
    transfer_types = {item["transfer_type"] for item in bridge["transfer_objects"]}
    if transfer_types.intersection(FORBIDDEN_TRANSFERS):
        raise BridgeAuthorityError("forbidden_transfer_object_present")
    if "decoded_image" not in transfer_types or "metadata_manifest" not in transfer_types:
        raise BridgeAuthorityError("decoded_bridge_required_transfer_missing")
    if set(bridge["forbidden_transfer_objects"]) != FORBIDDEN_TRANSFERS:
        raise BridgeAuthorityError("bridge_forbidden_transfer_set_incomplete")
    for transfer in bridge["transfer_objects"]:
        metadata = transfer.get("media_metadata")
        if metadata and metadata["metadata_sha256"] != canonical_sha256(metadata["payload"]):
            raise BridgeAuthorityError(f"bridge_metadata_hash_mismatch:{transfer['artifact_id']}")
    for transform in bridge["transform_chain"]:
        for operation in transform["operations"]:
            if operation["parameters_sha256"] != canonical_sha256(operation["parameters"]):
                raise BridgeAuthorityError("bridge_transform_parameters_hash_mismatch")
            if operation["invertible"] and operation["roundtrip_evidence_id"] is None:
                raise BridgeAuthorityError("bridge_invertible_transform_missing_roundtrip_evidence")
    if bridge["bridge_status"] != "blocked" or bridge["execution_allowed"] or bridge["compatibility_certificate_id"] is not None:
        raise BridgeAuthorityError("bridge_false_certification_or_execution")
    if not bridge["ownership_propagation"]:
        raise BridgeAuthorityError("bridge_ownership_propagation_missing")
    return {"bridge_transfer_object_count": len(bridge["transfer_objects"]), "bridge_transform_count": len(bridge["transform_chain"])}


def validate_translations(authority: dict[str, Any]) -> dict[str, int]:
    translations = authority["conditioning_translations"]
    semantics = [translation["semantic"] for translation in translations]
    if set(semantics) != REQUIRED_TRANSLATIONS or len(semantics) != len(REQUIRED_TRANSLATIONS):
        raise BridgeAuthorityError("conditioning_translation_set_incomplete_or_duplicate")
    ids = [translation["translation_id"] for translation in translations]
    if len(ids) != len(set(ids)):
        raise BridgeAuthorityError("duplicate_conditioning_translation_id")
    for translation in translations:
        if translation["raw_value_copy_allowed"]:
            raise BridgeAuthorityError(f"raw_conditioning_copy_forbidden:{translation['translation_id']}")
        if not translation["translator_revision"] or not translation["configuration_sha256"]:
            raise BridgeAuthorityError(f"conditioning_translation_not_versioned:{translation['translation_id']}")
    return {"conditioning_translation_count": len(translations)}


def validate_qualification(authority: dict[str, Any]) -> dict[str, int]:
    gate = authority["qualification_gate"]
    if set(gate["required_metrics"]) != REQUIRED_QUALIFICATION_METRICS:
        raise BridgeAuthorityError("bridge_qualification_metric_set_mismatch")
    metrics = [result["metric"] for result in gate["metric_results"]]
    if set(metrics) != REQUIRED_QUALIFICATION_METRICS or len(metrics) != len(REQUIRED_QUALIFICATION_METRICS):
        raise BridgeAuthorityError("bridge_qualification_results_incomplete_or_duplicate")
    if any(result["status"] != "not_run" or result["evidence_ids"] for result in gate["metric_results"]):
        raise BridgeAuthorityError("bridge_qualification_false_measurement")
    if gate["decision"] != "blocked" or gate["execution_allowed"] or gate["certificate_id"] is not None:
        raise BridgeAuthorityError("bridge_qualification_false_promotion")
    return {"qualification_metric_count": len(metrics), "qualification_blocker_count": len(gate["blocker_codes"])}


def build_specialist_contract(entry: dict[str, Any], authority: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    intent = entry["pass_intent"]
    route = source["route_decision"]
    return {
        "schema_version": "1.0.0",
        "specialist_pass_id": f"specialist_pass_{intent}_fixture_r001",
        "revision": "r001",
        "job_id": "job_scene001_bridge_fixture_001",
        "run_id": "run_scene001_bridge_fixture_001",
        "dag_id": "dag_scene001_bridge_fixture_001",
        "scene_id": "scene001",
        "shot_id": "shot001",
        "take_id": "take001",
        "compilation_status": "blocked_no_certified_bundle",
        "sequence_role": "side_branch",
        "pass_class": "specialist",
        "pass_intent": intent,
        "modality": "image",
        "required": False,
        "parent_artifact_ids": [authority["accepted_parent_artifact_id"]],
        "route_request_id": route["route_request_id"],
        "route_decision_id": route["route_decision_id"],
        "selected_execution_stack_id": None,
        "target_contract": [{"selector_type":"body_region","owner":{"owner_type":"character_instance","owner_id":"charinst_c01_scene001_01"},"selector":{"pass_intent":intent}}],
        "protected_contract": [{"selector_type":"body_region","owner":{"owner_type":"character_instance","owner_id":"charinst_c01_scene001_01"},"selector":{"regions":["face","body"]}}],
        "mask_factory_binding_id": None,
        "cross_engine_bridge_ids": [authority["decoded_bridge_contract"]["bridge_contract_id"]],
        "workflow_patch_contract": {"allowlisted_patch_keys":[],"patch_values_sha256":canonical_sha256({})},
        "generation_parameters": {},
        "resource_contract": {"allowed_execution_targets":["none_until_certified"],"max_vram_mib":0,"max_ram_mib":1,"max_disk_mib":1,"wall_timeout_seconds":1,"queue_timeout_seconds":1,"concurrency":1,"cost_ceiling":0,"cache_policy":"no_cache"},
        "retry_contract": {"max_attempts":1,"max_reroutes":0,"retryable_failure_classes":[],"accepted_parent_immutable":True,"smallest_scope_retry":True,"hypothesis_change_required":True,"stop_conditions":["no_certified_bundle"]},
        "attempt_plan": [],
        "qa_contract": {"gate_ids":entry["qa_gate_ids"],"target_gate_ids":entry["qa_gate_ids"],"protected_gate_ids":["qa_protected_regions"],"whole_artifact_gate_ids":["qa_whole_artifact_regression"],"thresholds":{},"required_evidence_types":["runtime_artifact","qa_record"],"blocking":True,"promotion_required":True},
        "output_slots": [{"slot_id":f"output_{intent}","artifact_type":"decoded_masked_crop","required":False}],
        "promotion_policy": "not_promotable",
        "failure_policy": {"allowed_actions":["block","reroute"],"default_action":"block"},
        "provenance": {"producer":"validate_wave64_bridge_specialist_authority.py","source_refs":[entry["catalog_entry_id"],route["route_decision_id"]],"registry_snapshot_ids":route["registry_snapshot_ids"],"canonicalization":"rfc8785_jcs"},
    }


def validate_specialists(authority: dict[str, Any], source: dict[str, Any], schema: dict[str, Any], registry: Registry) -> tuple[list[dict[str, Any]], dict[str, int]]:
    entries = authority["specialist_catalog"]
    intents = [entry["pass_intent"] for entry in entries]
    if set(intents) != REQUIRED_SPECIALISTS or len(intents) != len(REQUIRED_SPECIALISTS):
        raise BridgeAuthorityError("specialist_catalog_incomplete_or_duplicate")
    contracts: list[dict[str, Any]] = []
    for entry in entries:
        if entry["eligible_exact_stack_ids"] or entry["status"] != "blocked_no_certified_bundle":
            raise BridgeAuthorityError(f"specialist_false_eligible_stack:{entry['pass_intent']}")
        contract = build_specialist_contract(entry, authority, source)
        validate_schema(contract, schema, f"specialist_contract.{entry['pass_intent']}", registry)
        contracts.append(contract)
    return contracts, {"specialist_catalog_count": len(entries), "blocked_specialist_contract_count": len(contracts)}


def validate_all(root: Path, authority: dict[str, Any], authority_schema: dict[str, Any]) -> dict[str, Any]:
    validate_schema(authority, authority_schema, "bridge_specialist_authority")
    source = load_source_route(root, authority["source_route_evidence"])
    common = load_json(root / COMMON_SCHEMA)
    registry = Registry().with_resources([(common["$id"], Resource.from_contents(common))])
    validate_schema(authority["decoded_bridge_contract"], load_json(root / BRIDGE_SCHEMA), "decoded_bridge_contract", registry)
    result: dict[str, Any] = {
        "status": "PASS",
        "classification": "WAVE64_BRIDGE_SPECIALIST_AUTHORITY_SLICE_PASS",
        "rows_covered": [169, 170, 171, 172, 173],
        "runtime_scope": "blocked_contract_compilation_only",
        "runtime_execution_allowed": authority["runtime_execution_allowed"],
        "production_bridge_certified": authority["production_bridge_certified"],
    }
    result.update(validate_intent_classification(authority, source))
    result.update(validate_bridge(authority, source))
    result.update(validate_translations(authority))
    result.update(validate_qualification(authority))
    contracts, counts = validate_specialists(authority, source, load_json(root / SPECIALIST_SCHEMA), registry)
    result.update(counts)
    result["specialist_contracts"] = contracts
    return result


def build_evidence(root: Path, result: dict[str, Any], authority_path: Path, schema_path: Path) -> dict[str, Any]:
    compact_result = {key: value for key, value in result.items() if key != "specialist_contracts"}
    return {
        "schema_version": "1.0.0",
        "evidence_type": "wave64_bridge_specialist_authority_slice_validation",
        **compact_result,
        "specialist_contracts_sha256": canonical_sha256(result["specialist_contracts"]),
        "authority": {
            "registry_path": authority_path.as_posix(),
            "registry_sha256": sha256_file(root / authority_path),
            "schema_path": schema_path.as_posix(),
            "schema_sha256": sha256_file(root / schema_path),
            "validator_path": "Plan/07_IMPLEMENTATION/scripts/validate_wave64_bridge_specialist_authority.py",
            "validator_sha256": sha256_file(root / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_bridge_specialist_authority.py"),
        },
        "boundaries": {
            "first_pass_stack_selected": False,
            "bridge_executed": False,
            "conditioning_translation_executed": False,
            "bridge_certificate_issued": False,
            "specialist_pass_executed": False,
            "model_library_gate_changed": False,
            "accepted_parent_mutated": False,
            "item_tracker_status_changed": False,
        },
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
    result = validate_all(root, load_json(root / args.registry), load_json(root / args.schema))
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
