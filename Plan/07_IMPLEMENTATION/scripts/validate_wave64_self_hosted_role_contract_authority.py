#!/usr/bin/env python3
"""Validate fail-closed Wave64 Rows201-204 self-hosted role contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = Path("Plan/10_REGISTRIES/wave64_self_hosted_role_contract_authority.json")
DEFAULT_SCHEMA = Path("Plan/08_SCHEMAS/wave64_self_hosted_role_contract_authority.schema.json")
ROLES = {"planner", "prompt_composer", "router_advisor", "defect_classifier", "vlm_critic", "audio_critic", "retrieval", "summarizer"}
SOURCES = {"role_card_schema", "retrieval_bundle_schema", "planner_proposal_schema", "reviewer_observation_schema", "role_activation_schema", "model_library_activation_gate"}
RETRIEVAL_SOURCES = {"schemas", "packages", "capabilities", "workflows", "benchmarks", "failures", "evidence", "event_state"}
PROPOSAL_FIELDS = {"plans", "prompts", "routes", "diagnoses", "hypotheses", "confidence", "evidence_refs", "alternatives", "uncertainty", "abstention"}
STACK_FIELDS = {"model", "runtime", "template", "parser", "quantization", "context"}


class RoleContractError(ValueError):
    """Raised when role contracts cross an activation or authority boundary."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(payload, indent=2, ensure_ascii=True) + "\n").encode("utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_schema(instance: Any, schema: dict[str, Any]) -> None:
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(instance), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]; location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise RoleContractError(f"schema_validation_failed:{location}:{first.message}")


