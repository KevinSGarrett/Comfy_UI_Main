#!/usr/bin/env python3
"""Validate the fail-closed Wave64 Rows174-176 regional repair authority."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = Path("Plan/10_REGISTRIES/wave64_regional_repair_authority.json")
DEFAULT_SCHEMA = Path("Plan/08_SCHEMAS/wave64_regional_repair_authority.schema.json")
HYPOTHESIS_SCHEMA = Path("Plan/08_SCHEMAS/failure_diagnosis_and_repair_hypothesis.schema.json")
COMMON_SCHEMA = Path("Plan/08_SCHEMAS/model_intelligence_common.schema.json")
REQUIRED_GATES = {
    "target_region", "protected_regions", "boundary_seams", "color", "grain",
    "sharpness", "geometry", "identity", "ownership", "temporal_continuity",
    "audio_continuity", "unrelated_defect_scan", "whole_artifact_regression",
}


class RegionalRepairAuthorityError(ValueError):
    """Raised when regional repair authority crosses a fail-closed boundary."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def validate_schema(instance: Any, schema: dict[str, Any], label: str, registry: Registry | None = None) -> None:
    errors = sorted(
        Draft202012Validator(schema, registry=registry or Registry(), format_checker=FormatChecker()).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise RegionalRepairAuthorityError(f"schema_validation_failed:{label}:{location}:{first.message}")


def load_source(root: Path, reference: dict[str, str]) -> dict[str, Any]:
    relative = Path(reference["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise RegionalRepairAuthorityError("source_path_not_bounded_relative")
    path = (root / relative).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise RegionalRepairAuthorityError("source_missing_or_outside_project")
    if sha256_file(path) != reference["sha256"]:
        raise RegionalRepairAuthorityError("source_hash_mismatch")
    source = load_json(path)
    if source["classification"] != "WAVE64_BRIDGE_SPECIALIST_AUTHORITY_SLICE_PASS":
        raise RegionalRepairAuthorityError("source_classification_mismatch")
    if source["runtime_execution_allowed"] or source["production_bridge_certified"]:
        raise RegionalRepairAuthorityError("source_false_runtime_or_bridge_authority")
    if source["boundaries"]["accepted_parent_mutated"] or source["boundaries"]["specialist_pass_executed"]:
        raise RegionalRepairAuthorityError("source_parent_or_specialist_boundary_crossed")
    return source


def validate_regional_contract(authority: dict[str, Any]) -> dict[str, int]:
    parent = authority["accepted_parent"]
    contract = authority["regional_edit_contract"]
    if contract["parent_artifact_id"] != parent["artifact_id"]:
        raise RegionalRepairAuthorityError("regional_parent_binding_mismatch")
    if contract["denoise_bounds"]["minimum"] > contract["denoise_bounds"]["maximum"]:
        raise RegionalRepairAuthorityError("regional_denoise_bounds_inverted")
    operation = contract["transform"]
    if operation["parameters_sha256"] != canonical_sha256(operation["parameters"]):
        raise RegionalRepairAuthorityError("regional_transform_parameters_hash_mismatch")
    if operation["invertible"] and not operation["roundtrip_evidence_id"]:
        raise RegionalRepairAuthorityError("regional_transform_roundtrip_evidence_missing")
    if contract["target"]["mask_binding_id"] is not None:
        raise RegionalRepairAuthorityError("unvalidated_mask_binding_claimed")
    if contract["mask_authority"]["required_access_mode"] != "mode_a_package_read":
        raise RegionalRepairAuthorityError("regional_mask_access_mode_not_mode_a")
    if contract["mask_authority"]["mode_b_draft_only"] is not True or contract["mask_authority"]["writes_gold"]:
        raise RegionalRepairAuthorityError("regional_mask_authority_boundary_crossed")
    if contract["execution_allowed"] or contract["recomposition"]["parent_mutation_allowed"]:
        raise RegionalRepairAuthorityError("regional_false_execution_or_parent_mutation")
    return {"protected_scope_count": len(contract["protected_scopes"]), "regional_blocker_count": len(contract["blocker_codes"])}


def validate_hypothesis(authority: dict[str, Any], root: Path) -> dict[str, int]:
    common = load_json(root / COMMON_SCHEMA)
    schema_registry = Registry().with_resources([(common["$id"], Resource.from_contents(common))])
    hypothesis = authority["repair_hypothesis"]
    validate_schema(hypothesis, load_json(root / HYPOTHESIS_SCHEMA), "repair_hypothesis", schema_registry)
    prior = authority["prior_failed_attempt"]
    if not set(hypothesis["defect_codes"]).intersection(prior["defect_codes"]):
        raise RegionalRepairAuthorityError("repair_hypothesis_not_bound_to_failed_defect")
    changed = set(hypothesis["changed_variables"])
    if changed == set(prior["changed_variables"]):
        raise RegionalRepairAuthorityError("repair_hypothesis_repeats_prior_variables")
    if changed.issubset({"seed"}):
        raise RegionalRepairAuthorityError("seed_only_repair_forbidden")
    if hypothesis["remaining_attempt_budget"] > 2:
        raise RegionalRepairAuthorityError("repair_attempt_budget_unbounded")
    target = authority["regional_edit_contract"]["target"]
    scope = {
        "owner_id": target["owner_id"], "region": target["region"],
        "parent_artifact_id": authority["accepted_parent"]["artifact_id"],
        "coordinate_space": target["coordinate_space"],
    }
    if hypothesis["localized_scope_sha256"] != canonical_sha256(scope):
        raise RegionalRepairAuthorityError("repair_localized_scope_hash_mismatch")
    if hypothesis["accepted_parent_mutation_allowed"] or hypothesis["promotion_authority"] != "none":
        raise RegionalRepairAuthorityError("repair_hypothesis_false_parent_or_promotion_authority")
    return {"repair_changed_variable_count": len(changed), "remaining_attempt_budget": hypothesis["remaining_attempt_budget"]}


def validate_reintegration(authority: dict[str, Any]) -> dict[str, int]:
    parent = authority["accepted_parent"]
    gate = authority["reintegration_gate"]
    if gate["baseline_artifact_id"] != parent["artifact_id"] or not gate["accepted_parent_retained"]:
        raise RegionalRepairAuthorityError("reintegration_parent_not_retained")
    result_names = [entry["gate"] for entry in gate["gate_results"]]
    if set(gate["required_gates"]) != REQUIRED_GATES:
        raise RegionalRepairAuthorityError("reintegration_required_gate_set_mismatch")
    if set(result_names) != REQUIRED_GATES or len(result_names) != len(REQUIRED_GATES):
        raise RegionalRepairAuthorityError("reintegration_gate_results_incomplete_or_duplicate")
    if any(entry["status"] != "not_run" or entry["evidence_ids"] for entry in gate["gate_results"]):
        raise RegionalRepairAuthorityError("reintegration_false_qa_measurement")
    if gate["candidate_artifact_id"] is not None or gate["promotion_transaction_id"] is not None:
        raise RegionalRepairAuthorityError("reintegration_false_candidate_or_promotion_transaction")
    if gate["decision"] != "blocked":
        raise RegionalRepairAuthorityError("reintegration_false_promotion_decision")
    return {"reintegration_gate_count": len(result_names), "reintegration_blocker_count": len(gate["blocker_codes"])}


def validate_all(root: Path, authority: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    validate_schema(authority, schema, "regional_repair_authority")
    load_source(root, authority["source_bridge_evidence"])
    result: dict[str, Any] = {
        "status": "PASS",
        "classification": "WAVE64_REGIONAL_REPAIR_AUTHORITY_SLICE_PASS",
        "rows_covered": [174, 175, 176],
        "runtime_scope": "blocked_contract_validation_only",
        "runtime_execution_allowed": authority["runtime_execution_allowed"],
        "promotion_allowed": authority["promotion_allowed"],
        "accepted_parent_immutable": authority["accepted_parent"]["immutable"],
    }
    result.update(validate_regional_contract(authority))
    result.update(validate_hypothesis(authority, root))
    result.update(validate_reintegration(authority))
    return result


def build_evidence(root: Path, result: dict[str, Any], authority_path: Path, schema_path: Path) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "evidence_type": "wave64_regional_repair_authority_slice_validation",
        **result,
        "authority": {
            "registry_path": authority_path.as_posix(), "registry_sha256": sha256_file(root / authority_path),
            "schema_path": schema_path.as_posix(), "schema_sha256": sha256_file(root / schema_path),
            "validator_path": "Plan/07_IMPLEMENTATION/scripts/validate_wave64_regional_repair_authority.py",
            "validator_sha256": sha256_file(root / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_regional_repair_authority.py"),
        },
        "worker_dispatch": {
            "intent_id": "intent_20260717T070358414Z_wave64_rows174_176_regional_repair_authority_v3_98c5486f",
            "result": "AI_WORKER_RETRY_BUDGET_EXHAUSTED",
            "issue": "Dispatch project_root must be the registered primary worktree.",
            "fallback": "bounded_codex_implementation_and_deterministic_validation",
        },
        "boundaries": {
            "trusted_mask_claimed": False, "mode_b_used_as_truth": False,
            "accepted_parent_mutated": False, "candidate_artifact_generated": False,
            "repair_attempt_executed": False, "reintegration_qa_executed": False,
            "promotion_transaction_created": False, "model_library_gate_changed": False,
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
