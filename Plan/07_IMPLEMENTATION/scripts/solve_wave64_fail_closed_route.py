#!/usr/bin/env python3
"""Evaluate Wave64 routing candidates without activating deferred model execution."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIXTURE = Path("Plan/10_REGISTRIES/wave64_fail_closed_route_solver_fixture.json")
DEFAULT_FIXTURE_SCHEMA = Path("Plan/08_SCHEMAS/wave64_fail_closed_route_solver_fixture.schema.json")
ROUTE_REQUEST_SCHEMA = Path("Plan/08_SCHEMAS/multimodal_pass_route_request.schema.json")
ROUTE_DECISION_SCHEMA = Path("Plan/08_SCHEMAS/multimodal_pass_route_decision.schema.json")
CAPABILITY_CARD_SCHEMA = Path("Plan/08_SCHEMAS/engine_model_capability_card.schema.json")
COMMON_SCHEMA = Path("Plan/08_SCHEMAS/multimodal_contract_common.schema.json")
REQUIRED_CONFORMANCE_CHECKS = {"pose", "framing", "ownership", "contact", "protected_region"}


class RouteSolverError(ValueError):
    """Raised when dry routing violates hard-filter or abstention authority."""


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
        raise RouteSolverError(f"schema_validation_failed:{label}:{location}:{first.message}")


def load_bound_source(root: Path, reference: dict[str, str], label: str) -> dict[str, Any]:
    relative = Path(reference["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise RouteSolverError(f"source_path_not_bounded_relative:{label}")
    path = (root / relative).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise RouteSolverError(f"source_missing_or_outside_project:{label}")
    if sha256_file(path) != reference["sha256"]:
        raise RouteSolverError(f"source_hash_mismatch:{label}")
    return load_json(path)


def validate_conformance_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    gate = fixture["conformance_gate"]
    if set(gate["required_checks"]) != REQUIRED_CONFORMANCE_CHECKS:
        raise RouteSolverError("conformance_required_check_set_mismatch")
    if gate["runtime_output_present"]:
        raise RouteSolverError("dry_fixture_cannot_claim_runtime_output")
    return {
        "gate_id": gate["gate_id"],
        "status": "blocked_missing_runtime_output",
        "checks": [
            {"check_id": check_id, "status": "not_run", "defect_ids": []}
            for check_id in sorted(REQUIRED_CONFORMANCE_CHECKS)
        ],
        "promotion_allowed": False,
        "repair_scope": gate["repair_scope"],
        "blocker_codes": ["BLOCKED_CONFORMANCE_RUNTIME_OUTPUT_MISSING"],
    }


def candidate_reasons(
    card: dict[str, Any],
    stack: dict[str, Any],
    request: dict[str, Any],
    gate: dict[str, Any],
    constraints: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if not gate["runtime_execution_allowed"] or not gate["phase_permissions"]["execution_bundle_compilation"]:
        reasons.append("MODEL_LIBRARY_ACTIVATION_GATE_CLOSED")
    required_authority = constraints["required_authority_status"]
    if card["authority_status"] != required_authority or stack["authority_status"] != required_authority:
        reasons.append("STACK_AUTHORITY_NOT_CERTIFIED")
    if card["engine_family"] not in constraints["allowed_engine_families"]:
        reasons.append("ENGINE_FAMILY_INCOMPATIBLE")
    if card["model"]["sha256"] is None or stack["model"]["sha256"] is None:
        reasons.append("EXACT_MODEL_HASH_MISSING")
    if request["modality"] not in card["modalities"]:
        reasons.append("MODALITY_UNSUPPORTED")
    if request["pass_intent"] not in card["pass_intents"]:
        reasons.append("PASS_INTENT_UNSUPPORTED")
    if not set(request["input_contract"]).issubset(set(card["input_contract"])):
        reasons.append("INPUT_CONTRACT_UNSATISFIED")
    if not set(request["output_contract"]).issubset(set(card["output_contract"])):
        reasons.append("OUTPUT_CONTRACT_UNSATISFIED")
    declared_capabilities = (
        set(card["input_contract"])
        | set(card["output_contract"])
        | set(card["edit_and_control_methods"])
        | set(card["pass_intents"])
    )
    if not set(request["required_capabilities"]).issubset(declared_capabilities):
        reasons.append("REQUIRED_CAPABILITY_UNSATISFIED")
    if not set(constraints["required_package_contracts"]).issubset(set(request["input_contract"])):
        reasons.append("REQUIRED_PACKAGE_CONTRACT_MISSING")
    compatibility = card["compatibility"]
    if constraints["required_vae_family"] not in compatibility["vae_families"]:
        reasons.append("VAE_FAMILY_INCOMPATIBLE")
    if constraints["required_text_encoder_family"] not in compatibility["text_encoder_families"]:
        reasons.append("TEXT_ENCODER_FAMILY_INCOMPATIBLE")
    if constraints["required_adapter_family"] not in compatibility["adapter_families"]:
        reasons.append("ADAPTER_FAMILY_INCOMPATIBLE")
    if constraints["required_control_family"] not in compatibility["control_families"]:
        reasons.append("CONTROL_FAMILY_INCOMPATIBLE")
    if constraints["required_workflow_module_id"] not in compatibility["workflow_module_ids"]:
        reasons.append("WORKFLOW_MODULE_INCOMPATIBLE")
    if constraints["required_custom_node_lock_id"] not in compatibility.get("custom_node_lock_ids", []):
        reasons.append("CUSTOM_NODE_LOCK_MISSING")
    if card["model"].get("license_use_record_id") != constraints["required_license_use_record_id"]:
        reasons.append("LICENSE_USE_RECORD_MISSING_OR_MISMATCHED")
    required_count = len(request["target_scope"]["character_instance_ids"])
    if card["scope"]["character_count"]["maximum_certified"] < required_count:
        reasons.append("CHARACTER_COUNT_NOT_CERTIFIED")
    if not any(envelope["status"] == "certified" for envelope in card["runtime_envelopes"]):
        reasons.append("CERTIFIED_RUNTIME_ENVELOPE_MISSING")
    if not any(certificate["status"] == "certified" for certificate in card["benchmark_certificates"]):
        reasons.append("CERTIFIED_BENCHMARK_BUCKET_MISSING")
    workflow = stack["workflow"]
    if not workflow["api_compatible"] or workflow["api_graph_sha256"] is None:
        reasons.append("HASHED_API_WORKFLOW_MISSING")
    if any(value is None for value in stack["component_hashes"].values()):
        reasons.append("STACK_COMPONENT_HASH_MISSING")
    if stack["runtime_profile"]["hardware_envelope_id"] != constraints["required_hardware_envelope_id"]:
        reasons.append("HARDWARE_ENVELOPE_INCOMPATIBLE")
    if constraints["cross_family_latent_policy"] != "forbidden_decoded_artifacts_only":
        reasons.append("LATENT_TRANSFER_POLICY_UNSAFE")
    return sorted(set(reasons))


def evaluate_candidates(
    capability_registry: dict[str, Any],
    request: dict[str, Any],
    gate: dict[str, Any],
    constraints: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    card_by_id = {card["capability_card_id"]: card for card in capability_registry["capability_cards"]}
    if len(card_by_id) != len(capability_registry["capability_cards"]):
        raise RouteSolverError("duplicate_capability_card_id")
    evaluations: list[dict[str, Any]] = []
    for stack in capability_registry["execution_stack_templates"]:
        card = card_by_id.get(stack["capability_card_id"])
        if card is None:
            raise RouteSolverError(f"stack_capability_card_unknown:{stack['execution_stack_id']}")
        if stack["engine_family"] != card["engine_family"]:
            raise RouteSolverError(f"stack_engine_family_mismatch:{stack['execution_stack_id']}")
        reasons = candidate_reasons(card, stack, request, gate, constraints)
        evaluations.append({
            "execution_stack_id": stack["execution_stack_id"],
            "eligible": not reasons,
            "eligibility_reasons": reasons,
            "rank_score": None,
            "rank_components": {},
            "benchmark_bucket_id": None,
        })
    unstacked_cards = len(card_by_id) - len({stack["capability_card_id"] for stack in capability_registry["execution_stack_templates"]})
    return evaluations, unstacked_cards


def build_route_decision(fixture: dict[str, Any], activation_gate: dict[str, Any], capability_registry: dict[str, Any]) -> dict[str, Any]:
    request = fixture["route_request"]
    evaluations, _ = evaluate_candidates(
        capability_registry, request, activation_gate, fixture["hard_constraints"]
    )
    eligible = [entry for entry in evaluations if entry["eligible"]]
    if eligible:
        raise RouteSolverError("deferred_fixture_unexpected_eligible_stack")
    return {
        "schema_version": "1.0.0",
        "route_decision_id": fixture["decision_metadata"]["route_decision_id"],
        "revision": fixture["decision_metadata"]["revision"],
        "route_request_id": request["route_request_id"],
        "request_constraints_sha256": canonical_sha256(request),
        "decision_status": "blocked_no_eligible_stack",
        "registry_snapshot_ids": [activation_gate["activation_gate_id"], capability_registry["registry_id"]],
        "evaluated_candidates": evaluations,
        "ranked_eligible_stack_ids": [],
        "selected_execution_stack_id": None,
        "selection_reasons": ["hard_constraints_evaluated_before_ranking", "all_candidates_ineligible", "ranking_and_llm_proposal_not_invoked"],
        "blockers": [
            {
                "blocker_type": "MODEL_LIBRARY_ACTIVATION_GATE_CLOSED",
                "details": activation_gate["gate_state"],
                "missing_evidence_ids": list(activation_gate["fail_closed_reason_codes"]),
            },
            {
                "blocker_type": "NO_CERTIFIED_EXECUTION_STACK",
                "details": "Every evaluated stack has unresolved authority, hash, runtime, workflow, or benchmark constraints.",
                "missing_evidence_ids": ["scoped_model_capability_certificate", "certified_runtime_envelope", "hash_bound_workflow_release"],
            },
        ],
        "resource_allocation": None,
        "bridge_contract_ids": [],
        "fallback_sequence": ["abstain_preserve_accepted_parent", "wait_for_explicit_model_library_activation"],
        "prohibited_substitutions": {
            "component_substitution": "forbidden",
            "stack_substitution": "explicit_new_route_decision_only",
            "engine_family_change": "explicit_bridge_or_new_route_only",
            "queue_pressure_quality_downgrade": "forbidden",
            "missing_asset_behavior": "block_or_hash_verified_acquisition",
        },
        "qa_requirement_ids": ["pose_ownership_conformance_gate", "target_protected_whole_artifact_qa"],
        "decision_fresh_until": None,
        "supersedes_decision_id": None,
        "decided_at": fixture["decision_metadata"]["decided_at"],
        "provenance": {
            "producer": "solve_wave64_fail_closed_route.py",
            "source_refs": [fixture["fixture_id"], request["route_request_id"]],
            "registry_snapshot_ids": [activation_gate["activation_gate_id"], capability_registry["registry_id"]],
            "canonicalization": "rfc8785_jcs",
        },
    }


def validate_all(root: Path, fixture: dict[str, Any], fixture_schema: dict[str, Any]) -> dict[str, Any]:
    validate_schema(fixture, fixture_schema, "solver_fixture")
    validate_schema(fixture["route_request"], load_json(root / ROUTE_REQUEST_SCHEMA), "route_request")
    activation = load_bound_source(root, fixture["source_registries"]["activation_gate"], "activation_gate")
    capabilities = load_bound_source(root, fixture["source_registries"]["capability_registry"], "capability_registry")
    if activation["runtime_execution_allowed"] or activation["authorized_phase"] != "none":
        raise RouteSolverError("activation_gate_not_deferred")
    card_schema = load_json(root / CAPABILITY_CARD_SCHEMA)
    for index, card in enumerate(capabilities["capability_cards"]):
        validate_schema(card, card_schema, f"capability_cards.{index}")
    conformance = validate_conformance_fixture(fixture)
    evaluations, unstacked_cards = evaluate_candidates(
        capabilities, fixture["route_request"], activation, fixture["hard_constraints"]
    )
    decision = build_route_decision(fixture, activation, capabilities)
    common = load_json(root / COMMON_SCHEMA)
    decision_schema = load_json(root / ROUTE_DECISION_SCHEMA)
    registry = Registry().with_resources([(common["$id"], Resource.from_contents(common))])
    validate_schema(decision, decision_schema, "route_decision", registry)
    if any(entry["rank_score"] is not None or entry["rank_components"] for entry in evaluations):
        raise RouteSolverError("ineligible_candidate_received_ranking_score")
    return {
        "status": "PASS",
        "classification": "WAVE64_FAIL_CLOSED_ROUTE_SOLVER_SLICE_PASS",
        "rows_covered": [164, 165, 166, 167, 168],
        "runtime_scope": "deterministic_dry_solver_only",
        "runtime_execution_allowed": False,
        "production_selection_allowed": False,
        "capability_card_count": len(capabilities["capability_cards"]),
        "execution_stack_count": len(capabilities["execution_stack_templates"]),
        "unstacked_capability_card_count": unstacked_cards,
        "eligible_stack_count": 0,
        "ranked_stack_count": 0,
        "llm_proposal_invoked": False,
        "conformance_decision": conformance,
        "route_decision": decision,
    }


def build_evidence(root: Path, result: dict[str, Any], fixture_path: Path, schema_path: Path) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "evidence_type": "wave64_fail_closed_route_solver_slice_validation",
        **result,
        "authority": {
            "fixture_path": fixture_path.as_posix(),
            "fixture_sha256": sha256_file(root / fixture_path),
            "schema_path": schema_path.as_posix(),
            "schema_sha256": sha256_file(root / schema_path),
            "solver_path": "Plan/07_IMPLEMENTATION/scripts/solve_wave64_fail_closed_route.py",
            "solver_sha256": sha256_file(root / "Plan/07_IMPLEMENTATION/scripts/solve_wave64_fail_closed_route.py"),
        },
        "boundaries": {
            "model_library_gate_changed": False,
            "execution_bundle_compiled": False,
            "ranking_executed": False,
            "llm_proposal_executed": False,
            "model_execution_started": False,
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
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--schema", type=Path, default=DEFAULT_FIXTURE_SCHEMA)
    parser.add_argument("--evidence-out", type=Path)
    parser.add_argument("--tracker-evidence-out", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    result = validate_all(root, load_json(root / args.fixture), load_json(root / args.schema))
    if args.evidence_out or args.tracker_evidence_out:
        evidence = build_evidence(root, result, args.fixture, args.schema)
        if args.evidence_out:
            write_json(root / args.evidence_out, evidence)
        if args.tracker_evidence_out:
            write_json(root / args.tracker_evidence_out, evidence)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
