#!/usr/bin/env python3
"""Validate fail-closed Wave64 Rows177-180 MaskFactory adapter authority."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = Path("Plan/10_REGISTRIES/wave64_maskfactory_adapter_authority.json")
DEFAULT_SCHEMA = Path("Plan/08_SCHEMAS/wave64_maskfactory_adapter_authority.schema.json")
REQUIRED_BLOCKERS = {
    "service_offline": "MASKFACTORY_SERVICE_OFFLINE",
    "unknown_taxonomy": "MASKFACTORY_UNKNOWN_TAXONOMY",
    "ambiguous_owner": "MASKFACTORY_AMBIGUOUS_OWNER",
    "stale_certificate": "MASKFACTORY_STALE_CERTIFICATE",
    "transform_mismatch": "MASKFACTORY_TRANSFORM_MISMATCH",
}
AUTHORITY_STRENGTH = {
    "rejected": 0,
    "machine_draft": 1,
    "manual_draft": 1,
    "certified_machine": 3,
    "approved_package": 4,
    "gold": 5,
}


class MaskFactoryAdapterAuthorityError(ValueError):
    """Raised when adapter authority crosses a fail-closed boundary."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def validate_schema(instance: Any, schema: dict[str, Any], label: str) -> None:
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise MaskFactoryAdapterAuthorityError(f"schema_validation_failed:{label}:{location}:{first.message}")