def validate_sources(root: Path, authority: dict[str, Any]) -> dict[str, Any]:
    loaded: dict[str, Any] = {}
    for ref in authority["source_authorities"]:
        name = ref["name"]
        if name in loaded:
            raise RoleContractError("duplicate_source_authority_name")
        relative = Path(ref["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise RoleContractError(f"bound_path_not_relative:{name}")
        path = (root / relative).resolve()
        if root.resolve() not in path.parents or not path.is_file():
            raise RoleContractError(f"bound_file_missing_or_outside:{name}")
        if sha256_file(path) != ref["sha256"]:
            raise RoleContractError(f"bound_hash_mismatch:{name}")
        loaded[name] = load_json(path)
    if set(loaded) != SOURCES:
        raise RoleContractError("source_authority_exact_set_mismatch")
    gate = loaded["model_library_activation_gate"]
    if gate["gate_state"] != "deferred_waiting_for_complete_model_download" or gate["runtime_execution_allowed"]:
        raise RoleContractError("model_library_gate_not_fail_closed")
    if gate["prerequisites"]["all_prerequisites_satisfied"] or any(gate["phase_permissions"].values()):
        raise RoleContractError("model_library_phase_false_activation")
    return loaded


def validate_roles(authority: dict[str, Any]) -> dict[str, int]:
    roles = authority["roles"]
    if {role["role_id"] for role in roles} != ROLES or len(roles) != len(ROLES):
        raise RoleContractError("role_exact_set_mismatch")
    for role in roles:
        if role["stack_ref"] is not None or role["activated"] or role["direct_execution_authority"] or role["promotion_authority"]:
            raise RoleContractError(f"role_false_activation_or_authority:{role['role_id']}")
        if role["uncertainty_policy"] != "abstain_or_escalate" or not role["model_requirements"] or not role["escalation_conditions"]:
            raise RoleContractError(f"role_uncertainty_or_requirement_missing:{role['role_id']}")
    return {"bounded_role_count": len(roles)}


def validate_contracts(authority: dict[str, Any]) -> dict[str, int]:
    retrieval = authority["retrieval_contract"]
    if set(retrieval["source_classes"]) != RETRIEVAL_SOURCES or retrieval["runtime_active"] or retrieval["retrieval_bundle_ref"] is not None:
        raise RoleContractError("retrieval_contract_boundary_failed")
    if retrieval["required_citation_fields"] != ["immutable_id", "revision", "sha256"]:
        raise RoleContractError("retrieval_citation_fields_mismatch")
    proposal = authority["proposal_contract"]
    if set(proposal["required_fields"]) != PROPOSAL_FIELDS:
        raise RoleContractError("proposal_field_exact_set_mismatch")
    if proposal["execution_authority"] or proposal["promotion_authority"] or proposal["fixture_decision"] != "abstain_missing_qualified_stack":
        raise RoleContractError("proposal_false_authority_or_decision")
    gate = authority["qualification_gate"]
    if set(gate["required_stack_fields"]) != STACK_FIELDS or gate["qualified_stack_refs"]:
        raise RoleContractError("qualification_stack_boundary_failed")
    if gate["shadow_mode_allowed"] or gate["production_mode_allowed"] or gate["health_probe_run"] or gate["benchmark_run"]:
        raise RoleContractError("qualification_false_execution")
    return {"retrieval_source_count": len(retrieval["source_classes"]), "proposal_field_count": len(proposal["required_fields"]), "required_stack_field_count": len(gate["required_stack_fields"])}


def validate_all(root: Path, authority: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    validate_schema(authority, schema); validate_sources(root, authority)
    result: dict[str, Any] = {"status": "PASS", "classification": "WAVE64_SELF_HOSTED_ROLE_CONTRACT_AUTHORITY_SLICE_PASS", "rows_covered": [201, 202, 203, 204], "runtime_scope": "contract_and_fail_closed_fixture_only", "model_serving_active": authority["model_serving_active"], "role_activation_allowed": authority["role_activation_allowed"], "production_selection_allowed": authority["production_selection_allowed"]}
    result.update(validate_roles(authority)); result.update(validate_contracts(authority))
    if any(authority["boundaries"].values()):
        raise RoleContractError("authority_false_completion_boundary")
    return result


def build_evidence(root: Path, result: dict[str, Any], registry_path: Path, schema_path: Path) -> dict[str, Any]:
    return {"schema_version": "1.0.0", "evidence_type": "wave64_self_hosted_role_contract_authority_slice", **result, "authority": {"registry_path": registry_path.as_posix(), "registry_sha256": sha256_file(root / registry_path), "schema_path": schema_path.as_posix(), "schema_sha256": sha256_file(root / schema_path), "validator_path": "Plan/07_IMPLEMENTATION/scripts/validate_wave64_self_hosted_role_contract_authority.py", "validator_sha256": sha256_file(root / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_self_hosted_role_contract_authority.py")}, "worker_dispatch": {"intent_id": "intent_20260717T085158338Z_wave64_rows201_204_self_hosted_role_contracts_5dfe76b6", "result": "AI_WORKER_RETRY_BUDGET_EXHAUSTED_REGISTERED_PRIMARY_WORKTREE_REQUIRED", "fallback": "bounded_codex_contract_implementation_and_deterministic_validation"}, "boundaries": {"model_downloaded": False, "model_loaded": False, "qualification_executed": False, "shadow_role_activated": False, "production_role_activated": False, "direct_execution_granted": False, "promotion_authority_granted": False, "item_tracker_status_changed": False}}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, default=ROOT); parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY); parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA); parser.add_argument("--evidence-out", type=Path); parser.add_argument("--tracker-evidence-out", type=Path); args = parser.parse_args()
    root = args.root.resolve(); result = validate_all(root, load_json(root / args.registry), load_json(root / args.schema))
    if args.evidence_out or args.tracker_evidence_out:
        evidence = build_evidence(root, result, args.registry, args.schema)
        if args.evidence_out: write_json(root / args.evidence_out, evidence)
        if args.tracker_evidence_out: write_json(root / args.tracker_evidence_out, evidence)
    print(json.dumps(result, indent=2, ensure_ascii=True)); return 0


if __name__ == "__main__": raise SystemExit(main())
