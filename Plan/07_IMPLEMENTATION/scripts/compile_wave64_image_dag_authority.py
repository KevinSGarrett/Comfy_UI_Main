#!/usr/bin/env python3
"""Compile and validate fail-closed Wave64 Rows181-184 image DAG authority."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = Path("Plan/10_REGISTRIES/wave64_image_dag_authority.json")
DEFAULT_SCHEMA = Path("Plan/08_SCHEMAS/wave64_image_dag_authority.schema.json")
MODULE_ORDER = [
    "composition", "identity", "pose_depth", "realism",
    "regional_repair", "material", "upscale", "export",
]
INTENT_MODULE = {
    "composition": "composition",
    "identity": "identity",
    "pose_depth": "pose_depth",
    "ownership_contact": "pose_depth",
    "realism": "realism",
    "regional_repair": "regional_repair",
    "material": "material",
    "upscale": "upscale",
    "export": "export",
}
REQUIRED_LINEAGE = {
    "packages", "prompts", "seeds", "models", "workflows", "masks",
    "transforms", "attempts", "runtime", "scorecards", "revocation",
}
REQUIRED_QA_SCOPES = {"target", "protected", "whole_frame"}
REQUIRED_SOURCE_NAMES = {
    "maskfactory_adapter_evidence",
    "workflow_module_contract_schema",
    "multimodal_pass_dag_schema",
    "multimodal_contract_common_schema",
    "workflow_release_manifest_schema",
    "comfyui_execution_receipt_schema",
    "multimodal_artifact_manifest_schema",
    "artifact_promotion_transaction_schema",
}


class ImageDagAuthorityError(ValueError):
    """Raised when the image DAG authority crosses a fail-closed boundary."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = (json.dumps(payload, indent=2, ensure_ascii=True) + "\n").encode("utf-8")
    path.write_bytes(serialized)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def validate_schema(
    instance: Any,
    schema: dict[str, Any],
    label: str,
    schema_registry: Registry | None = None,
) -> None:
    kwargs: dict[str, Any] = {"format_checker": FormatChecker()}
    if schema_registry is not None:
        kwargs["registry"] = schema_registry
    errors = sorted(
        Draft202012Validator(schema, **kwargs).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise ImageDagAuthorityError(f"schema_validation_failed:{label}:{location}:{first.message}")


def load_bound_file(root: Path, reference: dict[str, str], label: str) -> tuple[Path, dict[str, Any]]:
    relative = Path(reference["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ImageDagAuthorityError(f"bound_path_not_relative:{label}")
    path = (root / relative).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise ImageDagAuthorityError(f"bound_file_missing_or_outside:{label}")
    if sha256_file(path) != reference["sha256"]:
        raise ImageDagAuthorityError(f"bound_hash_mismatch:{label}")
    return path, load_json(path)


def dag_digest(dag: dict[str, Any]) -> str:
    digest_input = copy.deepcopy(dag)
    digest_input.pop("compiled_plan_sha256", None)
    return canonical_sha256(digest_input)


def compile_dag(request: dict[str, Any], modules: dict[str, dict[str, Any]]) -> dict[str, Any]:
    unknown = set(request["needed_pass_intents"]) - set(INTENT_MODULE)
    if unknown:
        raise ImageDagAuthorityError(f"unknown_compile_intents:{','.join(sorted(unknown))}")
    selected = {INTENT_MODULE[intent] for intent in request["needed_pass_intents"]}
    ordered = [module_id for module_id in MODULE_ORDER if module_id in selected]
    if not ordered or ordered[0] != "composition" or ordered[-1] != "export":
        raise ImageDagAuthorityError("compile_request_missing_root_or_terminal")

    pass_ids = {module_id: f"{request['slice_id']}__{module_id}" for module_id in ordered}
    pass_nodes = [
        {
            "pass_id": pass_ids[module_id],
            "specialist_pass_contract_id": modules[module_id]["module_contract"]["module_id"],
            "required": True,
        }
        for module_id in ordered
    ]
    edges = []
    for index, (source, target) in enumerate(zip(ordered, ordered[1:]), start=1):
        edges.append(
            {
                "edge_id": f"{request['slice_id']}__edge_{index:02d}",
                "source_pass_id": pass_ids[source],
                "source_output_slot": modules[source]["module_contract"]["primary_outputs"][0],
                "target_pass_id": pass_ids[target],
                "target_input_slot": modules[target]["module_contract"]["primary_inputs"][0],
                "dependency_type": "qa" if target == "export" else "data",
                "artifact_contract": "immutable_image_candidate_or_control_manifest",
                "bridge_contract_id": None,
                "acceptance_required": target in {"regional_repair", "export"},
            }
        )

    dag = {
        "schema_version": "1.0.0",
        "multimodal_pass_dag_id": f"image_dag_{request['slice_id']}_r001",
        "revision": "r001",
        "job_id": f"job_{request['slice_id']}_blocked_fixture",
        "run_id": f"run_{request['slice_id']}_not_submitted",
        "scene_id": request["scene_id"],
        "shot_id": request["shot_id"],
        "take_id": request["take_id"],
        "dag_status": "blocked",
        "pass_nodes": pass_nodes,
        "edges": edges,
        "root_pass_ids": [pass_ids[ordered[0]]],
        "terminal_pass_ids": [pass_ids[ordered[-1]]],
        "required_output_slots": ["image_export_candidate"],
        "resource_schedule": {
            "scheduler_policy_id": "wave64_image_quality_priority_r001",
            "strategy": "quality_priority",
            "runtime_lease_required": True,
            "fencing_token_required": True,
            "max_parallel_passes": 1,
            "runtime_class_ids": ["comfyui_gpu_image_worker"],
            "per_pass_constraints": [
                {
                    "pass_id": pass_ids[module_id],
                    "runtime_class_ids": ["comfyui_gpu_image_worker"],
                    "max_queue_seconds": 900,
                    "max_wall_seconds": 1800,
                }
                for module_id in ordered
            ],
        },
        "global_retry_budget": {
            "max_attempts": request["retry_budget"]["max_attempts"],
            "max_reroutes": request["retry_budget"]["max_reroutes"],
        },
        "global_qa_contract": {
            "gate_ids": ["qa_target", "qa_protected", "qa_whole_frame"],
            "target_gate_ids": ["qa_target"],
            "protected_gate_ids": ["qa_protected"],
            "whole_artifact_gate_ids": ["qa_whole_frame"],
            "thresholds": {},
            "required_evidence_types": ["execution_receipt", "artifact_manifest", "independent_visual_qa"],
            "blocking": True,
            "promotion_required": True,
        },
        "failure_propagation": {
            "required_pass_failure": "bounded_repair_then_block",
            "optional_pass_failure": "record_and_continue",
            "upstream_invalidation": "revalidate_descendants",
            "join_failure": "block_join_and_descendants",
            "ambiguous_attempt": "block_no_failover_or_promotion",
            "silent_skip_allowed": False,
        },
        "promotion_rules": [
            {
                "output_slot": "image_export_candidate",
                "qa_gate_ids": ["qa_target", "qa_protected", "qa_whole_frame"],
                "policy_id": "wave64_image_artifact_promotion_r001",
                "exactly_once": True,
            }
        ],
        "compiled_plan_sha256": "0" * 64,
        "provenance": {
            "producer": "compile_wave64_image_dag_authority.py",
            "source_refs": [request["compile_request_id"], request["accepted_parent"]["artifact_id"]],
            "registry_snapshot_ids": ["wave64_image_dag_authority_rows181_184_r001"],
            "canonicalization": "rfc8785_jcs",
        },
    }
    dag["compiled_plan_sha256"] = dag_digest(dag)
    return dag


def validate_sources(root: Path, authority: dict[str, Any]) -> dict[str, dict[str, Any]]:
    loaded: dict[str, dict[str, Any]] = {}
    for reference in authority["source_authorities"]:
        if reference["name"] in loaded:
            raise ImageDagAuthorityError("duplicate_source_authority_name")
        _, payload = load_bound_file(root, reference, reference["name"])
        loaded[reference["name"]] = payload
    if set(loaded) != REQUIRED_SOURCE_NAMES:
        raise ImageDagAuthorityError("source_authority_exact_set_mismatch")
    source = loaded["maskfactory_adapter_evidence"]
    if source["classification"] != "WAVE64_MASKFACTORY_ADAPTER_AUTHORITY_SLICE_PASS":
        raise ImageDagAuthorityError("source_maskfactory_classification_mismatch")
    if source["runtime_execution_allowed"] or source["promotion_allowed"]:
        raise ImageDagAuthorityError("source_maskfactory_false_runtime_authority")
    return loaded


def validate_modules(authority: dict[str, Any], module_schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    modules: dict[str, dict[str, Any]] = {}
    for entry in authority["module_library"]:
        validate_schema(entry["module_contract"], module_schema, f"module:{entry['module_id']}")
        if entry["module_id"] in modules:
            raise ImageDagAuthorityError("duplicate_module_id")
        if entry["module_id"] != entry["module_contract"]["module_id"]:
            raise ImageDagAuthorityError(f"module_contract_id_mismatch:{entry['module_id']}")
        if entry["workflow_release_id"] is not None or entry["status"] != "blocked_no_workflow_release":
            raise ImageDagAuthorityError(f"module_false_release_claim:{entry['module_id']}")
        if not entry["api_compatible"] or not entry["stable_patch_points"]:
            raise ImageDagAuthorityError(f"module_api_or_patch_contract_missing:{entry['module_id']}")
        if entry["fixed_character_names"] or entry["hidden_paths"] or entry["orchestration_decisions"]:
            raise ImageDagAuthorityError(f"module_contains_forbidden_authority:{entry['module_id']}")
        modules[entry["module_id"]] = entry
    if set(modules) != set(MODULE_ORDER) or len(modules) != len(MODULE_ORDER):
        raise ImageDagAuthorityError("module_library_exact_set_mismatch")
    return modules


def validate_compilation(
    authority: dict[str, Any],
    modules: dict[str, dict[str, Any]],
    dag_schema: dict[str, Any],
    common_schema: dict[str, Any],
) -> dict[str, int]:
    schema_registry = Registry().with_resource(common_schema["$id"], Resource.from_contents(common_schema))
    requests = {request["slice_id"]: request for request in authority["compile_requests"]}
    dags = {entry["slice_id"]: entry for entry in authority["compiled_dags"]}
    if set(requests) != {"single_character", "two_character_contact"} or set(dags) != set(requests):
        raise ImageDagAuthorityError("compile_slice_exact_set_mismatch")
    node_count = 0
    for slice_id, request in requests.items():
        expected_character_count = 1 if slice_id == "single_character" else 2
        if request["character_count"] != expected_character_count:
            raise ImageDagAuthorityError(f"compile_request_character_count_mismatch:{slice_id}")
        stored = dags[slice_id]
        expected = compile_dag(request, modules)
        if stored["dag"] != expected:
            raise ImageDagAuthorityError(f"compiled_dag_not_deterministic:{slice_id}")
        validate_schema(stored["dag"], dag_schema, f"dag:{slice_id}", schema_registry)
        if stored["dag"]["compiled_plan_sha256"] != dag_digest(stored["dag"]):
            raise ImageDagAuthorityError(f"compiled_dag_hash_mismatch:{slice_id}")
        mapped = {mapping["intent"]: mapping["pass_id"] for mapping in stored["intent_coverage"]}
        if set(mapped) != set(request["needed_pass_intents"]):
            raise ImageDagAuthorityError(f"compile_intent_coverage_mismatch:{slice_id}")
        valid_passes = {node["pass_id"] for node in stored["dag"]["pass_nodes"]}
        if any(pass_id not in valid_passes for pass_id in mapped.values()):
            raise ImageDagAuthorityError(f"compile_intent_unknown_pass:{slice_id}")
        expected_modules = {INTENT_MODULE[intent] for intent in request["needed_pass_intents"]}
        actual_modules = {pass_id.rsplit("__", 1)[-1] for pass_id in valid_passes}
        if actual_modules != expected_modules:
            raise ImageDagAuthorityError(f"compiled_dag_not_minimal:{slice_id}")
        node_count += len(valid_passes)
    return {"compiled_slice_count": len(dags), "compiled_pass_node_count": node_count}


def validate_vertical_slices(authority: dict[str, Any]) -> dict[str, int]:
    slices = {entry["slice_id"]: entry for entry in authority["vertical_slices"]}
    if set(slices) != {"single_character", "two_character_contact"}:
        raise ImageDagAuthorityError("vertical_slice_exact_set_mismatch")
    for slice_id, entry in slices.items():
        if entry["status"] != "blocked_missing_prerequisites" or entry["runtime_execution_allowed"]:
            raise ImageDagAuthorityError(f"vertical_slice_false_execution:{slice_id}")
        if entry["execution_receipt_refs"] or entry["candidate_artifact_ref"] is not None:
            raise ImageDagAuthorityError(f"vertical_slice_false_runtime_artifact:{slice_id}")
        if not entry["accepted_parent_retained"] or not entry["resumable"] or not entry["failed_region_only_rerun"]:
            raise ImageDagAuthorityError(f"vertical_slice_resume_or_parent_boundary_failed:{slice_id}")
        if len(entry["blocker_codes"]) < 3:
            raise ImageDagAuthorityError(f"vertical_slice_blockers_incomplete:{slice_id}")
    if slices["single_character"]["character_count"] != 1 or slices["two_character_contact"]["character_count"] != 2:
        raise ImageDagAuthorityError("vertical_slice_character_count_mismatch")
    return {"blocked_vertical_slice_count": len(slices)}


def validate_promotion_gate(authority: dict[str, Any]) -> dict[str, int]:
    gate = authority["reproducibility_promotion_gate"]
    bindings = {entry["binding_type"] for entry in gate["lineage_bindings"]}
    if bindings != REQUIRED_LINEAGE or len(gate["lineage_bindings"]) != len(REQUIRED_LINEAGE):
        raise ImageDagAuthorityError("promotion_lineage_exact_set_mismatch")
    if any(entry["status"] != "unavailable" or entry["reference"] is not None for entry in gate["lineage_bindings"]):
        raise ImageDagAuthorityError("promotion_lineage_false_binding")
    qa = {entry["scope"] for entry in gate["qa_results"]}
    if qa != REQUIRED_QA_SCOPES or len(gate["qa_results"]) != len(REQUIRED_QA_SCOPES):
        raise ImageDagAuthorityError("promotion_qa_scope_exact_set_mismatch")
    if any(entry["status"] != "not_run" or entry["evidence_ids"] for entry in gate["qa_results"]):
        raise ImageDagAuthorityError("promotion_qa_false_result")
    if gate["candidate_artifact_manifest_ref"] is not None or gate["promotion_transaction_ref"] is not None:
        raise ImageDagAuthorityError("promotion_false_artifact_or_transaction")
    if gate["decision"] != "blocked" or gate["promotion_allowed"] or not gate["accepted_parent_retained"]:
        raise ImageDagAuthorityError("promotion_gate_boundary_failed")
    return {"lineage_binding_count": len(bindings), "promotion_qa_scope_count": len(qa)}


def validate_all(root: Path, authority: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    validate_schema(authority, schema, "image_dag_authority")
    loaded = validate_sources(root, authority)
    modules = validate_modules(authority, loaded["workflow_module_contract_schema"])
    result: dict[str, Any] = {
        "status": "PASS",
        "classification": "WAVE64_IMAGE_DAG_AUTHORITY_SLICE_PASS",
        "rows_covered": [181, 182, 183, 184],
        "runtime_scope": "blocked_contract_compilation_only",
        "runtime_execution_allowed": authority["runtime_execution_allowed"],
        "promotion_allowed": authority["promotion_allowed"],
        "module_count": len(modules),
    }
    result.update(validate_compilation(
        authority,
        modules,
        loaded["multimodal_pass_dag_schema"],
        loaded["multimodal_contract_common_schema"],
    ))
    result.update(validate_vertical_slices(authority))
    result.update(validate_promotion_gate(authority))
    if any(authority["boundaries"].values()):
        raise ImageDagAuthorityError("authority_false_completion_boundary")
    return result


def refresh_compiled_dags(authority: dict[str, Any]) -> dict[str, Any]:
    refreshed = copy.deepcopy(authority)
    modules = {entry["module_id"]: entry for entry in refreshed["module_library"]}
    requests = {request["slice_id"]: request for request in refreshed["compile_requests"]}
    for entry in refreshed["compiled_dags"]:
        entry["dag"] = compile_dag(requests[entry["slice_id"]], modules)
    return refreshed


def build_evidence(root: Path, result: dict[str, Any], authority_path: Path, schema_path: Path) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "evidence_type": "wave64_image_dag_authority_slice_validation",
        **result,
        "authority": {
            "registry_path": authority_path.as_posix(),
            "registry_sha256": sha256_file(root / authority_path),
            "schema_path": schema_path.as_posix(),
            "schema_sha256": sha256_file(root / schema_path),
            "compiler_path": "Plan/07_IMPLEMENTATION/scripts/compile_wave64_image_dag_authority.py",
            "compiler_sha256": sha256_file(root / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_image_dag_authority.py"),
        },
        "worker_dispatch": {
            "intent_id": "intent_20260717T073135479Z_wave64_rows181_184_image_dag_compiler_authority_63a1d920",
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
            "workflow_release_claimed": False,
            "runtime_lock_claimed": False,
            "execution_receipt_created": False,
            "candidate_artifact_created": False,
            "visual_qa_claimed": False,
            "accepted_parent_mutated": False,
            "promotion_transaction_created": False,
            "item_tracker_status_changed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--refresh-compiled-dags", action="store_true")
    parser.add_argument("--evidence-out", type=Path)
    parser.add_argument("--tracker-evidence-out", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    authority_path = root / args.registry
    authority = load_json(authority_path)
    if args.refresh_compiled_dags:
        authority = refresh_compiled_dags(authority)
        write_json(authority_path, authority)
    result = validate_all(root, authority, load_json(root / args.schema))
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