def load_bound_file(root: Path, reference: dict[str, str], label: str) -> tuple[Path, dict[str, Any]]:
    relative = Path(reference["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise MaskFactoryAdapterAuthorityError(f"bound_path_not_relative:{label}")
    path = (root / relative).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise MaskFactoryAdapterAuthorityError(f"bound_file_missing_or_outside:{label}")
    if sha256_file(path) != reference["sha256"]:
        raise MaskFactoryAdapterAuthorityError(f"bound_hash_mismatch:{label}")
    return path, load_json(path)


def validate_source(root: Path, authority: dict[str, Any]) -> None:
    _, source = load_bound_file(root, authority["source_regional_evidence"], "source_regional_evidence")
    if source["classification"] != "WAVE64_REGIONAL_REPAIR_AUTHORITY_SLICE_PASS":
        raise MaskFactoryAdapterAuthorityError("source_regional_classification_mismatch")
    if source["runtime_execution_allowed"] or source["promotion_allowed"]:
        raise MaskFactoryAdapterAuthorityError("source_regional_false_authority")
    boundaries = source["boundaries"]
    if boundaries["trusted_mask_claimed"] or boundaries["mode_b_used_as_truth"] or boundaries["accepted_parent_mutated"]:
        raise MaskFactoryAdapterAuthorityError("source_regional_mask_or_parent_boundary_crossed")


def validate_bindings(root: Path, authority: dict[str, Any]) -> dict[str, int]:
    _, binding_schema = load_bound_file(root, authority["binding_schema"], "binding_schema")
    bindings = {"mode_a": authority["mode_a_binding"], "mode_b": authority["mode_b_binding"]}
    for label, binding in bindings.items():
        validate_schema(binding, binding_schema, f"{label}_binding")
        for transform in binding["transform_chain"]:
            if transform["parameters_sha256"] != canonical_sha256(transform["parameters"]):
                raise MaskFactoryAdapterAuthorityError(f"binding_transform_hash_mismatch:{label}")
            if not transform["roundtrip_validated"]:
                raise MaskFactoryAdapterAuthorityError(f"binding_transform_not_roundtrip_validated:{label}")
        if binding["writes_gold"]:
            raise MaskFactoryAdapterAuthorityError(f"binding_writes_gold:{label}")
    mode_a, mode_b = bindings["mode_a"], bindings["mode_b"]
    if mode_a["access_mode"] != "mode_a_package_read":
        raise MaskFactoryAdapterAuthorityError("mode_a_access_mode_mismatch")
    if mode_a["can_satisfy_promotion_gate"] or mode_a["authority"]["certificate_id"] is not None:
        raise MaskFactoryAdapterAuthorityError("mode_a_false_certificate_or_promotion")
    if mode_b["access_mode"] not in {"mode_b_live_predict", "mode_b_live_refine"}:
        raise MaskFactoryAdapterAuthorityError("mode_b_access_mode_mismatch")
    if mode_b["authority"]["truth_tier"] != "machine_draft" or mode_b["can_satisfy_promotion_gate"]:
        raise MaskFactoryAdapterAuthorityError("mode_b_authority_not_draft_only")
    if mode_b["authority"]["certificate_id"] is not None or mode_b["authority"]["promotion_scope"]:
        raise MaskFactoryAdapterAuthorityError("mode_b_false_certificate_or_scope")
    return {"validated_binding_count": 2, "mode_a_mask_count": len(mode_a["masks"]), "mode_b_mask_count": len(mode_b["masks"])}


def validate_client(authority: dict[str, Any]) -> dict[str, int]:
    client = authority["mode_b_client"]
    if client["request_submitted"] or client["execution_allowed"]:
        raise MaskFactoryAdapterAuthorityError("mode_b_client_false_execution")
    if client["silent_fallback_allowed"]:
        raise MaskFactoryAdapterAuthorityError("mode_b_client_silent_fallback")
    if client["quality_retry_budget"] != 0 or client["transport_retry_budget"] > 2:
        raise MaskFactoryAdapterAuthorityError("mode_b_retry_budget_invalid")
    if client["champion_model_id"] is not None or client["service_route_id"] is not None:
        raise MaskFactoryAdapterAuthorityError("mode_b_unverified_model_or_route_claim")
    return {"mode_b_provenance_field_count": len(client["provenance_fields"]), "mode_b_blocker_count": len(client["blocker_codes"])}


def validate_normalization(authority: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    source_bindings = {binding["binding_id"]: binding for binding in (authority["mode_a_binding"], authority["mode_b_binding"])}
    normalized: dict[str, dict[str, Any]] = {}
    for entry in authority["normalized_bindings"]:
        source = source_bindings.get(entry["source_binding_id"])
        if source is None:
            raise MaskFactoryAdapterAuthorityError("normalized_source_binding_unknown")
        expected = {
            "access_mode": source["access_mode"],
            "owner_id": source["character_instance_id"],
            "person_index": source["person_index"],
            "ontology_version": source["package"]["ontology_version"],
            "image_sha256": source["image"]["sha256"].lower(),
            "transform_chain_sha256": canonical_sha256(source["transform_chain"]),
            "truth_tier": source["authority"]["truth_tier"],
            "provider": source["package"]["provider"],
            "certificate_id": source["authority"]["certificate_id"],
            "mask_ids": [mask["mask_id"] for mask in source["masks"]],
        }
        for field, value in expected.items():
            if entry[field] != value:
                raise MaskFactoryAdapterAuthorityError(f"normalized_field_not_preserved:{entry['normalized_id']}:{field}")
        if entry["derived"] or entry["promotion_ready"]:
            raise MaskFactoryAdapterAuthorityError("normalized_false_derivation_or_promotion")
        if entry["normalized_id"] in normalized:
            raise MaskFactoryAdapterAuthorityError("duplicate_normalized_id")
        normalized[entry["normalized_id"]] = entry
    if len(normalized) != len(source_bindings):
        raise MaskFactoryAdapterAuthorityError("normalized_binding_count_mismatch")
    return normalized, {"normalized_binding_count": len(normalized)}


def validate_arbitration_and_derivation(authority: dict[str, Any], normalized: dict[str, dict[str, Any]]) -> dict[str, int]:
    arbitration = authority["arbitration"]
    if set(arbitration["candidate_ids"]) != set(normalized):
        raise MaskFactoryAdapterAuthorityError("arbitration_candidate_set_mismatch")
    selected = normalized.get(arbitration["selected_normalized_id"])
    if selected is None:
        raise MaskFactoryAdapterAuthorityError("arbitration_selected_candidate_unknown")
    strongest = max(AUTHORITY_STRENGTH[entry["truth_tier"]] for entry in normalized.values())
    if AUTHORITY_STRENGTH[selected["truth_tier"]] != strongest:
        raise MaskFactoryAdapterAuthorityError("weaker_authority_overwrite_attempt")
    if arbitration["weaker_overwrite_allowed"] or arbitration["promotion_ready"]:
        raise MaskFactoryAdapterAuthorityError("arbitration_false_overwrite_or_promotion")
    derivation = authority["derivation"]
    if set(derivation["parent_normalized_ids"]) != set(normalized):
        raise MaskFactoryAdapterAuthorityError("derivation_parent_set_mismatch")
    expected_hashes = {
        mask["sha256"].lower()
        for binding in (authority["mode_a_binding"], authority["mode_b_binding"])
        for mask in binding["masks"]
    }
    if set(derivation["parent_mask_sha256s"]) != expected_hashes:
        raise MaskFactoryAdapterAuthorityError("derivation_parent_hash_set_mismatch")
    parent_floor = min(AUTHORITY_STRENGTH[entry["truth_tier"]] for entry in normalized.values())
    if AUTHORITY_STRENGTH[derivation["output_truth_tier"]] > parent_floor:
        raise MaskFactoryAdapterAuthorityError("derived_mask_authority_inflation")
    if derivation["authority_inflation_allowed"] or derivation["promotion_ready"]:
        raise MaskFactoryAdapterAuthorityError("derivation_false_authority_or_promotion")
    return {"arbitration_candidate_count": len(normalized), "derivation_parent_count": len(derivation["parent_normalized_ids"])}


def validate_availability(authority: dict[str, Any]) -> dict[str, int]:
    gate = authority["availability_gate"]
    matrix = gate["blocker_matrix"]
    actual = {entry["condition"]: entry["blocker_code"] for entry in matrix}
    if actual != REQUIRED_BLOCKERS or len(matrix) != len(REQUIRED_BLOCKERS):
        raise MaskFactoryAdapterAuthorityError("availability_blocker_matrix_mismatch")
    if any(not entry["dependent_pass_blocked"] or not entry["unrelated_branches_continue"] for entry in matrix):
        raise MaskFactoryAdapterAuthorityError("availability_scope_isolation_failed")
    if gate["execution_allowed"] or gate["promotion_allowed"] or gate["decision"] != "blocked":
        raise MaskFactoryAdapterAuthorityError("availability_false_execution_or_promotion")
    if not gate["accepted_parent_retained"] or not gate["unrelated_dag_branches_allowed"]:
        raise MaskFactoryAdapterAuthorityError("availability_parent_or_unrelated_branch_blocked")
    return {"typed_blocker_condition_count": len(matrix)}


def validate_all(root: Path, authority: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    validate_schema(authority, schema, "maskfactory_adapter_authority")
    validate_source(root, authority)
    result: dict[str, Any] = {
        "status": "PASS",
        "classification": "WAVE64_MASKFACTORY_ADAPTER_AUTHORITY_SLICE_PASS",
        "rows_covered": [177, 178, 179, 180],
        "runtime_scope": "blocked_contract_validation_only",
        "runtime_execution_allowed": authority["runtime_execution_allowed"],
        "promotion_allowed": authority["promotion_allowed"],
        "writes_gold": authority["writes_gold"],
    }
    result.update(validate_bindings(root, authority))
    result.update(validate_client(authority))
    normalized, counts = validate_normalization(authority)
    result.update(counts)
    result.update(validate_arbitration_and_derivation(authority, normalized))
    result.update(validate_availability(authority))
    return result


def build_evidence(root: Path, result: dict[str, Any], authority_path: Path, schema_path: Path) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "evidence_type": "wave64_maskfactory_adapter_authority_slice_validation",
        **result,
        "authority": {
            "registry_path": authority_path.as_posix(), "registry_sha256": sha256_file(root / authority_path),
            "schema_path": schema_path.as_posix(), "schema_sha256": sha256_file(root / schema_path),
            "validator_path": "Plan/07_IMPLEMENTATION/scripts/validate_wave64_maskfactory_adapter_authority.py",
            "validator_sha256": sha256_file(root / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_maskfactory_adapter_authority.py"),
        },
        "worker_dispatch": {
            "intent_id": "intent_20260717T072030253Z_wave64_rows177_180_maskfactory_adapter_authority_2d9cc5a4",
            "result": "AI_WORKER_RETRY_BUDGET_EXHAUSTED",
            "issue": "Dispatch project_root must be the registered primary worktree.",
            "fallback": "bounded_codex_implementation_and_deterministic_validation",
        },
        "future_rows321_348_package": {
            "adopted": False,
            "current_check": "FAIL_MISSING_VALIDATOR",
            "consumed_as_runtime_authority": False,
        },
        "boundaries": {
            "mode_a_certified": False, "mode_b_used_as_truth": False,
            "service_request_submitted": False, "silent_mask_fallback_used": False,
            "derived_authority_inflated": False, "accepted_parent_mutated": False,
            "dependent_pass_executed": False, "unrelated_dag_branches_blocked": False,
            "promotion_transaction_created": False, "writes_gold": False,
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
